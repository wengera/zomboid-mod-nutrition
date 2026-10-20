"""x48_lib -- the session engine of Plan 17 Task 4's live readings of the new health drain (spec section 4.5): the
remaining-fraction drain, its two options NR.DeathPace and NR.HealthCombine, and their admin switch, on a dedicated
server, one boot per session, the STAGED copy of mod/ booted (CLAUDE.md s5, x201).

Built on testing/experiments/xlib.py (the bus step, the wall budget, the grade recorder, RCON, the abort, teardown and
copy skeleton) and, like x47_lib.py and x46_lib.py (the latest libs), on testing/experiments/x45g_lib.py, frozen with
x452-x457 and imported unchanged for its Sess plumbing (the bus step, the clock and its restore, the record setter, the
ring and its pages, the store's next save W, the pure Z/RING grades and the replay-field grade) and its staged gate.
x46_lib and x47_lib are session-specific (fixture default at DayLength 1; fixture two) and are not imported.

THE STAGED COPY. Both profiles boot release/plan17-x48/NutritionRevamp/Contents/mods/NutritionRevamp, staged from mod/'s
last commit before the boot (`python tools/release_pack.py stage mod/NutritionRevamp --out release/plan17-x48`);
staged_gate checks it against release_pack.manifest() of mod/ at STAGED_FROM (a git archive) and refuses on a mismatch,
and preboot refuses when STAGED_FROM is not mod/'s last commit.

THE PROFILES (testing/profiles/x48-*.toml; fixture default, admin -debug, PZTestKit and the staged copy, Nutrition false
(ruling T18-1), DayLength 4 (the 90-minute day: the Realistic curves' calibration day, so r_hunger(dayMin) is the
calibrated 3.564 a game hour, and x442's vanilla death day), sleep off, build 42.21.0): x48-curve sets [sandbox.NR]
DeathPace 3 (Realistic) and HealthCombine 2 (Multiply), the declared defaults, written so the profile says what the run
is; x48-vanilla DeathPace 1 (Vanilla) and HealthCombine 3 (Add), the plain-vanilla corner (spec 2.3).

THE FIRST SIGHT (CLAUDE.md s5, Plan 15 Task 14b). The fixture's character has no store record (preboot reads the
fixture's players.db and store folder), so each session starts on a fresh record, which lands its seed plate. The
predictions are the HEAD replay of each exact schedule from that first sight (testing/experiments/x48_prerun.py, from
FIRST_SIGHT: x442's live start on this fixture at DayLength 4, the vanilla stats the mod's first sight finds; written to
x48_prerun.json, re-derived by `python testing/experiments/x48_prerun.py --write`); preboot refuses a boot whose
committed predictions are not the HEAD replay's.

THE INSTRUMENT. The minute ring (harness H2) carries the overall health and the dead flag on every row since the
harness's Plan 17 Task 4 wrap (`health`, `dead`), read inside the minute event before the mod's queue drains, so row k
reads the health drain k - 1 left, beside the record paths RING. The HEAD replay (tools/replay_live.replay_live,
ServerReplay, sleep off, game_heal on) of the run's own ring from W's start.json, with the record.set writes and the
sandbox write as setpath events, carries the stand-in's health on every row (tools/replay_live.py, Plan 17 Task 4).

THE CLOCK. RCON settimespeed n (time.multiplier only when it fails, x45g_lib.Sess.speed); x482 runs at SPEED_DEATH 30
(x442's: one tick a game minute at DayLength 4, #1776); every setting is restored from the trueMult read at S. No client
joins or relaunches. The seed, the thiamine and the switch are written at speed 1 (a game minute 3.75 wall s), so the
write's bracket of age reads holds at most one minute event.

THE WRITES AND THEIR PLACEMENT. A record.set is bracketed by two age reads (a_before, and the setter's own a_after);
its replay event is placed by place_set: the first ring row read after the set (within two game minutes) that shows
the set value exactly (the set came between the drain before it and its read: a set before a drain that moves the value
would show it moved), else the latest ring row read at or before a_after that holds the reply's `before` (the set came
after that row's read and before its drain), else the first row read after a_after. A value a drain moves (the
thiamine store p below its cap) places exactly; a value the drain leaves (the meal pool M once set to 0, which stays 0
unfed, and the unfed stamp fedAgeH while M is 0) may place one drain late when the set lands between a minute event's
ring read and its drain, which moves nothing graded (no drain restamps fedAgeH while M is 0, and the onset is
SEED_LEAD_H later). The sandbox write (sandbox.var NR.DeathPace) is placed at the first ring row whose
SandboxVars.NR.DeathPace reads the new value (place_sandbox): the ring and the mod's options poll read SandboxVars in the
same minute event, so that row's drain is the first to run on the new pace.

THE SESSIONS (each one boot, under 10 wall minutes, in a foreground call):
  x481 curve   (x48-curve)   S, H (RING), W (start.json), A (at speed 1: record.set satiety.M 0, then drain.fedAgeH to
               the age less STARVE_ONSET_H plus SEED_LEAD_H; speed SPEED_FAST until the record reads starveAcute), O
               (HOLD_H at speed SPEED_FAST), B (at speed 1: record.set nutrients.thiamine.p THIAMINE_P, under the
               clinical rung; polled until the grade reads 4), SW (SWITCH_AFTER_H at SPEED_FAST after the thiamine; at
               speed 1: SandboxVars.NR.DeathPace read, then sandbox.var NR.DeathPace SWITCH_PACE; the server's polled
               option read until it follows; FOLLOW_WATCH_GM at speed 1), P (POST_H at SPEED_FAST), C (the clock), R (the
               ring), K (NR.DeathPace back to the value read before the switch).
  x482 vanilla (x48-vanilla) S, H, W, A (the same seed, then SPEED_DEATH), D (SPEED_DEATH until admin reads dead, polled
               every DEATH_POLL_S with health.get and isDead, or the prerun's death plus DEATH_EXTRA_H, or the wall
               budget), E (the after-death reads), C, R. The server log is copied with the artifact (the death).

THE GRADES (pure; each has a failing case in testing/tests/test_x48_lib.py; a grade on no valid sample is unmeasured,
never as_predicted; every tolerance is named below, before any run):
  both   OPT       (precondition) the first ring row's SandboxVars.NR.DeathPace and HealthCombine, the mod's polled
                   options and K.drain.OPT pace and combine the profile's, and K.drain.OPT.dayMin DAY_MIN.
         ONSET     (precondition) a ring row reads starveAcute and the drain active within SEED_LEAD_H + ONSET_SLACK_H
                   game hours of the seed's write.
         REPLAY_health, REPLAY_drain.target  every ring row's health and target within REPLAY_TOL of the HEAD replay of
                   the run's own inputs (x482: the rows up to the first dead row).
         H1, RING, Z  H1 the ring's paths resolved at the start except H1_NIL_OK (unset before the onset); RING and Z
                   x45g_lib's.
  x481   OPEN_RATE the drain's rate (record drain.rate, health a game day) on the ring rows from the onset to the
                   thiamine within RATE_TOL_REL of r_hunger(dayMin) x 24 (dayMin the ring's K.drain.OPT.dayMin): the
                   Realistic cap at the calibrated rate (spec 1.4, ruling T2-2).
         OPEN_SLOPE the health slope over the first OPEN_GM game minutes from the onset row within OPEN_TOL_REL of the
                   kernel curve's own over the same ring ages for the live body (open_pred: the smoothed BMI clock at
                   the calibrated STARVE_DPDT x (CAL_BMI0 - 12) BMI a game hour from the ring's bmi0, A_STARVE, capped at
                   the rate): at the calibration body this is r_hunger(90) x 24 a day; a heavier body opens slower by
                   (CAL_BMI0 - 12) / (bmi0 - 12) (spec 1.2, recorded as a game choice; the prerun's ratio is a reading).
         BERI_ON   after the thiamine write, a ring row reads the thiamine grade 4 and beriberi's fraction drain.frac.3
                   within BERI_GM game minutes of the write's age, at most 1 and over 1 - BERI_F0_TOL.
         COMBINE   every ring row carrying both fractions reads the target 100 x frac.1 x frac.3 within COMBINE_TOL
                   (Multiply), with the polled combine 2.
         FOLLOW    the switch: the first ring row from the write on whose target is nearer the HEAD replay with the
                   switch than without it (the two arms more than DISCRIM apart there) was left by a drain at most
                   FOLLOW_GM game minutes after the age read before the write (else falsified; unmeasured when the arms
                   never part by DISCRIM).
         CAP       after the switch, while health sits more than CAP_GAP over the target, the health slope (at least
                   CAP_MIN_ROWS rows) within CAP_TOL_REL of the ring's drain.rate / 24 a game hour: health falls toward
                   a target that jumped at the sum of the active rates (spec 1.4).
  x482   SLOPE     the health slope over the active ring rows with health inside SLOPE_BAND within SLOPE_TOL_REL of
                   r_hunger(dayMin) a game hour: vanilla's line (spec 2.2).
         DEATH     the first ring row reading dead (or health at or under DEATH_HEALTH; else the first death poll) within
                   DEATH_TOL_H game hours of the replay's first row at or under DEATH_HEALTH; when the session ends
                   alive, unmeasured, with the line's projected death recorded (checks.projection).
         (reading) checks.x442: the death's game hours after the seed's write and after the onset beside x442's 36.45
                   after its HUNGER write and 28.12 after its level-4 crossing (the onsets differ; never a grade).

FROZEN WITH ITS FIRST RUN: once a driver that imports this file has run, this file is never edited (CLAUDE.md s5).
"""
import glob
import json
import math
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
USER = G.USER
NR = G.NR
LIB_FILE = "x48_lib.py"
MOD_DIR = G.MOD_DIR
STAGE_OUT = "release/plan17-x48"
STAGE_ROOT = STAGE_OUT + "/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
STAGED_FROM = "97f76bac"                 # mod/'s last commit (Plan 17 Task 3 fix 1)
PRERUN_FILE = "testing/experiments/x48_prerun.json"
FIXTURE_PLAYERS_DB = "testing/fixtures/default/cache/server/Saves/Multiplayer/pzt/players.db"
FIXTURE_STORE_DIR = "testing/fixtures/default/cache/server/Lua/NutritionRevamp"
MIN_FREE_GB = 12.0
MOD_DAY_LENGTH = 4
DAY_MIN = 90.0                           # DayLength 4: a 90-minute day, a game hour 225 wall s at speed 1
HOUR_OFFSET = G.HOUR_OFFSET              # world age 0 is 07:00 on the default fixture (#2890)

