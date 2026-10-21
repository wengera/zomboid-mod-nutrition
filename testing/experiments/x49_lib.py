"""x49_lib -- the session engine of Plan 18 Task 1, the live probe of the symptom levers before any design number is
fixed (spec docs/superpowers/specs/2026-10-21-symptoms-design.md section 2.4): added pain per body part, a deep
ENDURANCE cap, and the STRESS and UNHAPPINESS floors, each read on the dedicated server and on the client's own
moodles. Three sessions, each one boot under 10 wall minutes in a foreground call, build 42.21.0.

Built on testing/experiments/xlib.py (the bus step with its dead-bus handling, the phase runner, the wall budget, the
grade recorder, RCON, the abort, teardown and copy skeleton). It starts from x48b_lib.py, the latest lib (CLAUDE.md s5),
and keeps that lib's shape (the preboot, the gates, the main skeleton, the closing phases, the summary) on its own
constants; nothing NutritionRevamp-specific is kept, because no mod/ file is booted. The client relaunch and the server
restart are x46_lib.py's (launch_real, restart_real; frozen with x461a-x467), copied, not imported, since importing
x46_lib loads x45g_lib's prerun machinery for a mod this probe does not boot.

THE PROBE MOD. testing/experiments/TKX_Symptoms (installed only through the x49 profiles, CLAUDE.md s5). Its server
file holds, once a game minute on EveryOneMinute (the mod's own writer's cadence), a body part's added pain
(BodyPart:setAdditionalPain, re-set every minute), an ENDURANCE ceiling, STRESS and UNHAPPINESS floors and a BOREDOM
ceiling; it logs every hold's value before and after each write with the server ticks and the summed
GameTime:getMultiplier() since the previous minute event, rewrites a per-tick snapshot (TKX_Symptoms.s) with level
trackers (TKX_Symptoms.trk), keeps a per-tick ring, and dumps the log and the ring through the harness's TK.result.
Its client file rewrites TKX_Symptoms.c every client tick (the client's own stats, its BodyPart copy and its own moodle
levels) with trackers (TKX_Symptoms.ctrk). The driver reaches every function through the harness's lua.call (scalars
only) and every table through lua.read; no harness change is needed (bodypart.get and .set, moodle.level, stats.set
and .setany, time.snapshot and players already exist, docs/reference/harness-commands.md).

THE PROFILES (fixture default, admin -debug, PZTestKit + TKX_Symptoms by its path, no NutritionRevamp, Nutrition false
(ruling T18-1), SleepAllowed and SleepNeeded true): x49-levers DayLength 4 (the 90-minute day the design's magnitudes
are set for) for x491 and x493; x49-levers-d1 DayLength 1 (the 15-minute day) for x492, so the decay is read on a
second day length in the session that needs no particular day.

THE JAR (42.21, read 2026-10-21 through C:/Users/Angus/pz-b42; the cites are in the Task 1 report):
  PAIN       the stat tracks sum(part.getPain() x BodyPartType painModifier) - painReduction, rising 1/500 of the gap a
             tick and set at once when the target is lower (BodyDamage.Update @1724-@1833 L2424-L2436); BodyDamage.Update
             returns at once on a client (@21-@62 L2161-L2167), so PAIN is the server's, carried by the player-stats
             packet (#3600). BodyPart.getPain adds getAdditionalPain(true) (additionalPain + stiffness/3.5) and scales
             by the InjurySeverity switch (x0.7, x1.3; @251-@310 L1065-L1069). Torso_Lower's painModifier 0.78, Head 0.8
             (BodyPartType.<clinit> L20, L21). additionalPain falls 0.005 x getMultiplier per BodyPart.DamageUpdate,
             floored at 0 (@2312-@2353 L500-L503), which returns at once for a client's local player (@0-@30
             L154-L155): the decay is the server's alone. BodyDamage.save writes it (@264-@269 L275), load reads it
             (@270-@276 L205), and IsoGameCharacter.save/load call them (@128-@133 L5361, @113-@119 L5222).
  moodles    PAIN 10/20/50/75, UNHAPPY 20/45/60/80, STRESS 0.25/0.5/0.75/0.9, ENDURANCE 0.75/0.5/0.25/0.10
             (MoodleStat.<clinit> L10, L17, L18, L20; #2369, #3926). Moodle.Update: UNHAPPY and PAIN upward by strict >,
             STRESS from the top down on Stats.getNicotineStress (STRESS + NICOTINE_WITHDRAWAL, clamped; L253-L261,
             Stats.getNicotineStress L132-L133), ENDURANCE downward (L114-L126). The PAIN moodle recomputes only once
             every 120 Update calls (painTimer, @1743-@1766 L345-L349), so the client's level lags its PAIN.
  ENDURANCE  standing regeneration 0.0000930/3 x EnduranceRegenMultiplier x recovery x (1 - 0.85 fatigue) per
             multiplier unit (#2258); the mod's K.hybrid.END_REGEN_UNIT (x1.8 x1.6) is the worst case.
  the clock  the multiplier sums to 2 x dayMin over a game minute (#2922), so added pain falls 0.01 x dayMin a game
             minute: 0.9 at the 90-minute day, 0.15 at the 15-minute day; at about 10 server ticks a second the fall
             per wall second is the same on any day length.

THE SESSIONS:
  x491 levers  (x49-levers, DayLength 4) S (the sandbox, the clock, speed 1, the probe watching admin, the log and ring
               reset, the baseline parts and pair), P1A (pain hold on Torso_Lower (7) at A1, pairs every PAIR_EVERY_S for
               P1A_S; the client's BodyPart copy read, unsynced), P1B (the hold at A2 for P1B_S; then one harness
               bodypart.set ... sync and the client's copy read again), P2S (speed 5 for P2S_S, the hold kept), REL
               (the hold released, REL_S of pairs: the natural fall), C (speed restored; the log and ring dumped; the
               part set back to 0).
  x492 persist (x49-levers-d1, DayLength 1) S, P2D (the hold at A2 for P2D_S, then released), RELOG (setPain RELOG_V
               once, no hold; read; admin quits; the players list polled until admin is gone; admin relaunched from a
               fresh client restore in <run>/c1b; bodypart.get polled until admin is back; the first read), RESTART
               (setPain RESTART_V once; read; the log and ring dumped; the server stopped gracefully (its quit saves the
               world and the players) with admin connected; admin's client killed; the server started again on its run
               folder; admin relaunched in <run>/c1c; the first read), C.
  x493 floors  (x49-levers, DayLength 4) S, E (ENDURANCE caps END_CAPS in turn, each ARM_S of pairs after ARM_SETTLE_S
               and a tracker reset on both sides; then released and ENDURANCE set back to 1), F (BOREDOM capped at 0
               throughout; UNHAPPINESS floors 25 then 50, released and set to 0; STRESS floors 0.30 then 0.55, released
               and set to 0), C.

THE GRADES (pure; each has a failing case in testing/tests/test_x49_lib.py; a grade on no valid sample is unmeasured,
never as_predicted; every tolerance is named below, before any run). A pair is a server lua.read of TKX_Symptoms.s
and a client lua.read of TKX_Symptoms.c whose two wall midpoints sit within PAIR_GAP_MAX_S (CLAUDE.md s5).
  x491  P1_STEADY_A1, P1_STEADY_A2  the last STEADY_N valid pairs of the arm read the PAIN level the thresholds predict
               for painModifier x A (A1 20 -> 15.6: level 1; A2 40 -> 31.2: level 2) on the client and on the server.
        P1_TARGET  the server's PAIN at the arm's last valid pair within [TARGET_MIN_FRAC x mod x (A - dip), mod x A +
               TARGET_TOL], dip the fall of one game minute at the day length.
        P1_FOLLOWS on every valid pair of the pain arms, each side's PAIN level is the threshold level of that side's
               PAIN, a pair within FOLLOW_EPS of a threshold excluded (the 120-update moodle timer).
        P1_RISE    on consecutive ring ticks with PAIN under its target by RISE_GAP_MIN, the median of the step against
               (target - PAIN)/500 within RISE_TOL of 1, at least RISE_MIN_N steps.
        P2_TICK    every minute row of the pain hold at speed 1 (its predecessor a minute write of the same hold and
               value): the fall since the last write against 0.005 x the summed multiplier, within DECAY_TOL_TICKS ticks'
               fall + DECAY_TOL_ABS; at least DECAY_MIN_N rows.
        P2_GM      the same rows' summed fall over their summed game minutes within DECAY_GM_TOL of 0.01 x dayMin.
        P2_SPEED   P2_GM on the speed-5 rows.
        REL_SNAP   after the release, once PAIN reaches the falling target, every later ring tick reads PAIN within
               SNAP_TOL of mod x the part's added pain until the part reaches 0; at least SNAP_MIN_N ticks.
  x492  P2_TICK_D1, P2_GM_D1  P2_TICK and P2_GM on the 15-minute day (0.15 a game minute).
        P3_RELOG, P3_RESTART  the first server read after the rejoin holds at least SAVED_FRAC of the value read
               before the quit or the stop (saved, the jar's prediction); falsified under it (lost at or under LOST_EPS).
  x493  P4_LEVEL_<cap>  for each margin cap (0.74, 0.49, 0.24, 0.09: level 1, 2, 3, 4): every valid pair after the
               settle reads that ENDURANCE level on both sides, and both sides' trackers read it as their minimum and
               maximum over the arm; at least LEVEL_MIN_PAIRS pairs.
        P4_TIGHT   the cap 0.748 (0.002 under level 0's edge): a level-0 flip seen on the server's tracker exactly when
               the arm's median climb a minute exceeds the margin (the margin rule the mod's capAt keeps).
        P4_CLIMB   every endcap minute row's climb since the last write, per multiplier unit, in (0, END_REGEN_UNIT x
               (1 + CLIMB_TOL)]; at least CLIMB_MIN_N rows.
        P5_U25, P5_U50, P5_S30, P5_S55  the floor arms, graded as P4_LEVEL on the UNHAPPY and STRESS levels.
  all   P0_BASE    (precondition) at S's pair no part holds added pain and PAIN, STRESS (with NICOTINE_WITHDRAWAL),
               UNHAPPY and ENDURANCE read level 0 on the server: the first sight every prediction assumes (no committed
               artifact reads this fixture's PAIN, STRESS or UNHAPPINESS, so S reads it).
        Z          no probe or Lua error line in the server log, admin never parked, and no error recorded by the probe
               on either side.

FROZEN WITH ITS FIRST RUN: once a driver that imports this file has run, this file is never edited (CLAUDE.md s5).
"""
import glob
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))                                   # testing/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))
import xlib as X                                                              # noqa: E402