PROFILES = {"x48-curve": {"pace": 3, "combine": 2}, "x48-vanilla": {"pace": 1, "combine": 3}}
SESSIONS = {
    "x481": {"driver": "x481_curve.py", "artifact": "curve.json", "profile": "x48-curve"},
    "x482": {"driver": "x482_vanilla.py", "artifact": "vanilla.json", "profile": "x48-vanilla"},
}

# ---- the first sight (x442-20261015-173502 starve.json checks.start: stats.worldAge 2.3836374282836914, hunger
# 0.0022823589388281107, thirst 0.0019041254417970777, fatigue 1.6587773643550463e-05, weight 80, calories
# 796.040771484375, carbs -0.865961492061615, lipids -0.2795819044113159, proteins -0.21277907490730286; health.overall
# 100 at 2.3938474655151367): the vanilla state the mod's first sight finds on this fixture at DayLength 4; the age is the
# health read's, rounded to the minute after it
FIRST_SIGHT = {"age": 2.39, "stats": {"HUNGER": 0.0022823589388281107, "THIRST": 0.0019041254417970777,
                                      "FATIGUE": 1.6587773643550463e-05},
               "player": {"weight": 80.0, "health": 100.0,
                          "macros": [796.040771484375, -0.865961492061615, -0.2795819044113159,
                                     -0.21277907490730286]}}

# ---- the kernel's constants (mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Drain.lua at STAGED_FROM; a test
# reads each off the file)
K_R_HUNGER = 0.0396                      # K.drain.R_HUNGER: health a game hour per real minute of day length
K_A_STARVE = 509.81334200481825          # K.drain.A_STARVE
K_STARVE_DPDT = 0.0004359462040936248    # K.drain.STARVE_DPDT: BMI progress a game hour before the first close
K_CAL_BMI0 = 22.42350650342769           # K.drain.CAL_BMI0
K_CAL_DAY_MIN = 90                       # K.drain.CAL_DAY_MIN
K_BMI_DEATH = 12                         # K.drain.BMI_DEATH
K_BERIBERI_DEATH_H = 840                 # K.drain.BERIBERI_DEATH_H
K_CLINICAL = 4                           # K.drain.CLINICAL
THIAMINE_CLINICAL_P = 0.4166666666666667 # NR_Data_Records.lua thiamine ladder[3]
STARVE_ONSET_H = 30.0                    # K.drain.STARVE_ONSET_H


def r_hunger(day_min):
    """Vanilla's hunger level-4 drain in health a game hour at a day of day_min real minutes (spec 2.1)."""
    return K_R_HUNGER * day_min


# ---- the schedule (game hours at DayLength 4)
SEED_LEAD_H = 0.1                        # the unfed clock set to STARVE_ONSET_H - SEED_LEAD_H
HOLD_H = 1.0                             # x481: onset to the thiamine write
THIAMINE_P = 0.30                        # under the clinical rung 0.4167 by more than the absorption can lift in hours
SWITCH_AFTER_H = 0.5                     # x481: the thiamine write to the switch
SWITCH_PACE = 2                          # Shortened
FOLLOW_WATCH_GM = 5.0                    # x481: game minutes watched at speed 1 after the switch
POST_H = 0.75                            # x481: after the watch, at SPEED_FAST
SPEED_FAST = 5                           # a game hour 45 wall s at DayLength 4
SPEED_DEATH = 30                         # x442's: 8 game minutes a wall second at DayLength 4
ONSET_CAP_S = 30.0
BERI_CAP_S = 15.0
FOLLOW_CAP_S = 15.0
POLL_S = 0.25
DEATH_POLL_S = 1.0
DEATH_EXTRA_H = 1.5                      # x482: the run's game-hour cap past the prerun's death
DEAD_HOLD_S = 3.0                        # x482: wall seconds held after the death read, so a ring row reads it

# ---- the tolerances (named before any run)
REPLAY_TOL = {"health": ("abs", 0.002), "drain.target": ("abs", 0.002)}   # x46_lib.REPLAY_TOL's HUNGER bound
OPEN_GM = 3.0
OPEN_TOL_REL = 0.01
RATE_TOL_REL = 0.01
ONSET_SLACK_H = 0.25
BERI_GM = 2.5                            # two minute events at speed 1 (the drain after the write, then the ring read after it), each at most 1.11 game minutes (x46_lib.POLL_GM)
BERI_F0_TOL = 0.001
COMBINE_TOL = 1e-6
FOLLOW_GM = 1.2                          # one minute event of at most 1.11 game minutes at speed 1 (x46_lib.POLL_GM)
                                         # from the age read before the write
DISCRIM = 0.02                           # 10 x REPLAY_TOL: the arms must part by this for FOLLOW to be measured
CAP_GAP = 0.2
CAP_TOL_REL = 0.01
CAP_MIN_ROWS = 5
SLOPE_TOL_REL = 0.01
SLOPE_BAND = (5.0, 95.0)
DEATH_HEALTH = 1e-6                      # tools/mod_guide_series.DEATH_HEALTH
DEATH_TOL_H = 0.05                       # three game minutes: a ring row, a tick's dtM at SPEED_DEATH, the death's tick
EQ_TOL = 1e-9

# ---- x442 (testing/artifacts/x442-20261015-173502/starve.json: checks.X.write.ages[1], checks.X.death.age; the
# level-4 crossing #3882): vanilla starvation to death at DayLength 4
X442_WRITE_AGE = 2.4204587936401367
X442_DEATH_AGE = 38.866790771484375
X442_LEVEL4_AGE = 10.745660781860352

# ---- the ring (32 paths, the harness's cap)
RING = ("drain.active", "drain.state", "drain.mask", "drain.target", "drain.rate", "drain.drainThisMinute",
        "drain.frac.1", "drain.frac.3", "drain.starveAcute", "drain.starving", "drain.starvedH", "drain.stH",
        "drain.fedAgeH", "drain.bmi0", "drain.bClose", "drain.bRate", "drain.pAt", "drain.pS",
        "satiety.M", "nutrients.thiamine.p", "nutrients.thiamine.g", "nutrients.thiamine.ah",
        "body.dayStartH", "body.lm", "body.fm",
        "_G.SandboxVars.NR.DeathPace", "_G.SandboxVars.NR.HealthCombine",
        "_G.NutritionRevamp.server.options.deathPace", "_G.NutritionRevamp.server.options.healthCombine",
        "_G.NutritionRevamp.kernel.drain.OPT.pace", "_G.NutritionRevamp.kernel.drain.OPT.combine",
        "_G.NutritionRevamp.kernel.drain.OPT.dayMin")
H1_NIL_OK = ("drain.frac.1", "drain.frac.3", "drain.pAt")
SB_PACE, SB_COMBINE = "_G.SandboxVars.NR.DeathPace", "_G.SandboxVars.NR.HealthCombine"
OPT_PACE, OPT_COMBINE = "_G.NutritionRevamp.kernel.drain.OPT.pace", "_G.NutritionRevamp.kernel.drain.OPT.combine"
OPT_DAYMIN = "_G.NutritionRevamp.kernel.drain.OPT.dayMin"
POLLED_PACE = "_G.NutritionRevamp.server.options.deathPace"
POLLED_COMBINE = "_G.NutritionRevamp.server.options.healthCombine"
F1, F3 = "drain.frac.1", "drain.frac.3"

# ---- the harness markers (the repository files and every deployed copy)
LUA_DIR = G.LUA_DIR
HARNESS_FILES = {"PZTestKit_Server.lua": LUA_DIR + "/server/PZTestKit_Server.lua",
                 "PZTestKit_Core.lua": LUA_DIR + "/shared/PZTestKit_Core.lua"}
HARNESS_MARKERS = {
    "PZTestKit_Server.lua": tuple(f'TK.register("{c}", function(' for c in (
        "minute.ring", "stats.all", "health.get", "witness.chain", "record.set", "sandbox.var", "nutrition.get",
        "time.multiplier", "players")) + ("function TK.TMH.sampleHealth(row, R)",),
    "PZTestKit_Core.lua": tuple(f'TK.register("{c}", function(' for c in ("time.snapshot", "lua.read",
                                                                         "lua.global")),
}
LOG_RX = G.LOG_RX
MOD_ERR_RX = G.MOD_ERR_RX
DEATH_LOG_RX = re.compile(r"died|dead|death|kill", re.I)
CONSTANTS = {k: v for k, v in dict(globals()).items() if re.match(r"^[A-Z][A-Z0-9_]+$", k)
             and isinstance(v, (int, float, str, bool, tuple, dict)) and k not in ("REPO", "HERE")}


# ================================================================ small readers (pure)
num = G.num
g = G.g
vals = G.vals
fit_slope = G.fit_slope


def same(a, b, tol=EQ_TOL):
    a, b = num(a), num(b)
    return a is not None and b is not None and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def ring_age(r):
    return num(r.get("age"))


def first_index(rows, fn, start=0):
    for i in range(start, len(rows)):
        if fn(rows[i]):
            return i
    return None


def load_prerun(path=None):
    p = path or os.path.join(REPO, PRERUN_FILE)
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


# ================================================================ the write placement (pure)
def place_set(rows, path, after, before, a_before, a_after, back=5, shown_gm=2.0):
    """The ring row s whose drain is the first to run on a record.set (see the module docstring): returns (s, how).
    A row read after the set, inside shown_gm game minutes of a_after, that shows the set value exactly: the set came
    between the drain before it and its read (a drain moves a value it reads, so a set before the drain shows
    changed); else the latest row read at or before a_after (of the last `back`) that holds `before`: the set came
    after that row's read and before its drain; else the first row read after a_after."""
    lo = (a_before if a_before is not None else a_after) - EQ_TOL
    for r in rows:
        a = ring_age(r)
        if a is not None and lo <= a <= a_after + shown_gm / 60.0 and same(r.get(path), after):
            return r["s"], "shown"
    upto = [i for i, r in enumerate(rows) if ring_age(r) is not None and ring_age(r) <= a_after + EQ_TOL]
    for i in reversed(upto[-back:]):
        if before is not None and same(rows[i].get(path), before):
            return rows[i]["s"], "before"
    for r in rows:
        a = ring_age(r)
        if a is not None and a > a_after + EQ_TOL:
            return r["s"], "age"
    return None, "unplaced"


def place_sandbox(rows, path, value, a_before):
    """The first ring row from a_before on whose SandboxVars path reads the new value: that row's drain is the first to
    run on it (the ring and the options poll read SandboxVars in the same minute event)."""
    for r in rows:
        a = ring_age(r)
        if a is not None and a >= a_before - 1.0 / 60.0 and same(r.get(path), value):
            return r["s"], "shown"
    return None, "unplaced"


def build_events(rows, sets, sandbox=()):
    """The run's writes as replay setpath events: each record.set (sets: {path, value, age, age_before, reply:
    {ok, before, after}}) placed by place_set, each sandbox write ({path, value, age_before, ok}) by place_sandbox.
    Returns (events, book)."""
    events, book = [], []
    for st in sets:
        rep = st.get("reply") or {}
        if rep.get("ok") is not True:
            book.append({"path": st.get("path"), "skipped": "the set did not answer ok"})
            continue
        after = num(rep.get("after"))
        if after is None:
            after = num(st.get("value"))
        s, how = place_set(rows, st["path"], after, num(rep.get("before")), num(st.get("age_before")),
                           num(st.get("age")))
        book.append({"path": st["path"], "value": after, "s": s, "how": how})
        if s is not None:
            events.append({"s": s, "kind": "setpath", "path": st["path"], "value": after, "label": st.get("tag")})
    for sb in sandbox:
        if sb.get("ok") is not True:
            book.append({"path": sb.get("path"), "skipped": "the write did not answer ok"})
            continue
        s, how = place_sandbox(rows, sb["ring_path"], sb["value"], num(sb.get("age_before")))
        book.append({"path": sb["path"], "value": sb["value"], "s": s, "how": how})
        if s is not None:
            events.append({"s": s, "kind": "setpath", "path": sb["path"], "value": sb["value"],
                           "label": sb.get("tag")})
    events.sort(key=lambda e: e["s"])
    return events, book


# ================================================================ the grades (pure)
def grade_h1(h1, ring_start, nil_ok=H1_NIL_OK):
    """H1: the ring armed and its paths resolved at the start (lua.read) except those unset before the onset."""
    miss = g(h1, "missing") or {}
    bad = {k: v for k, v in miss.items() if k not in nil_ok} if isinstance(miss, dict) else miss
    ok = g(ring_start, "ok") is True and isinstance(h1, dict) and not bad
    return ("as_predicted" if ok else "falsified"), {"missing": miss, "missing_not_allowed": bad,
                                                      "ring_ok": g(ring_start, "ok")}