REPO = X.REPO
SRV = X.SRV
num = X.num
LIB_FILE = "x49_lib.py"
USER = "admin"
CLIENT = "client:admin"
MIN_FREE_GB = 12.0
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
PROBE = "TKX_Symptoms"
PROBE_DIR = "testing/experiments/TKX_Symptoms"
PROBE_SERVER = PROBE_DIR + "/42.21/media/lua/server/TKX_Symptoms_Server.lua"
PROBE_CLIENT = PROBE_DIR + "/42.21/media/lua/client/TKX_Symptoms_Client.lua"

SESSIONS = {
    "x491": {"driver": "x491_levers.py", "artifact": "levers.json", "profile": "x49-levers", "budget_s": 510.0},
    "x492": {"driver": "x492_persist.py", "artifact": "persist.json", "profile": "x49-levers-d1", "budget_s": 510.0},
    "x493": {"driver": "x493_floors.py", "artifact": "floors.json", "profile": "x49-levers", "budget_s": 510.0},
}
PROFILES = {"x49-levers": {"day_length": 4, "day_min": 90},
            "x49-levers-d1": {"day_length": 1, "day_min": 15}}

# ---- the jar's numbers (42.21; module docstring)
PAIN_TH = (10.0, 20.0, 50.0, 75.0)
UNHAPPY_TH = (20.0, 45.0, 60.0, 80.0)
STRESS_TH = (0.25, 0.5, 0.75, 0.8999999761581421)
END_TH = (0.75, 0.5, 0.25, 0.10000000149011612)
PAIN_MOD = {6: 0.699999988079071, 7: 0.7799999713897705, 8: 0.800000011920929, 9: 0.800000011920929,
            13: 0.6000000238418579, 14: 0.6000000238418579}
INJURY_FACTOR = {1: 0.699999988079071, 2: 1.0, 3: 1.2999999523162842}      # the switch's case keys are inference
DECAY_PER_UNIT = 0.005
RISE_DIV = 500.0
UNITS_PER_GM_PER_DAYMIN = 2.0
END_REGEN_BASE = 0.0000930 / 3
END_REGEN_UNIT = 0.0000930 / 3 * 1.8 * 1.6                                   # the mod's K.hybrid.END_REGEN_UNIT

# ---- the schedule
PART = 7                                 # Torso_Lower, starvation's part in the spec
A1, A2 = 20.0, 40.0                      # added pain: mod x A = 15.6 (level 1) and 31.2 (level 2)
RELOG_V = 60.0
RESTART_V = 60.0
END_CAPS = (0.748, 0.74, 0.49, 0.24, 0.09)
END_TIGHT = 0.748
END_WANT = {0.748: 1, 0.74: 1, 0.49: 2, 0.24: 3, 0.09: 4}
UNHAPPY_FLOORS = (25.0, 50.0)
UNHAPPY_WANT = {25.0: 1, 50.0: 2}
STRESS_FLOORS = (0.30, 0.55)
STRESS_WANT = {0.30: 1, 0.55: 2}
SPEED_FAST = 5

PAIR_EVERY_S = 2.0
PAIR_GAP_MAX_S = 1.0
ARM_SETTLE_S = 4.0
P1A_S = 140.0
P1B_S = 90.0
P2S_S = 25.0
REL_S = 25.0
P2D_S = 40.0
ARM_S = 26.0
SYNC_WAIT_S = 2.0
DEPART_CAP_S = 40.0
REJOIN_CAP_S = 60.0
RELAUNCH_TIMEOUT_S = 150
RESTART_TIMEOUT_S = 180
RESTART_NEED_S = 230.0                   # the wall the restart arm needs (stop, start, relaunch) before it begins
RESULT_WAIT_S = 20.0

# ---- the tolerances (named before any run)
STEADY_N = 5
TARGET_MIN_FRAC = 0.85
TARGET_TOL = 0.01
FOLLOW_EPS = 1.5                         # PAIN units (the moodle's 120-update timer, at most ~0.6 a second of rise)
FOLLOW_EPS_STRESS = 0.01
FOLLOW_EPS_UNHAPPY = 0.5
FOLLOW_EPS_END = 0.002
RISE_GAP_MIN = 0.5
RISE_TOL = 0.15
RISE_MIN_N = 50
DECAY_TOL_TICKS = 1.5
DECAY_TOL_ABS = 0.001
DECAY_MIN_N = 5
DECAY_GM_TOL = 0.05
SNAP_TOL = 0.05
SNAP_MIN_N = 20
SAVED_FRAC = 0.5
LOST_EPS = 0.01
LEVEL_MIN_PAIRS = 3
CLIMB_TOL = 0.02
CLIMB_MIN_N = 3

S_PATHS = ("online", "n", "ms", "age", "mult", "trackPart", "pain", "part", "endurance", "stress", "nicotine",
           "unhappy", "boredom", "fatigue", "lvPain", "lvEnd", "lvStress", "lvUnhappy")
C_PATHS = ("n", "ms", "cpart", "pain", "part", "endurance", "stress", "nicotine", "unhappy", "boredom", "lvPain",
           "lvEnd", "lvStress", "lvUnhappy")
TRK_PATHS = ("n", "ms") + tuple(f"{k}{e}" for k in ("lvPain", "lvEnd", "lvStress", "lvUnhappy") for e in ("Min", "Max"))
ERR_PATHS = ("lastError", "cLastError", "version")

HARNESS_FILES = {"PZTestKit_Server.lua": LUA_DIR + "/server/PZTestKit_Server.lua",
                 "PZTestKit_Core.lua": LUA_DIR + "/shared/PZTestKit_Core.lua"}
HARNESS_MARKERS = {
    "PZTestKit_Server.lua": tuple(f'TK.register("{c}", function(' for c in (
        "bodypart.get", "bodypart.set", "moodle.level", "stats.set", "stats.setany", "stats.all", "players")),
    "PZTestKit_Core.lua": tuple(f'TK.register("{c}", function(' for c in ("lua.call", "lua.read", "time.snapshot",
                                                                         "lua.global")) + ("function TK.result(",),
}
PROBE_MARKERS = {
    PROBE_SERVER: ('T.version = "1"', "function T.hold(", "function T.release(", "function T.setPain(",
                   "function T.dump(", "function T.onMinute(", "function T.onTick(", "function T.trkReset(",
                   "function T.watch(", "function T.ringOn("),
    PROBE_CLIENT: ('T.version = "1"', "function T.cTick(", "function T.creset("),
}
ECHO_RX = re.compile(r"PZTK: ")
NEVER_RX = re.compile(r"(?!x)x")
LOG_RX = re.compile(r"TKX_Symptoms|LuaError|STACK TRACE|lua error|attempted index|tried to call nil", re.I)
MOD_ERR_RX = re.compile(r"TKX_Symptoms_\w+\.lua|STACK TRACE|attempted index|tried to call nil")