def grade_opt(rows, pace, combine, day_min=DAY_MIN):
    """OPT: the first ring row's sandbox leaves, the polled options and K.drain.OPT read the profile's pace and combine,
    and OPT.dayMin the day length."""
    if not rows:
        return "unmeasured", {"why": "no ring row"}
    r = rows[0]
    want = {SB_PACE: pace, SB_COMBINE: combine, POLLED_PACE: pace, POLLED_COMBINE: combine, OPT_PACE: pace,
            OPT_COMBINE: combine, OPT_DAYMIN: day_min}
    got = {k: r.get(k) for k in want}
    off = {k: (got[k], v) for k, v in want.items() if not same(got[k], v)}
    return ("falsified" if off else "as_predicted"), {"s": r.get("s"), "read": got, "off": off}


def onset_index(rows, after_age=None):
    return first_index(rows, lambda r: r.get("drain.starveAcute") is True and r.get("drain.active") is True
                       and (after_age is None or (ring_age(r) or -1) > after_age))


def grade_onset(rows, seed_age):
    """ONSET (precondition): a row reads starveAcute and the drain active within SEED_LEAD_H + ONSET_SLACK_H of the
    seed's write."""
    if seed_age is None or not rows:
        return "unmeasured", {"why": "no seed write or no ring row"}
    i = onset_index(rows, seed_age)
    obs = {"seed_age": seed_age, "onset_s": None if i is None else rows[i]["s"],
           "onset_age": None if i is None else ring_age(rows[i])}
    limit = seed_age + SEED_LEAD_H + ONSET_SLACK_H
    if i is not None and ring_age(rows[i]) <= limit:
        obs["after_seed_h"] = ring_age(rows[i]) - seed_age
        return "as_predicted", obs
    if i is not None or (ring_age(rows[-1]) or 0) > limit:
        obs["why"] = "no onset row within the lead and the slack"
        return "falsified", obs
    return "unmeasured", obs


def grade_open_rate(rows, i_on, i_end=None):
    """OPEN_RATE: drain.rate on the rows from the onset row to i_end (excluded) within RATE_TOL_REL of
    r_hunger(dayMin) x 24 (dayMin the row's K.drain.OPT.dayMin)."""
    if i_on is None:
        return "unmeasured", {"why": "no onset row"}
    span = rows[i_on:i_end] if i_end is not None else rows[i_on:]
    pts = [(r.get("drain.rate"), r.get(OPT_DAYMIN)) for r in span if r.get("drain.active") is True]
    pts = [(num(a), num(b)) for a, b in pts if num(a) is not None and num(b) is not None]
    if not pts:
        return "unmeasured", {"why": "no active row with a rate and a day length"}
    worst = max(abs(a - r_hunger(b) * 24.0) / (r_hunger(b) * 24.0) for a, b in pts)
    obs = {"n": len(pts), "rate_first": pts[0][0], "want": r_hunger(pts[0][1]) * 24.0, "worst_rel": worst,
           "tol_rel": RATE_TOL_REL}
    return ("as_predicted" if worst <= RATE_TOL_REL else "falsified"), obs


def curve(tau, T, a):
    """K.drain.curve."""
    if not T > 0:
        return 0.0
    t = max(0.0, min(T, tau))
    if not a > 1e-9:
        return 1.0 - t / T
    return 1.0 - math.log(1.0 + a * t) / math.log(1.0 + a * T)


def open_pred(rows, i_on, gm=OPEN_GM):
    """The live opening: the health slope (health a game hour) from the onset row over gm game minutes, beside the kernel
    curve's over the same ring ages for the ring's bmi0 (the progress STARVE_DPDT x (CAL_BMI0 - 12) / (bmi0 - 12) a
    game hour from the onset drain, the row before the onset row; capped at the row's rate), and the slope at 0."""
    if i_on is None or i_on < 1:
        return None
    r0 = rows[i_on]
    a_on = ring_age(rows[i_on - 1])
    bmi0 = num(r0.get("drain.bmi0"))
    rate = num(r0.get("drain.rate"))
    if a_on is None or bmi0 is None or not bmi0 > K_BMI_DEATH or rate is None:
        return None
    span = [r for r in rows[i_on:] if ring_age(r) is not None and ring_age(r) <= ring_age(r0) + gm / 60.0 + EQ_TOL]
    if len(span) < 2:
        return None
    dbmi = K_STARVE_DPDT * (K_CAL_BMI0 - K_BMI_DEATH)
    idx = {id(r): i for i, r in enumerate(rows)}
    pred, h = [], 100.0
    for r in span:
        i = idx[id(r)]
        p = dbmi * (ring_age(rows[i - 1]) - a_on) / (bmi0 - K_BMI_DEATH)
        t = 100.0 * curve(p, 1.0, K_A_STARVE)
        if pred:
            dt = (ring_age(rows[i - 1]) - ring_age(rows[i - 2])) * 60.0
            h = max(t, h - rate * dt / 1440.0)
        else:
            h = t
        pred.append(h)
    live = [num(r.get("health")) for r in span]
    if any(v is None for v in live):
        return None
    dt_h = ring_age(span[-1]) - ring_age(span[0])
    slope0 = 100.0 * K_A_STARVE / math.log(1.0 + K_A_STARVE) * dbmi / (bmi0 - K_BMI_DEATH)
    return {"rows": len(span), "dt_h": dt_h, "live": (live[0] - live[-1]) / dt_h, "pred": (pred[0] - pred[-1]) / dt_h,
            "slope0": min(slope0, rate / 24.0), "bmi0": bmi0, "rate_day": rate,
            "body_ratio": (K_CAL_BMI0 - K_BMI_DEATH) / (bmi0 - K_BMI_DEATH)}


def grade_open_slope(op):
    """OPEN_SLOPE: open_pred's live slope within OPEN_TOL_REL of its kernel slope."""
    if not op or not op.get("pred"):
        return "unmeasured", {"why": "no opening span", "open": op}
    rel = abs(op["live"] - op["pred"]) / op["pred"]
    obs = dict(op, rel=rel, tol_rel=OPEN_TOL_REL)
    return ("as_predicted" if rel <= OPEN_TOL_REL else "falsified"), obs


def grade_beri(rows, set_age):
    """BERI_ON: after the thiamine write at set_age, a row reads grade 4 and frac.3 in (1 - BERI_F0_TOL, 1] within
    BERI_GM game minutes."""
    if set_age is None or not rows:
        return "unmeasured", {"why": "no thiamine write or no ring row"}
    i = first_index(rows, lambda r: (ring_age(r) or -1) > set_age and same(r.get("nutrients.thiamine.g"), K_CLINICAL)
                    and num(r.get(F3)) is not None)
    obs = {"set_age": set_age, "s": None if i is None else rows[i]["s"]}
    if i is None:
        late = (ring_age(rows[-1]) or 0) > set_age + BERI_GM / 60.0
        obs["why"] = "no row with the clinical grade and beriberi's fraction"
        return ("falsified" if late else "unmeasured"), obs
    r = rows[i]
    obs.update({"age": ring_age(r), "lag_gm": (ring_age(r) - set_age) * 60.0, "frac3": num(r.get(F3))})
    ok = obs["lag_gm"] <= BERI_GM and 1.0 - BERI_F0_TOL < obs["frac3"] <= 1.0
    return ("as_predicted" if ok else "falsified"), obs


def grade_combine(rows, combine=2):
    """COMBINE: every row with both fractions reads the target 100 x f1 x f3 (Multiply) within COMBINE_TOL, the polled
    combine the profile's."""
    both = [r for r in rows if num(r.get(F1)) is not None and num(r.get(F3)) is not None]
    if not both:
        return "unmeasured", {"why": "no row with both fractions"}
    bad = []
    for r in both:
        want = 100.0 * max(0.0, num(r[F1]) * num(r[F3]))
        t = num(r.get("drain.target"))
        if t is None or abs(t - want) > COMBINE_TOL * 100.0 or not same(r.get(OPT_COMBINE), combine):
            bad.append({"s": r.get("s"), "target": t, "want": want, "combine": r.get(OPT_COMBINE)})
    obs = {"n": len(both), "off": bad[:10], "n_off": len(bad)}
    return ("falsified" if bad else "as_predicted"), obs


def grade_follow(rows, arm_on, arm_off, a_before, window_h=0.25):
    """FOLLOW: the first ring row from a_before on whose target is nearer the switch arm than the no-switch arm, where the
    arms part by more than DISCRIM; its drain (the row before) at most FOLLOW_GM game minutes after a_before. arm_on and
    arm_off are replay rows labelled by s (replay row k carries ring row k + 1's s)."""
    if a_before is None or not rows:
        return "unmeasured", {"why": "no write or no ring row"}
    on = {r.get("s"): num(r.get("drain.target")) for r in arm_on or []}
    off = {r.get("s"): num(r.get("drain.target")) for r in arm_off or []}
    parted, i_follow = [], None
    for i, r in enumerate(rows):
        a = ring_age(r)
        if a is None or a < a_before - EQ_TOL or a > a_before + window_h:
            continue
        t, x, y = num(r.get("drain.target")), on.get(r.get("s")), off.get(r.get("s"))
        if t is None or x is None or y is None or abs(x - y) <= DISCRIM:
            continue
        parted.append(r.get("s"))
        if abs(t - x) < abs(t - y):
            i_follow = i
            break
    obs = {"a_before": a_before, "parted_rows": parted[:5]}
    if i_follow is None:
        if not parted:
            obs["why"] = "the arms never parted by DISCRIM inside the window"
            return "unmeasured", obs
        obs["why"] = "the target never followed the switch arm inside the window"
        return "falsified", obs
    if i_follow < 1:
        return "unmeasured", dict(obs, why="the following row has no row before it")
    d_age = ring_age(rows[i_follow - 1])
    obs.update({"s": rows[i_follow]["s"], "drain_age": d_age, "lag_gm": (d_age - a_before) * 60.0,
                "target": num(rows[i_follow].get("drain.target")), "arm_on": on.get(rows[i_follow]["s"]),
                "arm_off": off.get(rows[i_follow]["s"])})
    return ("as_predicted" if obs["lag_gm"] <= FOLLOW_GM else "falsified"), obs


def grade_cap(rows, a0, a1=None):
    """CAP: on the rows after a0 where health sits more than CAP_GAP over the target, the health slope within
    CAP_TOL_REL of drain.rate / 24 a game hour."""
    span = [r for r in rows if ring_age(r) is not None and ring_age(r) > a0 and (a1 is None or ring_age(r) <= a1)
            and num(r.get("health")) is not None and num(r.get("drain.target")) is not None
            and num(r.get("health")) - num(r.get("drain.target")) > CAP_GAP and num(r.get("drain.rate")) is not None]
    if len(span) < CAP_MIN_ROWS:
        return "unmeasured", {"why": f"{len(span)} capped row(s), under {CAP_MIN_ROWS}"}
    slope = fit_slope([(ring_age(r), num(r["health"])) for r in span])
    rate = sum(num(r["drain.rate"]) for r in span) / len(span)
    want = -rate / 24.0
    rel = abs(slope - want) / abs(want) if slope is not None and want else math.inf
    obs = {"n": len(span), "slope_h": slope, "want_h": want, "rate_day": rate, "rel": rel, "tol_rel": CAP_TOL_REL,
           "a0": ring_age(span[0]), "a1": ring_age(span[-1])}
    return ("as_predicted" if rel <= CAP_TOL_REL else "falsified"), obs


def grade_slope(rows):
    """SLOPE (x482): the health slope over the active rows with health inside SLOPE_BAND within SLOPE_TOL_REL of
    r_hunger(dayMin) a game hour."""
    span = [r for r in rows if r.get("drain.active") is True and num(r.get("health")) is not None
            and SLOPE_BAND[0] < num(r["health"]) < SLOPE_BAND[1] and ring_age(r) is not None]
    dm = [num(r.get(OPT_DAYMIN)) for r in span if num(r.get(OPT_DAYMIN)) is not None]
    if len(span) < 2 or not dm:
        return "unmeasured", {"why": "under two active rows inside the band"}
    slope = fit_slope([(ring_age(r), num(r["health"])) for r in span])
    want = -r_hunger(dm[0])
    rel = abs(slope - want) / abs(want) if slope is not None else math.inf
    obs = {"n": len(span), "slope_h": slope, "want_h": want, "day_min": dm[0], "rel": rel, "tol_rel": SLOPE_TOL_REL,
           "a0": ring_age(span[0]), "a1": ring_age(span[-1])}
    return ("as_predicted" if rel <= SLOPE_TOL_REL else "falsified"), obs


def death_row(rows):
    """The first ring row reading dead, or health at or under DEATH_HEALTH."""
    i = first_index(rows, lambda r: r.get("dead") is True or (num(r.get("health")) is not None
                                                              and num(r["health"]) <= DEATH_HEALTH))
    return None if i is None else rows[i]


def death_live(rows, polls=()):
    """The live death: (age, source), the ring's death row, else the first poll reading dead; (None, None) alive."""
    r = death_row(rows)
    if r is not None:
        return ring_age(r), "ring"
    p = next((p for p in polls if p.get("dead")), None)
    if p is not None:
        return num(p.get("age")), "poll"
    return None, None


def death_replay(rep_rows):
    r = next((r for r in rep_rows or [] if num(r.get("health")) is not None and num(r["health"]) <= DEATH_HEALTH), None)
    return None if r is None else num(r.get("age"))


def grade_death(live_age, rep_age, last_age=None):
    """DEATH: the live death within DEATH_TOL_H of the replay's; alive past the replay's death plus the tolerance is
    falsified; ended alive before it, unmeasured."""
    obs = {"live_age": live_age, "replay_age": rep_age, "tol_h": DEATH_TOL_H, "last_age": last_age}
    if rep_age is None:
        return "unmeasured", dict(obs, why="the replay never died")
    if live_age is None:
        if last_age is not None and last_age > rep_age + DEATH_TOL_H:
            return "falsified", dict(obs, why="alive past the replay's death plus the tolerance")
        return "unmeasured", dict(obs, why="the session ended alive before the replay's death plus the tolerance")
    obs["miss_h"] = live_age - rep_age
    return ("as_predicted" if abs(obs["miss_h"]) <= DEATH_TOL_H else "falsified"), obs


def projection(rows):
    """The line's projected death when the session ended alive: the last active row's age plus its health over the
    fitted slope."""
    span = [r for r in rows if r.get("drain.active") is True and num(r.get("health")) is not None
            and ring_age(r) is not None]
    if len(span) < 2:
        return None
    slope = fit_slope([(ring_age(r), num(r["health"])) for r in span])
    if slope is None or slope >= 0:
        return None
    last = span[-1]
    return {"last_age": ring_age(last), "last_health": num(last["health"]), "slope_h": slope,
            "projected_age": ring_age(last) + num(last["health"]) / -slope}


def x442_reading(death_age, seed_age, onset_age):
    """The death beside x442's (a reading: the onsets differ)."""
    if death_age is None:
        return {"why": "no live death"}
    out = {"x442_after_write_h": X442_DEATH_AGE - X442_WRITE_AGE,
           "x442_after_level4_h": X442_DEATH_AGE - X442_LEVEL4_AGE}
    if seed_age is not None:
        out["after_seed_h"] = death_age - seed_age
        out["diff_after_write_h"] = out["after_seed_h"] - out["x442_after_write_h"]
    if onset_age is not None:
        out["after_onset_h"] = death_age - onset_age
        out["diff_after_onset_h"] = out["after_onset_h"] - out["x442_after_level4_h"]
    return out


def rows_upto_death(rows):
    r = death_row(rows)
    if r is None:
        return list(rows)
    return [x for x in rows if x["s"] <= r["s"]]