PRED = {
    "P1_STEADY_A1": "Torso_Lower added pain 20 (PAIN target 0.78 x 20 = 15.6): PAIN moodle level 1 on client and server",
    "P1_STEADY_A2": "added pain 40 (target 31.2): PAIN moodle level 2 on client and server",
    "P1_TARGET": "the server's PAIN reaches painModifier x A less at most one game minute's fall, by the arm's end",
    "P1_FOLLOWS": "each side's PAIN moodle level is the threshold level of that side's PAIN (10/20/50/75, strict >)",
    "P1_RISE": "PAIN rises 1/500 of its gap to the target a server tick (BodyDamage.Update L2434)",
    "P2_TICK": "added pain falls 0.005 x the summed multiplier between minute writes (BodyPart.DamageUpdate L501)",
    "P2_GM": "added pain falls 0.01 x dayMin a game minute: 0.9 at the 90-minute day",
    "P2_SPEED": "the same 0.9 a game minute at speed 5",
    "REL_SNAP": "released, PAIN follows the falling target down at once each tick (set when the target is lower)",
    "P2_TICK_D1": "added pain falls 0.005 x the summed multiplier between minute writes on the 15-minute day",
    "P2_GM_D1": "added pain falls 0.01 x dayMin a game minute: 0.15 at the 15-minute day",
    "P3_RELOG": "added pain is saved: BodyDamage.save writes it (L275), so a relog keeps it",
    "P3_RESTART": "added pain is saved: a graceful restart keeps it",
    "P4_TIGHT": "a cap 0.002 under level 0's edge flips to level 0 between writes when the climb a minute exceeds 0.002",
    "P4_CLIMB": "endurance climbs at most END_REGEN_UNIT per multiplier unit between writes (#2258's worst case)",
    "P5_U25": "UNHAPPINESS floor 25: UNHAPPY level 1 on both sides",
    "P5_U50": "UNHAPPINESS floor 50: UNHAPPY level 2 on both sides",
    "P5_S30": "STRESS floor 0.30: STRESS level 1 on both sides",
    "P5_S55": "STRESS floor 0.55: STRESS level 2 on both sides",
    "Z": "no probe or Lua error line in the server log, admin never parked, no probe-recorded error",
    "P0_BASE": "(precondition) the first sight: no part holds added pain; PAIN, STRESS, UNHAPPY, ENDURANCE at level 0",
}
for _c in END_CAPS:
    if _c != END_TIGHT:
        PRED[f"P4_LEVEL_{_c}"] = f"ENDURANCE cap {_c}: ENDURANCE moodle level {END_WANT[_c]} on both sides, no flip"
SESSION_GRADES = {
    "x491": ("P0_BASE", "P1_STEADY_A1", "P1_STEADY_A2", "P1_TARGET", "P1_FOLLOWS", "P1_RISE", "P2_TICK", "P2_GM",
             "P2_SPEED", "REL_SNAP", "Z"),
    "x492": ("P0_BASE", "P2_TICK_D1", "P2_GM_D1", "P3_RELOG", "P3_RESTART", "Z"),
    "x493": (("P0_BASE",) + tuple(f"P4_LEVEL_{c}" for c in END_CAPS if c != END_TIGHT)
             + ("P4_TIGHT", "P4_CLIMB", "P5_U25", "P5_U50", "P5_S30", "P5_S55", "Z")),
}
CONSTANTS = {k: v for k, v in dict(globals()).items() if re.match(r"^[A-Z][A-Z0-9_]+$", k)
             and isinstance(v, (int, float, str, bool, tuple, dict)) and k not in ("REPO", "HERE", "PRED")}


# ================================================================ pure helpers
def g(d, *path):
    for k in path:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def level_of(kind, v):
    """The moodle level vanilla's Moodle.Update gives the stat value v (kind pain, unhappy, stress or endurance)."""
    v = num(v)
    if v is None:
        return None
    if kind == "endurance":
        lv = 4
        for i, th in enumerate(END_TH):
            if v > th:
                lv = i
                break
        return lv
    th = {"pain": PAIN_TH, "unhappy": UNHAPPY_TH, "stress": STRESS_TH}[kind]
    if kind == "stress":
        v = min(1.0, max(0.0, v))
    return sum(1 for t in th if v > t)


def near_threshold(kind, v, eps):
    th = {"pain": PAIN_TH, "unhappy": UNHAPPY_TH, "stress": STRESS_TH, "endurance": END_TH}[kind]
    v = num(v)
    return v is None or any(abs(v - t) <= eps for t in th)


def pain_target(a, part=PART, injury=2):
    return PAIN_MOD[part] * INJURY_FACTOR.get(injury, 1.0) * a


def dip_per_gm(day_min):
    return DECAY_PER_UNIT * UNITS_PER_GM_PER_DAYMIN * day_min


def valid_pairs(pairs, arm=None):
    return [p for p in pairs if p.get("valid") and (arm is None or p.get("arm") == arm)]


def make_pair(tag, arm, s, ws, c, wc):
    """One pair from the server's and the client's lua.read values and their wall midpoints."""
    gap = abs(ws - wc) if (ws is not None and wc is not None) else None
    ok = bool(s) and bool(c) and s.get("online") is True and gap is not None and gap <= PAIR_GAP_MAX_S
    return {"tag": tag, "arm": arm, "s": s, "c": c, "ws": ws, "wc": wc, "gap": gap, "valid": ok}


def minute_rows(doc, key=None, value=None, ms0=None, ms1=None):
    """The dump's minute rows, in order, optionally one hold's (key and value) inside [ms0, ms1)."""
    rows = [r for r in (g(doc, "minutes") or []) if isinstance(r, dict)]
    out = []
    for r in rows:
        if key is not None and r.get("key") != key:
            continue
        if value is not None and (num(r.get("value")) is None or abs(num(r.get("value")) - value) > 1e-9):
            continue
        ms = num(r.get("ms"))
        if ms0 is not None and (ms is None or ms < ms0):
            continue
        if ms1 is not None and (ms is None or ms >= ms1):
            continue
        out.append(r)
    return out


def gaps(row_sets):
    """Consecutive (prev, row) pairs inside each of row_sets (lists of one hold's rows, one list per window) where row
    is a minute write whose predecessor was a minute write (an arm's row lands mid-minute, so the minute after it
    spans less than its summed multiplier). A pair never spans two windows."""
    out = []
    for rows in row_sets:
        for prev, row in zip(rows, rows[1:]):
            if row.get("ev") == "minute" and prev.get("ev") == "minute":
                out.append((prev, row))
    return out


def combine(results):
    """Several grade results as one: falsified if any is, as_predicted only if every one is, else unmeasured."""
    verdicts = [r[0] for r in results]
    if "falsified" in verdicts:
        v = "falsified"
    elif verdicts and all(x == "as_predicted" for x in verdicts):
        v = "as_predicted"
    else:
        v = "unmeasured"
    samples = []
    for r in results:
        samples += list(r[2])
    return v, [r[1] for r in results], samples


# ================================================================ the pure grades
def grade_steady(pairs, arm, lv_key, want, n=STEADY_N):
    """The arm's last n valid pairs read level `want` on both sides."""
    vp = valid_pairs(pairs, arm)[-n:]
    obs = [{"tag": p["tag"], "client": g(p, "c", lv_key), "server": g(p, "s", lv_key)} for p in vp]
    if len(vp) < n:
        return "unmeasured", {"want": want, "pairs": obs, "why": f"{len(vp)} valid pairs, {n} needed"}, []
    bad = [o for o in obs if o["client"] != want or o["server"] != want]
    return ("as_predicted" if not bad else "falsified"), {"want": want, "pairs": obs, "off": bad}, obs


def grade_target(pairs, arm, a, day_min, part=PART, injury=2):
    """The server's PAIN at the arm's last valid pair inside [TARGET_MIN_FRAC x mod x (a - dip), mod x a + TOL]."""
    vp = valid_pairs(pairs, arm)
    if not vp:
        return "unmeasured", {"why": "no valid pair"}, []
    pain = num(g(vp[-1], "s", "pain"))
    hi = pain_target(a, part, injury) + TARGET_TOL
    lo = TARGET_MIN_FRAC * pain_target(a - dip_per_gm(day_min), part, injury)
    obs = {"pain": pain, "lo": lo, "hi": hi, "tag": vp[-1]["tag"]}
    if pain is None:
        return "unmeasured", obs, []
    return ("as_predicted" if lo <= pain <= hi else "falsified"), obs, [pain]


def grade_follows(pairs, arms, kind, stat_key, lv_key, eps, extra_key=None):
    """Each side's level is level_of(kind, that side's stat) on every valid pair of `arms` not within eps of a
    threshold; extra_key (nicotine) is added to the stat first (the STRESS moodle's getNicotineStress)."""
    used, bad = [], []
    for p in pairs:
        if not p.get("valid") or p.get("arm") not in arms:
            continue
        for side in ("s", "c"):
            v = num(g(p, side, stat_key))
            if v is not None and extra_key is not None:
                v = v + (num(g(p, side, extra_key)) or 0.0)
            if v is None or near_threshold(kind, v, eps):
                continue
            want, got = level_of(kind, v), g(p, side, lv_key)
            row = {"tag": p["tag"], "side": side, "stat": v, "want": want, "got": got}
            used.append(row)
            if got != want:
                bad.append(row)
    if not used:
        return "unmeasured", {"n": 0, "why": "no valid pair away from a threshold"}, used
    return ("as_predicted" if not bad else "falsified"), {"n": len(used), "off": bad[:20]}, used