# ================================================================ the replay
def replay(ring_rows, events, start, pace, combine, day_min, player=None, start_stats=None):
    """The HEAD replay of the ring (tools/replay_live.replay_live, sleep off, game_heal on). Returns (rows, backend)."""
    import replay_live as RL
    return RL.replay_live(ring_rows, events, start, paths=list(RING), user=USER, player=player,
                          start_stats=start_stats, sleep_allowed=False, death_pace=pace, health_combine=combine,
                          day_minutes=day_min, game_heal=True)


def replay_diff(rep_rows, ring_rows, tol=None):
    import replay_live as RL
    return RL.diff(rep_rows, ring_rows, REPLAY_TOL if tol is None else tol)


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
    """A profile's TOML against PROFILES[name]: its header naming its own file, fixture default, the one admin client,
    sleep off, PZTestKit and the staged copy, Nutrition false, DayLength 4, the [sandbox.NR] block of DeathPace and
    HealthCombine alone at the session's values, two version verify rows."""
    spec = PROFILES.get(name)
    if spec is None:
        return {"known_profile": False}
    mods = [m.get("id") for m in doc.get("mods") or []]
    paths = {m.get("id"): m.get("path") for m in doc.get("mods") or []}
    sb = doc.get("sandbox") or {}
    srv = doc.get("server") or {}
    return {"known_profile": True,
            "header_names_file": text.startswith(f"# testing/profiles/{name}.toml"),
            "fixture_default": doc.get("fixture") == "default",
            "one_admin_client": doc.get("clients", ["admin"]) == ["admin"],
            "sleep_off": srv.get("SleepAllowed") is False and srv.get("SleepNeeded") is False,
            "mods_staged": mods == ["PZTestKit", NR] and paths.get(NR) == STAGE_MOD,
            "nutrition_false": sb.get("Nutrition") is False,
            "day_length": sb.get("DayLength") == MOD_DAY_LENGTH,
            "nr_block": sb.get("NR") == {"DeathPace": spec["pace"], "HealthCombine": spec["combine"]},
            "verify_version": sum(1 for v in doc.get("verify") or [] if v.get("args") == f"{NR}.version") >= 2}


def players_db_read(path, user=USER):
    """x46_lib's: the admin row of a players.db read without a lock: the blob's length and whether it holds the mod's
    key."""
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


def fixture_fresh(repo=REPO):
    """x46_lib's: the fixture's admin holds no copy of a record and the fixture no store slot: a fresh record."""
    r = players_db_read(os.path.join(repo, FIXTURE_PLAYERS_DB))
    r["store_dir"] = os.path.isdir(os.path.join(repo, FIXTURE_STORE_DIR))
    r["fresh"] = r.get("length") is not None and r.get("has_key") is False and r["store_dir"] is False
    return r


def mod_head(repo=REPO):
    try:
        p = subprocess.run(["git", "log", "-1", "--format=%h", "--", MOD_DIR], cwd=repo, capture_output=True,
                           text=True)
    except OSError:
        return None
    return p.stdout.strip() or None


def prerun_current(key, repo=REPO, compute=None, committed=None):
    """The session's committed prerun against the HEAD replay re-derived now (x48_prerun.compute)."""
    if compute is None:
        import x48_prerun as PR
        compute = PR.compute
    have = (committed if committed is not None else load_prerun(os.path.join(repo, PRERUN_FILE))).get(key)
    try:
        now = json.loads(json.dumps(compute([key])[key], sort_keys=True, default=str))
    except Exception as e:                                         # noqa: BLE001 - recorded, refuses the boot
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return {"ok": have == now, "committed": have is not None, "diff": None if have == now else {"committed": have,
                                                                                               "now": now}}


def preboot(key, profile_name, prefix, driver_file, repo=REPO, compute=None):
    """The driver's prefix, profile and file name its session (CLAUDE.md s5); no artifact of the prefix committed; the
    profile's TOML; the harness markers; STAGED_FROM mod/'s last commit; the fixture fresh; the prerun current.
    Returns (checks, ok)."""
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
    pr = prerun_current(key, repo, compute) if c["key"] else {"ok": False}
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
    """One x48 session's phases over an xlib.Xs, on x45g_lib.Sess's plumbing."""

    def __init__(self, xs, key, run_dir=None, prerun=None):
        self.xs = xs
        self.out = xs.out
        self.key = key
        self.spec = SESSIONS[key]
        self.prof = PROFILES[self.spec["profile"]]
        self.D = self.out.setdefault("checks", {})
        self.run_dir = run_dir
        self.speeds = self.out.setdefault("speeds", [])
        self.cur_speed = None
        self.restore_to = None
        self.pages, self.eats, self.pairs, self.points, self.consts, self.drinks = [], [], [], [], [], []
        self.sets = self.out.setdefault("sets", [])
        self.sandbox = self.out.setdefault("sandbox_writes", [])
        self.polls = self.out.setdefault("death_polls", [])
        self.red0 = None
        self.dead = False
        self.P = prerun if prerun is not None else load_prerun().get(key, {})
        self.out["lib_x48"] = LIB_FILE
        self.out["constants_x48"] = dict(CONSTANTS)
        self.out["prerun_x48"] = self.P

    # -- reads and writes
    def glob_read(self, tag, paths, log=False):
        return vals(self.lread(tag, SRV, "_G", paths, log=log))

    def write(self, tag, path, value):
        """record.set bracketed by an age read before it (the setter reads the age after)."""
        a0 = self.age(tag + "_a0")
        row = self.record_set(tag, path, value)
        row["age_before"] = a0
        return row

    def sandbox_write(self, tag, leaf, value):
        """sandbox.var NR.<leaf> <value>, bracketed by two age reads; the SandboxVars leaf read before it."""
        P = {"tag": tag, "path": f"_G.SandboxVars.NR.{leaf}", "ring_path": f"_G.SandboxVars.NR.{leaf}",
             "value": value}
        P["read_before"] = self.glob_read(tag + "_read", (f"SandboxVars.NR.{leaf}",), log=True).get(
            f"SandboxVars.NR.{leaf}")
        P["age_before"] = self.age(tag + "_a0")
        r = self.k(tag, SRV, "sandbox.var", f"NR.{leaf} {value}")
        P["reply"] = {k: r.get(k) for k in ("ok", "path", "requested", "before", "after", "reason", "raw")}
        P["ok"] = r.get("ok") is True
        P["age"] = self.age(tag + "_a1")
        if not P["ok"]:
            self.xs.note(f"{tag}: sandbox.var NR.{leaf} {value} answered {r.get('reason') or r.get('raw')!r}")
        self.sandbox.append(P)
        return P

    def death_check(self, tag):
        """x44's: isDead (witness.chain) and the overall health (health.get); `gone` when both say no online player."""
        d = self.k(tag + "_dead", SRV, "witness.chain", f"{USER} isDead", log=False)
        h = self.k(tag + "_hp", SRV, "health.get", USER, log=False)
        a = self.age(tag + "_a")
        overall = num(h.get("overall"))
        row = {"age": a, "dead": str(d.get("value")).lower() == "true" or (overall is not None and overall <= 0.0),
               "dead_raw": d.get("value"), "overall": overall,
               "gone": all(str(x or "").startswith("no online player") for x in (d.get("raw"), h.get("raw")))}
        self.polls.append(row)
        if row["dead"] and not self.dead:
            self.dead = True
            self.xs.note(f"admin read dead at age {a}")
        return row

    # ======================================================== the phases
    def phase_S48(self):
        P = self.D["S"] = {}
        P["players"] = self.xs.step("S_players", SRV, "players")["ack"]
        P["sandbox"] = self.glob_read("S_sv", ("SandboxVars.Nutrition", "SandboxVars.DayLength", "SandboxVars.NR.DeathPace",
                                               "SandboxVars.NR.HealthCombine", "NutritionRevamp.version",
                                               "NutritionRevamp.server.options.deathPace",
                                               "NutritionRevamp.server.options.healthCombine",
                                               "NutritionRevamp.kernel.drain.OPT.dayMin"), log=True)
        P["clock"] = self.clock_read()
        P["nutrition"] = self.k("S_nutrition", SRV, "nutrition.get", USER)
        P["stats_all"] = self.k("S_stats_all", SRV, "stats.all", USER)
        P["health"] = self.health("S_health")
        P["const"] = self.constant("S_const")

    def phase_H(self):
        P = self.D["H"] = {}
        rec = [p for p in RING if not p.startswith("_G.")]
        P["ring_paths"] = list(RING)
        P["h1_record"] = self.lread("H_h1", SRV, f"record:{USER}", rec + list(G.H1_EXTRA))
        P["h1_globals"] = self.lread("H_h1g", SRV, "_G", [p[3:] for p in RING if p.startswith("_G.")])
        P["ring_start"] = self.ring_start(list(RING))

    def phase_W48(self):
        self.phase_W()
        self.D["W"]["health"] = self.health("W_health")

    def phase_A(self):
        """The seed at speed 1: the meal pool 0, then the unfed clock past the onset by STARVE_ONSET_H - SEED_LEAD_H;
        then the session's speed until the record reads starveAcute."""
        P = self.D["A"] = {}
        self.set_speed(1, "A_one")
        P["pre"] = self.rec("A_pre", ("satiety.M", "drain.fedAgeH", "drain.starveAcute"), log=True)
        P["set_M"] = self.write("A_M", "satiety.M", "0")
        a = self.age("A_a")
        P["set_fed"] = self.write("A_fed", "drain.fedAgeH", f"{a - STARVE_ONSET_H + SEED_LEAD_H:.6f}")
        P["seed_age"] = P["set_fed"]["age"]
        P["fed_after"] = self.rec("A_fed_check", ("satiety.M", "drain.fedAgeH"), log=True)
        self.set_speed(SPEED_DEATH if self.key == "x482" else SPEED_FAST, "A_go")

        def fn():
            v = self.rec("A_poll", ("drain.starveAcute", "drain.active"))
            return v.get("drain.starveAcute") is True, v
        P["poll"] = self.poll("A_onset", fn, ONSET_CAP_S, POLL_S)
        P["onset_polled_age"] = self.age("A_on") if P["poll"]["done"] else None
        P["drain"] = self.rec("A_drain", ("drain.active", "drain.state", "drain.target", "drain.rate", "drain.bmi0"),
                              log=True)

    def phase_O(self):
        a = self.D["A"].get("onset_polled_age") or self.age("O_a0") or 0.0
        self.D["O"] = {"end": self.run_until(a + HOLD_H, SPEED_FAST, "O_hold")}

    def phase_B(self):
        """The thiamine store under the clinical rung at speed 1, polled until the grade reads 4."""
        P = self.D["B"] = {}
        self.set_speed(1, "B_one")
        P["set_p"] = self.write("B_p", "nutrients.thiamine.p", f"{THIAMINE_P}")

        def fn():
            v = self.rec("B_poll", ("nutrients.thiamine.g", "drain.frac.3"))
            return same(v.get("nutrients.thiamine.g"), K_CLINICAL), v
        P["poll"] = self.poll("B_grade", fn, BERI_CAP_S, POLL_S)

    def phase_SW(self):
        """SWITCH_AFTER_H at SPEED_FAST after the thiamine; at speed 1 the switch, its poll, FOLLOW_WATCH_GM watched."""
        P = self.D["SW"] = {}
        a = num(g(self.D, "B", "set_p", "age")) or self.age("SW_a0") or 0.0
        self.run_until(a + SWITCH_AFTER_H, SPEED_FAST, "SW_lead")
        self.set_speed(1, "SW_one")
        P["write"] = self.sandbox_write("SW_pace", "DeathPace", SWITCH_PACE)

        def fn():
            v = self.glob_read("SW_poll", (POLLED_PACE[3:], OPT_PACE[3:]))
            return same(v.get(OPT_PACE[3:]), SWITCH_PACE), v
        P["poll"] = self.poll("SW_follow", fn, FOLLOW_CAP_S, POLL_S)
        P["followed_age"] = self.age("SW_fa") if P["poll"]["done"] else None
        a1 = self.age("SW_a1") or 0.0
        P["watch_end"] = self.run_until(a1 + FOLLOW_WATCH_GM / 60.0, 1, "SW_watch")

    def phase_P(self):
        a = self.age("P_a0") or 0.0
        self.D["P"] = {"end": self.run_until(a + POST_H, SPEED_FAST, "P_post")}

    def phase_D(self):
        """SPEED_DEATH until admin reads dead (polled), the prerun's death plus DEATH_EXTRA_H, or the budget."""
        P = self.D["D"] = {}
        seed = num(g(self.D, "A", "seed_age")) or self.age("D_a0") or 0.0
        h = num(g(self.P, "death_after_seed_h")) or (100.0 / r_hunger(DAY_MIN) + SEED_LEAD_H)
        P["cap_age"] = seed + h + DEATH_EXTRA_H
        P["end"] = self.run_until(P["cap_age"], SPEED_DEATH, "D_run", every_s=DEATH_POLL_S,
                                  fn=lambda a: self.death_check("D_poll"), stop=lambda a: self.dead)
        P["dead"] = self.dead
        if self.dead:
            self.sleep_until(self.xs.clock() + DEAD_HOLD_S)

    def phase_E(self):
        P = self.D["E"] = {}
        P["death"] = self.death_check("E_dead")
        P["players"] = self.xs.step("E_players", SRV, "players")["ack"]
        P["drain"] = self.rec("E_drain", ("drain.active", "drain.state", "drain.target", "drain.stH"), log=True)

    def phase_K(self):
        """NR.DeathPace back to the value read before the switch (never the reply's echo)."""
        w = g(self.D, "SW", "write") or {}
        before = w.get("read_before")
        if not w or before is None:
            self.D["K"] = {"skipped": "no switch, or its leaf unread before it"}
            return
        self.D["K"] = {"restore": self.k("K_pace", SRV, "sandbox.var", f"NR.DeathPace {before}")}

    def phases(self):
        S, H, W = ("S", self.phase_S48), ("H", self.phase_H), ("W", self.phase_W48)
        A, C, R = ("A", self.phase_A), ("C", self.restore_clock), ("R", self.phase_R)
        return {
            "x481": [S, H, W, A, ("O", self.phase_O), ("B", self.phase_B), ("SW", self.phase_SW),
                     ("P", self.phase_P), C, R, ("K", self.phase_K)],
            "x482": [S, H, W, A, ("D", self.phase_D), ("E", self.phase_E), C, R],
        }[self.key]

    def closing_names(self):
        return ("C", "R", "K", "E")

    # ======================================================== the grades
    def _g(self, name, res, falsifier):
        v, obs = res
        self.xs.grade(name, v, obs, falsifier)

    def grade_all(self):
        rows = self.ring_rows()
        self.out["ring_rows"] = len(rows)
        self._g("H1", grade_h1(g(self.D, "H", "h1_record"), g(self.D, "H", "ring_start")),
                "a ring path other than H1_NIL_OK unresolved at the start")
        self._g("RING", G.grade_ring(g(self.D, "R", "pages") or []), "a ring page unread or a ring error")
        self._g("Z", G.grade_z(self.out), "a mod error line in the server log, or admin parked in the debugger")
        self._g("OPT", grade_opt(rows, self.prof["pace"], self.prof["combine"]),
                "the first row's sandbox leaves, polled options or K.drain.OPT off the profile's")
        seed = num(g(self.D, "A", "seed_age"))
        self._g("ONSET", grade_onset(rows, seed), "no starveAcute row within the lead and the slack")
        live = rows_upto_death(rows) if self.key == "x482" else rows
        arms = self.grade_replay(live)
        getattr(self, "grade_" + self.key)(rows, arms)
        self.out["verdict_summary"] = {k: v.get("verdict") for k, v in self.out["verdicts"].items()}

    def replay_inputs(self):
        start_path = os.path.join(self.run_dir or "", "start.json")
        if not os.path.isfile(start_path):
            return None
        with open(start_path, encoding="utf-8") as fh:
            start = json.load(fh)
        nut = g(self.D, "S", "nutrition") or {}
        sex = g(self.D, "H", "h1_record", "values", "body.sex")
        player = {"female": sex == 2, "weight": num(nut.get("weight")) or 80.0,
                  "macros": [num(nut.get(k)) or 0.0 for k in ("calories", "carbs", "lipids", "proteins")],
                  "health": num(g(self.D, "W", "health")) or 100.0}
        return start, player, g(self.D, "W", "start_stats") or {}

    def grade_replay(self, rows):
        """The HEAD replay of the run's own ring with REPLAY_TOL, the writes as setpath events; for x481 also the arm
        without the switch (FOLLOW). Returns {"on": rows, "off": rows} or None."""
        xs = self.xs
        inp = self.replay_inputs() if rows else None
        if inp is None:
            self.out["replay"] = {"error": "no ring rows or no start record"}
            for f in REPLAY_TOL:
                xs.grade(f"REPLAY_{f}", "unmeasured", {"why": "no replay"}, "")
            return None
        start, player, start_stats = inp
        events, book = build_events(rows, self.sets, self.sandbox)
        day_min = num(rows[0].get(OPT_DAYMIN)) or DAY_MIN
        pace, combine = self.prof["pace"], self.prof["combine"]
        if self.run_dir:
            for name, obj in (("events.json", events), ("player.json", player)):
                with open(os.path.join(self.run_dir, name), "w", encoding="utf-8", newline="\n") as fh:
                    json.dump(obj, fh, indent=1, sort_keys=True)
                xs.copied.append(name)
        self.out["model_inputs"] = {"tool": "tools/replay_live.py replay_live (ServerReplay) at HEAD, game_heal on",
                                    "ring": self.pages, "events": "events.json", "start": "start.json",
                                    "start_stats": start_stats, "player": player, "sleep_allowed": False,
                                    "death_pace": pace, "health_combine": combine, "day_minutes": day_min,
                                    "tol": {k: list(v) for k, v in REPLAY_TOL.items()}, "placement": book}
        arms = {}
        try:
            arms["on"], _ = replay(rows, events, start, pace, combine, day_min, player, start_stats)
            if self.sandbox:
                off_events = [e for e in events if not e["path"].startswith("_G.SandboxVars.")]
                arms["off"], _ = replay(rows, off_events, start, pace, combine, day_min, player, start_stats)
        except Exception as e:                     # noqa: BLE001 - recorded, graded unmeasured
            self.out["replay"] = {"error": f"{type(e).__name__}: {e}"}
            for f in REPLAY_TOL:
                xs.grade(f"REPLAY_{f}", "unmeasured", {"why": "the replay raised"}, "")
            return None
        d = replay_diff(arms["on"], rows)
        if self.run_dir:
            with open(os.path.join(self.run_dir, "replay.json"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps({"rows": arms["on"], "diff": d, "events": events,
                                     "arm_off_targets": [{"s": r.get("s"), "drain.target": r.get("drain.target")}
                                                         for r in arms.get("off") or []]},
                                    indent=1, sort_keys=True, default=str) + "\n")
            xs.copied.append("replay.json")
        self.out["replay"] = {"rows": len(arms["on"]), "fields": d.get("fields"), "classes": d.get("classes"),
                              "findings_n": len(d.get("findings") or [])}
        for f in REPLAY_TOL:
            self._g(f"REPLAY_{f}", G.grade_replay_field(d, f), f"{f} off the HEAD replay by more than {REPLAY_TOL[f][1]}")
        return arms

    def grade_x481(self, rows, arms):
        i_on = onset_index(rows, num(g(self.D, "A", "seed_age")))
        a_p = num(g(self.D, "B", "set_p", "age"))
        i_b = first_index(rows, lambda r: a_p is not None and (ring_age(r) or -1) > a_p) if a_p is not None else None
        self._g("OPEN_RATE", grade_open_rate(rows, i_on, i_b),
                "drain.rate off r_hunger(dayMin) x 24 by more than RATE_TOL_REL on an onset row")
        op = open_pred(rows, i_on)
        self.D["open"] = op
        self._g("OPEN_SLOPE", grade_open_slope(op),
                "the opening health slope off the kernel curve's for the live body by more than OPEN_TOL_REL")
        self._g("BERI_ON", grade_beri(rows, a_p), "no clinical grade and beriberi fraction within BERI_GM")
        self._g("COMBINE", grade_combine(rows, self.prof["combine"]), "a target off 100 x f1 x f3")
        w = g(self.D, "SW", "write") or {}
        a_sw = num(w.get("age_before"))
        self._g("FOLLOW", grade_follow(rows, (arms or {}).get("on"), (arms or {}).get("off"), a_sw),
                "the target followed the switch more than FOLLOW_GM game minutes after the write, or never")
        self._g("CAP", grade_cap(rows, a_sw if a_sw is not None else math.inf),
                "the capped health slope off the summed rate by more than CAP_TOL_REL")

    def grade_x482(self, rows, arms):
        self._g("SLOPE", grade_slope(rows), "the health line off r_hunger(dayMin) by more than SLOPE_TOL_REL")
        live_age, src = death_live(rows, self.polls)
        rep_age = death_replay((arms or {}).get("on"))
        last = ring_age(rows[-1]) if rows else None
        v, obs = grade_death(live_age, rep_age, last)
        obs["source"] = src
        self._g("DEATH", (v, obs), "dead more than DEATH_TOL_H off the replay's death, or alive past it")
        if live_age is None:
            self.D["projection"] = projection(rows)
        i_on = onset_index(rows, num(g(self.D, "A", "seed_age")))
        self.D["x442"] = x442_reading(live_age, num(g(self.D, "A", "seed_age")),
                                      ring_age(rows[i_on - 1]) if i_on else None)


def main(key, prefix, profile_name, artifact, session_text, pred, budget_s, driver_file):
    from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
    from pzt import fixture as fx, profile                          # noqa: E402
    from pzt.bus import resolve_side                                # noqa: E402
    from pzt.harness import lint_paths                              # noqa: E402
    from pzt.paths import new_run_dir                               # noqa: E402
    from pzt.session import Timeline, attach_clients, make_server, teardown, verify   # noqa: E402

    pre, ok = preboot(key, profile_name, prefix, driver_file)
    if not ok:
        print(json.dumps({"preboot": pre}, indent=1, default=str)[:20000])
        print("a pre-boot check failed; the session was not started")
        sys.exit(1)
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
    S = Sess(xs, key, run_dir=run_dir)
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
            L = out["logs"] = {"patterns": {"log": LOG_RX.pattern, "death": DEATH_LOG_RX.pattern}}
            if server is not None:
                logs = sorted(set([os.path.join(run_dir, "server-stdout.log"), server.log_path]))
                L["server"], L["server_echo_excluded"], L["death_lines"] = [], 0, []
                for lp in logs:
                    hits, skipped = X.grep_noecho(lp, LOG_RX, 300, G.ECHO_RX, G.NEVER_RX)
                    L["server"] += hits
                    L["server_echo_excluded"] += skipped
                    L["death_lines"] += X.grep_noecho(lp, DEATH_LOG_RX, 40, G.ECHO_RX, G.NEVER_RX)[0]
                L["mod_error"] = [ln for ln in L["server"] if MOD_ERR_RX.search(ln)][:40]
                if key == "x482" and os.path.isfile(os.path.join(run_dir, "server-stdout.log")):
                    xs.copied.append("server-stdout.log")             # the death's server record (ruling T5-1)
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