def grade_rise(ticks, part=PART, injury=2):
    """On consecutive ring ticks with PAIN under its target by RISE_GAP_MIN, the median of the step against
    (target - PAIN)/500 within RISE_TOL of 1 over at least RISE_MIN_N steps."""
    mod = PAIN_MOD[part] * INJURY_FACTOR.get(injury, 1.0)
    ratios = []
    for a, b in zip(ticks, ticks[1:]):
        if num(b.get("n")) is None or num(a.get("n")) is None or num(b["n"]) != num(a["n"]) + 1:
            continue
        pa, pb, part_a = num(a.get("pain")), num(b.get("pain")), num(a.get("part"))
        if pa is None or pb is None or part_a is None:
            continue
        gap = mod * part_a - pa
        if gap <= RISE_GAP_MIN:
            continue
        ratios.append((pb - pa) / (gap / RISE_DIV))
    if len(ratios) < RISE_MIN_N:
        return "unmeasured", {"n": len(ratios), "why": f"fewer than {RISE_MIN_N} rise steps"}, ratios
    med = statistics.median(ratios)
    obs = {"n": len(ratios), "median_ratio": med, "p10": sorted(ratios)[len(ratios) // 10],
           "p90": sorted(ratios)[(9 * len(ratios)) // 10]}
    return ("as_predicted" if abs(med - 1.0) <= RISE_TOL else "falsified"), obs, ratios


def grade_decay_tick(row_sets):
    """Every minute-to-minute gap of row_sets (gaps()): the fall (the write before less this row's before) against
    DECAY_PER_UNIT x the row's summed multiplier, within DECAY_TOL_TICKS of one tick's fall plus DECAY_TOL_ABS."""
    obs, bad = [], []
    for prev, row in gaps(row_sets):
        a, b, m, t = num(prev.get("after")), num(row.get("before")), num(row.get("mult")), num(row.get("ticks"))
        if a is None or b is None or m is None or not t:
            continue
        fall, pred = a - b, DECAY_PER_UNIT * m
        tol = DECAY_TOL_TICKS * DECAY_PER_UNIT * (m / t) + DECAY_TOL_ABS
        o = {"tick": row.get("tick"), "fall": fall, "pred": pred, "tol": tol, "ticks": t, "mult": m}
        obs.append(o)
        if abs(fall - pred) > tol:
            bad.append(o)
    if len(obs) < DECAY_MIN_N:
        return "unmeasured", {"n": len(obs), "why": f"fewer than {DECAY_MIN_N} minute gaps"}, obs
    return ("as_predicted" if not bad else "falsified"), {"n": len(obs), "off": bad[:20]}, obs


def grade_decay_gm(row_sets, day_min):
    """The gaps' (gaps()) summed fall over their summed game minutes within DECAY_GM_TOL of 0.01 x dayMin."""
    fall, gm, n = 0.0, 0.0, 0
    for prev, row in gaps(row_sets):
        a, b, a0, a1 = num(prev.get("after")), num(row.get("before")), num(prev.get("age")), num(row.get("age"))
        if None in (a, b, a0, a1) or a1 <= a0:
            continue
        fall += a - b
        gm += (a1 - a0) * 60.0
        n += 1
    want = dip_per_gm(day_min)
    if n < DECAY_MIN_N or gm <= 0:
        return "unmeasured", {"n": n, "want": want, "why": f"fewer than {DECAY_MIN_N} minute gaps"}, []
    per = fall / gm
    obs = {"n": n, "fall": fall, "game_minutes": gm, "per_gm": per, "want": want, "rel": per / want - 1.0}
    return ("as_predicted" if abs(per / want - 1.0) <= DECAY_GM_TOL else "falsified"), obs, [per]


def grade_snap(ticks, part=PART, injury=2):
    """After the release: from the first tick PAIN reads at or above mod x part (the target fell under it), every tick
    reads PAIN within SNAP_TOL of mod x part until the part reaches 0."""
    mod = PAIN_MOD[part] * INJURY_FACTOR.get(injury, 1.0)
    started, used, bad = False, [], []
    for t in ticks:
        pain, pv = num(t.get("pain")), num(t.get("part"))
        if pain is None or pv is None:
            continue
        if pv <= 0:
            break
        tgt = mod * pv
        if not started:
            started = pain >= tgt - SNAP_TOL
            if not started:
                continue
        o = {"n": t.get("n"), "pain": pain, "target": tgt}
        used.append(o)
        if abs(pain - tgt) > SNAP_TOL:
            bad.append(o)
    if len(used) < SNAP_MIN_N:
        return "unmeasured", {"n": len(used), "why": f"fewer than {SNAP_MIN_N} snapped ticks"}, used
    return ("as_predicted" if not bad else "falsified"), {"n": len(used), "off": bad[:20]}, used


def grade_persist(before, back):
    """Saved when the first read after the rejoin holds at least SAVED_FRAC of the value read before."""
    b0, b1 = num(before), num(back)
    obs = {"before": b0, "back": b1, "saved_frac": SAVED_FRAC}
    if b0 is None or b1 is None or b0 <= LOST_EPS:
        return "unmeasured", obs, []
    obs["state"] = "saved" if b1 >= SAVED_FRAC * b0 else ("lost" if b1 <= LOST_EPS else "partial")
    return ("as_predicted" if obs["state"] == "saved" else "falsified"), obs, [b1]


def grade_hold_level(pairs, arm, lv_key, want, trk_s, trk_c):
    """Every valid pair of the arm reads level `want` on both sides, and both trackers' min and max read it."""
    vp = valid_pairs(pairs, arm)
    obs = {"want": want, "pairs": len(vp),
           "trk_server": {k: g(trk_s, k) for k in (lv_key + "Min", lv_key + "Max", "n")},
           "trk_client": {k: g(trk_c, k) for k in (lv_key + "Min", lv_key + "Max", "n")}}
    if len(vp) < LEVEL_MIN_PAIRS or not num(g(trk_s, "n")) or not num(g(trk_c, "n")):
        obs["why"] = "too few pairs or an empty tracker"
        return "unmeasured", obs, []
    off = [{"tag": p["tag"], "client": g(p, "c", lv_key), "server": g(p, "s", lv_key)} for p in vp
           if g(p, "c", lv_key) != want or g(p, "s", lv_key) != want]
    trk_off = [k for t in (trk_s, trk_c) for k in (lv_key + "Min", lv_key + "Max") if g(t, k) != want]
    obs["off"], obs["trk_off"] = off[:20], trk_off
    return ("as_predicted" if not off and not trk_off else "falsified"), obs, vp


def climbs(row_sets):
    """Endcap holds' climbs a gap (gaps()): (row.before - prev.after), per minute and per multiplier unit."""
    out = []
    for prev, row in gaps(row_sets):
        a, b, m = num(prev.get("after")), num(row.get("before")), num(row.get("mult"))
        if a is None or b is None or not m:
            continue
        out.append({"tick": row.get("tick"), "climb": b - a, "per_unit": (b - a) / m, "mult": m})
    return out


def grade_tight(trk_s, rows, margin):
    """A level-0 flip on the server's tracker exactly when the median climb a minute of the arm's rows exceeds the
    margin."""
    cl = climbs([rows])
    obs = {"margin": margin, "n": len(cl), "trk_server": {k: g(trk_s, k) for k in ("lvEndMin", "lvEndMax", "n")}}
    if not cl or not num(g(trk_s, "n")) or g(trk_s, "lvEndMin") is None:
        obs["why"] = "no climb row or an empty tracker"
        return "unmeasured", obs, []
    med = statistics.median(c["climb"] for c in cl)
    obs["median_climb"] = med
    obs["flip_predicted"] = med > margin
    obs["flip_seen"] = g(trk_s, "lvEndMin") == 0
    return ("as_predicted" if obs["flip_seen"] == obs["flip_predicted"] else "falsified"), obs, cl


def grade_climb(cl):
    """Every climb per multiplier unit (climbs() rows; several arms' joined, each arm's gaps its own) in
    (0, END_REGEN_UNIT x (1 + CLIMB_TOL)]."""
    if len(cl) < CLIMB_MIN_N:
        return "unmeasured", {"n": len(cl), "why": f"fewer than {CLIMB_MIN_N} climb rows"}, cl
    hi = END_REGEN_UNIT * (1.0 + CLIMB_TOL)
    bad = [c for c in cl if not (0.0 < c["per_unit"] <= hi)]
    med = statistics.median(c["per_unit"] for c in cl)
    obs = {"n": len(cl), "hi": hi, "median_per_unit": med, "median_over_base": med / END_REGEN_BASE, "off": bad[:20]}
    return ("as_predicted" if not bad else "falsified"), obs, cl


def grade_base(pair, parts_reply):
    """The first sight the predictions assume: no part holds added pain, and PAIN, STRESS (with nicotine), UNHAPPINESS
    and ENDURANCE all read level 0 on the server at S's pair."""
    s = g(pair, "s") or {}
    parts = parts_reply.get("parts") if isinstance(parts_reply, dict) else None
    obs = {"pain": s.get("pain"), "stress": s.get("stress"), "nicotine": s.get("nicotine"),
           "unhappy": s.get("unhappy"), "endurance": s.get("endurance"), "parts": None}
    if not (pair or {}).get("valid") or not isinstance(parts, list) or not parts:
        obs["why"] = "no valid S pair or no part read"
        return "unmeasured", obs, []
    pained = [p.get("index") for p in parts if isinstance(p, dict) and (num(p.get("additionalPain")) or 0.0) != 0.0]
    obs["parts"], obs["pained"] = len(parts), pained
    levels = {"pain": level_of("pain", s.get("pain")),
              "stress": level_of("stress", (num(s.get("stress")) or 0.0) + (num(s.get("nicotine")) or 0.0)),
              "unhappy": level_of("unhappy", s.get("unhappy")), "endurance": level_of("endurance", s.get("endurance"))}
    obs["levels"] = levels
    ok = not pained and all(v == 0 for v in levels.values())
    return ("as_predicted" if ok else "falsified"), obs, parts


def grade_z(log_errors, parked, probe_errors):
    """No probe or Lua error line in the server log, admin never parked, no probe-recorded error."""
    obs = {"log_errors": list(log_errors or [])[:20], "parked": parked, "probe_errors": probe_errors}
    if parked is None:
        return "unmeasured", obs, []
    bad = bool(log_errors) or parked is True or any(v for v in (probe_errors or {}).values())
    return ("falsified" if bad else "as_predicted"), obs, [1]


# ================================================================ the session
class Sess:
    def __init__(self, xs, key, day_min, run_dir=None, launch=None, restart=None, stop=None):
        self.xs = xs
        self.key = key
        self.day_min = day_min
        self.out = xs.out
        self.run_dir = run_dir
        self.launch = launch
        self.restart_fn = restart
        self.stop_fn = stop
        self.D = self.out.setdefault("readings", {})
        self.pairs = self.out.setdefault("pairs", [])
        self.arms = self.out.setdefault("arms", [])
        self.speeds = self.out.setdefault("speeds", [])
        self.dumps = self.out.setdefault("dumps", {})
        self.restore_to = None
        self.cur_speed = None
        self.injury = 2

    # -- plumbing
    def k(self, tag, side, cmd, args="", log=True):
        return self.xs.keep(self.xs.step(tag, side, cmd, args, log=log))

    def call(self, tag, side, fn, *args, log=True):
        return self.k(tag, side, "lua.call", " ".join([f"{PROBE}.{fn}"] + [str(a) for a in args]), log=log)

    @staticmethod
    def mid(a):
        w0, w1 = num(a.get("wall")), num(a.get("wall_after"))
        if w0 is None or w1 is None:
            return None
        return (w0 + w1) / 2.0

    def read(self, tag, side, root, paths, log=False):
        a = self.k(tag, side, "lua.read", " ".join([root] + list(paths)), log=log)
        v = a.get("values") if isinstance(a.get("values"), dict) else {}
        return dict(v), self.mid(a)

    def pair(self, tag, arm):
        s, ws = self.read(tag + "_s", SRV, f"{PROBE}.s", S_PATHS)
        c, wc = self.read(tag + "_c", CLIENT, f"{PROBE}.c", C_PATHS)
        p = make_pair(tag, arm, s, ws, c, wc)
        self.pairs.append(p)
        return p

    def hold_pairs(self, arm, secs):
        end = self.xs.clock() + secs
        i = 0
        while self.xs.clock() < end:
            self.xs.check()
            t0 = self.xs.clock()
            self.pair(f"{arm}_{i}", arm)
            i += 1
            self.xs.sleep(max(0.0, min(PAIR_EVERY_S - (self.xs.clock() - t0), end - self.xs.clock())))
        return i

    def snap(self, tag):
        return self.xs.snap(tag, log=True)

    def speed(self, n, tag):
        r = self.xs.rcon(f"settimespeed {int(n)}", tag)
        row = {"want": n, "rcon_ok": r.get("ok"), "epoch_ms": int(self.xs.clock() * 1000), "tag": tag}
        if not r.get("ok"):
            row["fallback"] = self.k(tag + "_mult", SRV, "time.multiplier", f"{n}").get("raw")
        s = self.snap(tag + "_t")
        row.update({"trueMult": num(s.get("trueMult")), "mult": num(s.get("mult")), "age": num(s.get("worldAge"))})
        row["ok"] = row["trueMult"] is not None and abs(row["trueMult"] - n) < 1e-6
        self.speeds.append(row)
        self.cur_speed = n
        return row

    def trk(self, tag):
        s, _ = self.read(tag + "_trk_s", SRV, f"{PROBE}.trk", TRK_PATHS, log=True)
        c, _ = self.read(tag + "_trk_c", CLIENT, f"{PROBE}.ctrk", TRK_PATHS, log=True)
        return {"server": s, "client": c}

    def trk_reset(self, tag):
        self.call(tag + "_trk_rs", SRV, "trkReset")
        self.call(tag + "_trk_rc", CLIENT, "creset")

    def arm(self, name, kind, a, b=None, secs=None, settle=True):
        """Arm a hold and record it; then (settle) ARM_SETTLE_S, a tracker reset on both sides, secs of pairs and the
        trackers read."""
        args = (USER, kind, a) if b is None else (USER, kind, a, b)
        rec = {"arm": name, "kind": kind, "a": a, "b": b, "epoch_ms": int(self.xs.clock() * 1000)}
        rec["reply"] = self.call(name + "_hold", SRV, "hold", *args)
        self.arms.append(rec)
        if settle:
            self.xs.sleep(ARM_SETTLE_S)
            self.trk_reset(name)
        rec["settled_epoch_ms"] = int(self.xs.clock() * 1000)
        if secs:
            rec["pairs"] = self.hold_pairs(name, secs)
            rec["trk"] = self.trk(name)
        rec["end_epoch_ms"] = int(self.xs.clock() * 1000)
        return rec

    def dump(self, tag):
        after = time.time() - 1.0
        r = self.call(f"dump_{tag}", SRV, "dump", tag)
        doc = self.xs.wait_doc(f"tkxs-{tag}", after, RESULT_WAIT_S) if r.get("r1") is True else None
        self.dumps[tag] = {"reply": {k: r.get(k) for k in ("ok", "r1", "r2", "r3", "err")}, "doc": doc}
        return doc

    def part_read(self, tag, side=SRV, part=PART):
        a = self.k(tag, side, "bodypart.get", f"{USER} {part}")
        parts = a.get("parts") if isinstance(a.get("parts"), list) else []
        row = parts[0] if parts and isinstance(parts[0], dict) else {}
        return {"ok": a.get("ok"), "additionalPain": num(row.get("additionalPain")), "wall": self.mid(a),
                "row": row, "raw": a.get("raw")}

    def poll(self, tag, fn, cap_s, sleep_s=0.5):
        end = self.xs.clock() + cap_s
        n, done, last = 0, False, None
        while True:
            done, last = fn()
            n += 1
            if done or self.xs.clock() >= end:
                break
            self.xs.check()
            self.xs.sleep(sleep_s)
        if not done:
            self.xs.note(f"{tag}: not reached inside {cap_s} s")
        return {"done": done, "last": last, "polls": n}

    def errors_read(self, tag):
        s, _ = self.read(tag + "_err_s", SRV, PROBE, ERR_PATHS, log=True)
        c, _ = self.read(tag + "_err_c", CLIENT, PROBE, ERR_PATHS, log=True)
        return {"server": s.get("lastError"), "client": c.get("cLastError")}

    # -- phase runner
    def closing_names(self):
        return ("C",)

    def body_run(self, phases):
        closing = set(self.closing_names())
        for name, fn in phases:
            if self.xs.parked():
                self.out["abort"] = f"admin parked in the debugger before phase {name}"
                break
            stopped = self.out.get("budget_stop") or self.xs.bus_dead or self.out.get("stop_reason")
            if stopped and name not in closing:
                self.out.setdefault("skipped_phases", []).append(name)
                self.xs.note(f"phase {name} skipped: an earlier phase stopped")
                continue
            self.xs.run_phase(name, fn)

    def phases(self):
        common = [("S", self.phase_S)]
        if self.key == "x491":
            body = [("P1A", self.phase_P1A), ("P1B", self.phase_P1B), ("P2S", self.phase_P2S), ("REL", self.phase_REL)]
        elif self.key == "x492":
            body = [("P2D", self.phase_P2D), ("RELOG", self.phase_RELOG), ("RESTART", self.phase_RESTART)]
        elif self.key == "x493":
            body = [("E", self.phase_E), ("F", self.phase_F)]
        else:
            raise ValueError(f"unknown session {self.key}")
        return common + body + [("C", self.phase_C)]

    # -- the shared phases
    def phase_S(self):
        P = self.D["S"] = {}
        P["players"] = self.xs.step("S_players", SRV, "players")["ack"]
        P["sandbox"], _ = self.read("S_sv", SRV, "_G", ("SandboxVars.DayLength", "SandboxVars.InjurySeverity",
                                                       "SandboxVars.Nutrition", "SandboxVars.EnduranceRegenMultiplier",
                                                       "SandboxVars.StatsDecrease", "TK.version"), log=True)
        inj = num(P["sandbox"].get("SandboxVars.InjurySeverity"))
        self.injury = int(inj) if inj is not None and int(inj) in INJURY_FACTOR else 2
        if inj is None or int(inj) != 2:
            self.xs.note(f"S: InjurySeverity read {inj}; the PAIN predictions use the factor of {self.injury}")
        P["clock"] = self.snap("S_clock")
        self.restore_to = num(P["clock"].get("trueMult"))
        P["speed1"] = self.speed(1, "S_speed1")
        P["watch"] = self.call("S_watch", SRV, "watch", USER)
        P["reset"] = self.call("S_reset", SRV, "reset")
        P["ring"] = self.call("S_ring", SRV, "ringOn", "true")
        P["cpart"] = self.call("S_cpart", CLIENT, "cpartSet", PART)
        P["parts"] = self.k("S_parts", SRV, "bodypart.get", f"{USER} all")
        P["stats_all"] = self.k("S_stats_all", SRV, "stats.all", USER)
        P["errors"] = self.errors_read("S")
        self.xs.sleep(1.0)
        P["pair"] = self.pair("S_pair", "S")

    def phase_C(self):
        P = self.D["C"] = {}
        P["release"] = self.call("C_release", SRV, "release", "all")
        v = self.restore_to if self.restore_to is not None else 1.0
        if abs(v - round(v)) < 1e-6 and round(v) >= 1:
            P["restore"] = self.speed(int(round(v)), "C_restore")
        else:
            P["restore"] = {"reply": self.k("C_restore_mult", SRV, "time.multiplier", f"{v}").get("raw"),
                            "restore_to": v}
        P["errors"] = self.errors_read("C")
        P["dump"] = bool(self.dump("end"))
        if self.key in ("x491", "x492"):
            P["part_zero"] = self.k("C_part0", SRV, "bodypart.set", f"{USER} {PART} additionalPain 0")

    # -- x491
    def phase_P1A(self):
        rec = self.arm("P1A", "pain", PART, A1, P1A_S, settle=False)
        self.D["P1A"] = {"client_part_unsynced": self.part_read("P1A_cpart", CLIENT), "pairs": rec.get("pairs")}

    def phase_P1B(self):
        rec = self.arm("P1B", "pain", PART, A2, P1B_S, settle=False)
        P = self.D["P1B"] = {"pairs": rec.get("pairs"), "client_part_before_sync": self.part_read("P1B_cpart0", CLIENT)}
        P["sync"] = self.k("P1B_sync", SRV, "bodypart.set", f"{USER} {PART} additionalPain {A2} sync")
        self.xs.sleep(SYNC_WAIT_S)
        P["client_part_after_sync"] = self.part_read("P1B_cpart1", CLIENT)
        P["server_part_after_sync"] = self.part_read("P1B_spart1", SRV)

    def phase_P2S(self):
        P = self.D["P2S"] = {}
        P["fast"] = self.speed(SPEED_FAST, "P2S_fast")
        P["pairs"] = self.hold_pairs("P2S", P2S_S)
        P["slow"] = self.speed(1, "P2S_slow")

    def phase_REL(self):
        P = self.D["REL"] = {"epoch_ms": int(self.xs.clock() * 1000)}
        P["release"] = self.call("REL_release", SRV, "release", "pain", PART)
        P["pairs"] = self.hold_pairs("REL", REL_S)

    # -- x492
    def phase_P2D(self):
        rec = self.arm("P2D", "pain", PART, A2, P2D_S, settle=False)
        self.D["P2D"] = {"pairs": rec.get("pairs"), "release": self.call("P2D_release", SRV, "release", "pain", PART)}

    def players(self, tag):
        a = self.xs.step(tag, SRV, "players", log=False).get("ack")
        return a if isinstance(a, list) else None

    def rejoin_read(self, P, label, sub):
        P["launch"] = self.launch(self, USER, sub) if self.launch else {"error": "no launcher"}
        if not g(P, "launch", "ready_took"):
            self.xs.note(f"{label}: admin was not ready after the relaunch")
            return

        def back():
            r = self.part_read(f"{label}_back", SRV)
            return (r.get("ok") is True and r.get("additionalPain") is not None), r
        w = self.poll(f"{label}_back", back, REJOIN_CAP_S)
        P["back_polls"] = w["polls"]
        P["back"] = w["last"] if w["done"] else None
        P["watch"] = self.call(f"{label}_watch", SRV, "watch", USER)
        self.xs.sleep(ARM_SETTLE_S)
        P["pair"] = self.pair(f"{label}_pair", label)

    def phase_RELOG(self):
        P = self.D["RELOG"] = {}
        P["set"] = self.call("RELOG_set", SRV, "setPain", USER, PART, RELOG_V)
        P["before"] = self.part_read("RELOG_before", SRV)
        c = self.xs.clients.get(USER)
        q = {"wall0": self.xs.wall()}
        try:
            q["rc"] = c.quit() if c is not None else None
        except Exception as e:                       # noqa: BLE001 - recorded
            q["error"] = f"{type(e).__name__}: {e}"
        q["wall1"] = self.xs.wall()
        self.xs.clients.pop(USER, None)
        P["quit"] = q

        def gone():
            lst = self.players("RELOG_players")
            return (lst is not None and USER not in lst), lst
        P["depart"] = self.poll("RELOG_depart", gone, DEPART_CAP_S)
        P["depart_wall"] = self.xs.wall()
        if not P["depart"]["done"]:
            self.xs.note("RELOG: admin never left the server inside the cap; no rejoin")
            return
        self.rejoin_read(P, "RELOG", "c1b")

    def phase_RESTART(self):
        P = self.D["RESTART"] = {}
        if self.xs.budget_s - self.xs.wall() < RESTART_NEED_S:
            P["skipped"] = f"wall {self.xs.wall()} s leaves under {RESTART_NEED_S} s of the budget"
            self.xs.note("RESTART: skipped: " + P["skipped"])
            return
        P["set"] = self.call("RESTART_set", SRV, "setPain", USER, PART, RESTART_V)
        P["before"] = self.part_read("RESTART_before", SRV)
        P["dump"] = bool(self.dump("prestop"))
        P["stop"] = self.stop_fn(self) if self.stop_fn else {"error": "no stopper"}
        c = self.xs.clients.get(USER)
        try:
            if c is not None:
                c.kill()
            P["client_killed"] = c is not None
        except Exception as e:                       # noqa: BLE001 - recorded
            P["client_kill_error"] = f"{type(e).__name__}: {e}"
        self.xs.clients.pop(USER, None)
        if not g(P, "stop", "exited"):
            self.xs.note("RESTART: the server did not exit; no restart")
            return
        P["restart"] = self.restart_fn(self, "up") if self.restart_fn else {"error": "no restarter"}
        if not g(P, "restart", "ok"):
            return
        P["clock"] = self.snap("RESTART_clock")
        self.rejoin_read(P, "RESTART", "c1c")

    # -- x493
    def phase_E(self):
        P = self.D["E"] = {"arms": []}
        for cap in END_CAPS:
            P["arms"].append(self.arm(f"E_{cap}", "endcap", cap, secs=ARM_S)["arm"])
        P["release"] = self.call("E_release", SRV, "release", "endcap")
        P["restore"] = self.k("E_restore", SRV, "stats.set", f"{USER} endurance 1")

    def phase_F(self):
        P = self.D["F"] = {"arms": []}
        P["bored"] = self.call("F_bored", SRV, "hold", USER, "boredcap", 0)
        for fl in UNHAPPY_FLOORS:
            P["arms"].append(self.arm(f"U_{fl:g}", "unhappy", fl, secs=ARM_S)["arm"])
        P["u_release"] = self.call("F_u_release", SRV, "release", "unhappy")
        P["u_zero"] = self.k("F_u_zero", SRV, "stats.setany", f"{USER} UNHAPPINESS 0")
        for fl in STRESS_FLOORS:
            P["arms"].append(self.arm(f"S_{fl:g}", "stress", fl, secs=ARM_S)["arm"])
        P["s_release"] = self.call("F_s_release", SRV, "release", "stress")
        P["s_zero"] = self.k("F_s_zero", SRV, "stats.setany", f"{USER} STRESS 0")

    # -- the grades
    def _g(self, name, res, falsifier, extra=None):
        verdict, observed, samples = res
        return self.xs.grade(name, verdict, observed, falsifier, extra=extra, samples=samples)

    def doc(self):
        return g(self.dumps, "end", "doc") or {}

    def arm_rec(self, name):
        for a in self.arms:
            if a.get("arm") == name:
                return a
        return {}

    def window(self, name):
        a = self.arm_rec(name)
        return a.get("epoch_ms"), a.get("end_epoch_ms")

    def ticks_between(self, doc, ms0, ms1):
        return [t for t in (g(doc, "ticks") or []) if isinstance(t, dict) and num(t.get("ms")) is not None
                and (ms0 is None or num(t["ms"]) >= ms0) and (ms1 is None or num(t["ms"]) < ms1)]

    def grade_all(self):
        z_logs = g(self.out, "logs", "mod_error") or []
        probe_err = {"S": g(self.D, "S", "errors"), "C": g(self.D, "C", "errors")}
        probe_err = {k: v for k, v in probe_err.items() if v}
        flat = {f"{k}.{s}": e for k, v in probe_err.items() for s, e in v.items()}
        self._g("P0_BASE", grade_base(g(self.D, "S", "pair"), g(self.D, "S", "parts") or {}),
                "a part holding added pain, or PAIN, STRESS, UNHAPPY or ENDURANCE off level 0 at the first sight")
        if self.key == "x491":
            self.grade_x491()
        elif self.key == "x492":
            self.grade_x492()
        elif self.key == "x493":
            self.grade_x493()
        self._g("Z", grade_z(z_logs, self.out.get("admin_lua_error"), flat), "a probe or Lua error, or admin parked")

    def grade_x491(self):
        doc = self.doc()
        key = f"pain:{PART}"
        ms_fast = g(self.D, "P2S", "fast", "epoch_ms")
        ms_slow = g(self.D, "P2S", "slow", "epoch_ms")
        ms_rel = g(self.D, "REL", "epoch_ms")
        self._g("P1_STEADY_A1", grade_steady(self.pairs, "P1A", "lvPain", level_of("pain", pain_target(A1, PART,
                self.injury))), "a client or server PAIN level other than the predicted in the arm's last pairs")
        self._g("P1_STEADY_A2", grade_steady(self.pairs, "P1B", "lvPain", level_of("pain", pain_target(A2, PART,
                self.injury))), "a client or server PAIN level other than the predicted in the arm's last pairs")
        self._g("P1_TARGET", combine([grade_target(self.pairs, "P1A", A1, self.day_min, PART, self.injury),
                                      grade_target(self.pairs, "P1B", A2, self.day_min, PART, self.injury)]),
                "the server's PAIN outside its band at an arm's end")
        self._g("P1_FOLLOWS", grade_follows(self.pairs, ("P1A", "P1B", "P2S", "REL"), "pain", "pain", "lvPain",
                                            FOLLOW_EPS), "a side's PAIN level off its own PAIN's threshold level")
        rise = self.ticks_between(doc, *self.window("P1A")) + self.ticks_between(doc, *self.window("P1B"))
        self._g("P1_RISE", grade_rise(rise, PART, self.injury), "the median rise step off (gap)/500 by over RISE_TOL")
        slow = [minute_rows(doc, key, A1, *self.window("P1A")), minute_rows(doc, key, A2, *self.window("P1B"))]
        self._g("P2_TICK", combine([grade_decay_tick([slow[0]]), grade_decay_tick([slow[1]])]),
                "a minute gap's fall off 0.005 x its summed multiplier beyond the tolerance")
        self._g("P2_GM", grade_decay_gm(slow, self.day_min), "the fall a game minute off 0.01 x dayMin by over 5 %")
        fast = [minute_rows(doc, key, A2, ms_fast, ms_slow)]
        self._g("P2_SPEED", grade_decay_gm(fast, self.day_min), "the speed-5 fall a game minute off 0.01 x dayMin")
        self._g("REL_SNAP", grade_snap(self.ticks_between(doc, ms_rel, None), PART, self.injury),
                "a released tick's PAIN off mod x part by over SNAP_TOL")

    def grade_x492(self):
        doc = g(self.dumps, "prestop", "doc") or self.doc()
        rows = [minute_rows(doc, f"pain:{PART}", A2, *self.window("P2D"))]
        self._g("P2_TICK_D1", grade_decay_tick(rows), "a minute gap's fall off 0.005 x its summed multiplier")
        self._g("P2_GM_D1", grade_decay_gm(rows, self.day_min), "the fall a game minute off 0.01 x dayMin by over 5 %")
        self._g("P3_RELOG", grade_persist(g(self.D, "RELOG", "before", "additionalPain"),
                                          g(self.D, "RELOG", "back", "additionalPain")),
                "the first read after the rejoin under SAVED_FRAC of the value before the quit")
        self._g("P3_RESTART", grade_persist(g(self.D, "RESTART", "before", "additionalPain"),
                                            g(self.D, "RESTART", "back", "additionalPain")),
                "the first read after the restart under SAVED_FRAC of the value before the stop")

    def grade_x493(self):
        doc = self.doc()
        for cap in END_CAPS:
            a = self.arm_rec(f"E_{cap}")
            if cap == END_TIGHT:
                rows = minute_rows(doc, "endcap", cap, a.get("epoch_ms"), a.get("end_epoch_ms"))
                self._g("P4_TIGHT", grade_tight(g(a, "trk", "server"), rows, 0.75 - cap),
                        "a level-0 flip seen without a climb over the margin, or none seen with one")
                continue
            self._g(f"P4_LEVEL_{cap}", grade_hold_level(self.pairs, f"E_{cap}", "lvEnd", END_WANT[cap],
                                                        g(a, "trk", "server"), g(a, "trk", "client")),
                    "a pair or a tracker reading an ENDURANCE level other than the predicted")
        cl_rows = []
        for cap in END_CAPS:
            a = self.arm_rec(f"E_{cap}")
            cl_rows += climbs([minute_rows(doc, "endcap", cap, a.get("epoch_ms"), a.get("end_epoch_ms"))])
        self.D["climbs"] = cl_rows
        res = grade_climb(cl_rows)
        self._g("P4_CLIMB", res, "a climb per multiplier unit outside (0, END_REGEN_UNIT x 1.02]")
        for name, kind, fl, want, lv in (("P5_U25", "U", 25.0, 1, "lvUnhappy"), ("P5_U50", "U", 50.0, 2, "lvUnhappy"),
                                         ("P5_S30", "S", 0.30, 1, "lvStress"), ("P5_S55", "S", 0.55, 2, "lvStress")):
            a = self.arm_rec(f"{kind}_{fl:g}")
            self._g(name, grade_hold_level(self.pairs, f"{kind}_{fl:g}", lv, want, g(a, "trk", "server"),
                                           g(a, "trk", "client")),
                    "a pair or a tracker reading a level other than the predicted")



# ================================================================ the pre-boot checks (pure over files)
def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def markers_ok(files, markers, repo=REPO):
    """Every marker in each file (files: name -> repo path; markers: name -> strings)."""
    found = {}
    for name, rel in files.items():
        text = _read(os.path.join(repo, rel)) or ""
        found[name] = {mk: (mk in text) for mk in markers[name]}
    return found, bool(found) and all(all(d.values()) for d in found.values())


def harness_markers_ok(repo=REPO):
    return markers_ok(HARNESS_FILES, HARNESS_MARKERS, repo)


def probe_markers_ok(repo=REPO):
    return markers_ok({p: p for p in PROBE_MARKERS}, PROBE_MARKERS, repo)


def profile_doc_checks(name, doc, text=""):
    """A profile's TOML against PROFILES[name]: its header names its own file; fixture default; the one admin client;
    PZTestKit and TKX_Symptoms by PROBE_DIR, no NutritionRevamp; Nutrition false and the profile's DayLength; sleep on;
    two TKX_Symptoms.version verify rows (server and client)."""
    spec = PROFILES.get(name)
    if spec is None:
        return {"known_profile": False}
    mods = [m.get("id") for m in doc.get("mods") or []]
    paths = {m.get("id"): m.get("path") for m in doc.get("mods") or []}
    sb = doc.get("sandbox") or {}
    srv = doc.get("server") or {}
    vr = doc.get("verify") or []
    return {
        "header_names_file": text.startswith(f"# testing/profiles/{name}.toml"),
        "fixture_default": doc.get("fixture") == "default",
        "one_admin": doc.get("clients") == [USER],
        "mods": mods == ["PZTestKit", PROBE],
        "probe_path": paths.get(PROBE) == PROBE_DIR,
        "no_mod": "NutritionRevamp" not in mods,
        "nutrition_off": sb.get("Nutrition") is False,
        "day_length": sb.get("DayLength") == spec["day_length"],
        "sleep_on": srv.get("SleepAllowed") is True and srv.get("SleepNeeded") is True,
        "verify_rows": sorted(v.get("side") for v in vr) == ["client", "server"]
        and all(v.get("args") == f"{PROBE}.version" and v.get("cmd") == "lua.global" for v in vr),
    }


def preboot(key, driver_file, repo=REPO):
    """The driver names its session; no artifact of the session committed; the profile's TOML; the harness and probe
    markers. Returns (checks, ok)."""
    import tomllib
    spec = SESSIONS.get(key)
    if spec is None:
        return {"known_session": False}, False
    base = os.path.basename(driver_file)
    c = {"known_session": True, "driver_file": base == spec["driver"], "driver_prefix": base.startswith(key + "_")}
    c["no_prior_artifact"] = not glob.glob(os.path.join(repo, "testing", "artifacts", key + "-*"))
    text = _read(os.path.join(repo, "testing", "profiles", spec["profile"] + ".toml"))
    try:
        prof = profile_doc_checks(spec["profile"], tomllib.loads(text or ""), text or "")
    except ValueError as e:
        prof = {"profile_read": False, "error": f"{type(e).__name__}: {e}"}
    c["profile_checks"] = prof
    c["harness_markers"], c["harness_ok"] = harness_markers_ok(repo)
    c["probe_markers"], c["probe_ok"] = probe_markers_ok(repo)
    skip = ("profile_checks", "harness_markers", "probe_markers")
    good = all(v is True for k, v in c.items() if k not in skip) and bool(prof) and all(
        v is True for k, v in prof.items() if k != "error")
    return c, good


def parse_argv(argv, driver_file):
    """A driver takes no argument (Plan 17 close: a driver refuses any argument it does not define); returns the
    refusal text, or None for a bare call."""
    if argv:
        return f"{os.path.basename(driver_file)} takes no arguments; a bare call boots the session"
    return None


# ================================================================ the live run
def launch_real(make_client, prof, rec_fx, started, tl):
    """x46_lib's relaunch: a fresh client restore in <run>/<sub>, started and waited ready."""
    def launch(S, user, sub):
        c, restored = make_client(os.path.join(S.run_dir, sub), user, S.xs.server, rec_fx,
                                  safemode=prof.safemode, launcher=prof.launcher)
        c.start()
        started.append(c)
        S.xs.clients[user] = c
        tl.mark("client_launch", user=user, which=sub, restored=restored)
        took = c.wait_ready(timeout=min(prof.client_timeout, RELAUNCH_TIMEOUT_S))
        tl.mark("client_ready", user=user, which=sub, took=took)
        return {"restored": restored, "ready_took": took, "wall": S.xs.wall()}
    return launch


def stop_real(tl):
    """The graceful stop: pzt's Server.stop (quit on stdin, which saves the world and the players, then the wait; a
    kill only on its own timeout). Only this session's own server is touched."""
    def stop(S):
        srv = S.xs.server
        out = {"pid": getattr(getattr(srv, "proc", None), "pid", None), "wall0": S.xs.wall()}
        S.xs.persist()
        tl.mark("server_stop", pid=out["pid"])
        try:
            out["rc"] = srv.stop()
            out["exited"] = not srv.alive
        except Exception as e:                       # noqa: BLE001 - recorded
            out["exited"] = False
            out["error"] = f"{type(e).__name__}: {e}"
        out["wall1"] = S.xs.wall()
        return out
    return stop


def restart_real(prof, run_dir, tl):
    """x46_lib's: the same Server object started again on its run folder's cache (the world as the engine last saved
    it), its log in a second file so the first stays whole."""
    def restart(S, tag):
        srv = S.xs.server
        out = {"log": f"server-stdout-{tag}.log"}
        try:
            srv._started.clear()
            srv.log_path = os.path.join(run_dir, out["log"])
            srv.bus.reset()
            out["took"] = srv.start(timeout=min(prof.server_timeout, RESTART_TIMEOUT_S))
            out["pid"] = srv.proc.pid
            out["ok"] = True
            tl.mark("server_restarted", pid=out["pid"], took=out["took"])
        except Exception as e:                       # noqa: BLE001 - recorded
            out["ok"] = False
            out["error"] = f"{type(e).__name__}: {e}"
        S.xs.copied.append(out["log"])
        return out
    return restart


def summary(out, run_id, run_dir):
    print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                      "bus_dead": out.get("bus_dead"), "error": out.get("error"), "abort": out.get("abort"),
                      "budget_stop": out.get("budget_stop"), "skipped_phases": out.get("skipped_phases"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "summary_error": out.get("summary_error"), "logs_error": out.get("logs_error"),
                      "run_id": run_id, "run_dir": run_dir, "memory": out.get("memory"),
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str)[:8000])


def main(key, driver_file):
    from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
    from pzt import fixture as fx, profile                          # noqa: E402
    from pzt.bus import resolve_side                                # noqa: E402
    from pzt.harness import lint_paths                              # noqa: E402
    from pzt.paths import new_run_dir                               # noqa: E402
    from pzt.session import Timeline, attach_clients, make_client, make_server, teardown, verify   # noqa: E402

    spec = SESSIONS[key]
    pre, ok = preboot(key, driver_file)
    if not ok:
        print(json.dumps({"preboot": pre}, indent=1, default=str)[:20000])
        print("a pre-boot check failed; the session was not started")
        sys.exit(1)
    prof = profile.load(spec["profile"])
    rec_fx = fx.load(prof.fixture)
    run_id, run_dir = new_run_dir(key)
    tl = Timeline()
    clients, started = {}, []
    holder = {"server": None}
    out = {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
           "world_changes": {"restored": f"fixture {prof.fixture} restored into the run dir", "left_in_place": []}}
    pred = {k: PRED[k] for k in SESSION_GRADES[key]}
    xs = X.Xs(out, node=lambda side: resolve_side(side, holder["server"], clients), tl=tl, clients=clients,
              ask=ask, budget_s=spec["budget_s"], predictions=pred, user=USER)
    xs.path = os.path.join(run_dir, spec["artifact"])
    S = Sess(xs, key, PROFILES[spec["profile"]]["day_min"], run_dir=run_dir,
             launch=launch_real(make_client, prof, rec_fx, started, tl), restart=restart_real(prof, run_dir, tl),
             stop=stop_real(tl))
    doctor_clean, doctor_text = doctor()
    out.update({
        "run_id": run_id, "session_key": key, "driver": os.path.basename(driver_file), "lib": LIB_FILE, "user": USER,
        "profile": prof.report(), "preboot": pre,
        "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                    "build": rec_fx.get("build")},
        "argv": sys.argv[1:], "commit": git_say("rev-parse", "--short", "HEAD"),
        "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
        "harness_lua_dirty": git_dirty(LUA_DIR)[0],
        "probe_commit": git_say("log", "-1", "--format=%h", "--", PROBE_DIR),
        "probe_dirty": git_dirty(PROBE_DIR)[0],
        "xlib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/xlib.py"),
        "lib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/" + LIB_FILE),
        "driver_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/" + spec["driver"]),
        "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
        "predictions": pred, "constants": CONSTANTS, "meta": {"budget_s": spec["budget_s"]},
    })
    if not doctor_clean:
        xs.refuse("doctor not clean; the session was not started (CLAUDE.md s5)")
    if out["harness_lua_dirty"] or out["probe_dirty"]:
        xs.refuse("the harness Lua or the probe mod is dirty; commit before the boot (CLAUDE.md s5)")
    m0 = xs.mem("preboot")
    if not X.memory_ok(m0["free_gb"], MIN_FREE_GB):
        xs.refuse(f"free memory {m0['free_gb']} GB under {MIN_FREE_GB} GB; the session was not started")
    out["lint_errors"] = lint_paths(profile.lint_sources(prof, prof.sources))
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
        clients.update(attach_clients(run_dir, prof, server, rec_fx, tl, users=[USER], started=started))
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
            Lg = out["logs"] = {"patterns": {"log": LOG_RX.pattern, "mod_error": MOD_ERR_RX.pattern}}
            if server is None:
                return
            logs = sorted(set([os.path.join(run_dir, "server-stdout.log"), server.log_path]))
            Lg["server"], Lg["server_echo_excluded"] = [], 0
            for lp in logs:
                hits, skipped = X.grep_noecho(lp, LOG_RX, 300, ECHO_RX, NEVER_RX)
                Lg["server"] += hits
                Lg["server_echo_excluded"] += skipped
            Lg["mod_error"] = [ln for ln in Lg["server"] if MOD_ERR_RX.search(ln)][:40]
            for c in every:
                lines, _ = X.grep_noecho(c.console, LOG_RX, 80, ECHO_RX, NEVER_RX)
                Lg.setdefault("clients", {})[getattr(c, "username", "?")] = lines

        xs.finish(teardown, hard_kill, every, read_logs=read_logs, grade_all=S.grade_all)
        xs.mem("after")
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, spec["artifact"])
    summary(out, run_id, run_dir)
    return out
