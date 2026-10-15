"""x43_strength_lib -- the session engine of Plan 13's four live acceptance runs (Tasks 19 to 22): x431_beyondten.py,
x432_offline.py, x433_creation.py and x434_growth.py. Started from x42c_calib_lib.py (frozen with x423) and x411_smoke.py
(the staged-copy gate, the quit, the clock raise and the rejoin), with x42b_levers_lib.py's respawn route (x192's), on
testing/experiments/xlib.py. Every session boots the STAGED release copy (release/plan13-x43, `python
tools/release_pack.py stage mod/NutritionRevamp --out release/plan13-x43`, made before the boots; the driver checks its
MANIFEST against release_pack.manifest() of a clean mod/NutritionRevamp at HEAD and refuses on a mismatch; CLAUDE.md
s5, x201), Nutrition false (ruling T18-1), DayLength 1 (a game minute is 0.625 s of wall at true multiplier 1), build
42.21.0. The subject is admin (fixture default, the -debug client) in Tasks 19, 20 and 22, and bob (fixture two, the
release user-role client, with admin attached first) in Task 21.

THE RECORD READS: the mod's in-memory record of a user (lua.read record:<user>, never through S.get) as the body's
scalars and its seven-day rings (sig7, p7, eb7, mass7, bandWeek), in two lua.read calls (64 paths a call). Every field
but the day accumulators (pDay, ebDay, eeDay, inDay, alcDay, sigDay), lastAgeH and wday moves only at the day close
(NR_Server_Metabolism closeDay, K.strength.day, K.partition.closeDay), so two reads a tick apart agree on them.

TASK 19 (x431, profile x43-beyondten: fixture default, PZTestKit, the staged copy, BeyondTen by its workshop item
3765241705, read-only, copied in by the harness). Phases:
  S   the setting: BeyondTen's API version, the level guard's sentinel NR_StrengthGuardInstalled (a type read of the
      table, its wrapper and its orig; xpUpdate.checkForLosingLevel and BeyondTen's saved original as types), the strength
      parameters the server runs (NutritionRevamp.server.options.strength: R, M5, Fnm, b, incidental, xpPerSet), the
      record's body, Strength's level and XP, BeyondTen's stored XP and its cumulative costs to 12 and 13
      (BeyondTen.GetTotalMasteryCost through lua.call).
  W12 body.N0 and body.T re-read, then record.set body.lm fOfLevel(12.3, N0, T) (the strength level's inverse at the
      server's R, M5, Fnm and b) and body.levelDue true; once the Strength minute's levelWrites rises and levelDue reads
      false: Strength's level and XP polled until the XP reads the level-9 total (BeyondTen's park) or W12_PARK_S,
      BeyondTen's stored XP, the client mirror's body_level (requestMirror, then NutritionRevamp.client.mirror).
  G   body.sigDay and the capture's count (xpStats.captures) read, xp.grant admin Strength 1000, both and the level
      read after SETTLE_S (BeyondTen's AddXP listener re-parks the XP inside the grant, so the landing is the count).
  R   the forced rust pass: moddata.set admin strengthUpTimer RUST_TIMER (vanilla's xpUpdate.everyTenMinutes then
      grants getLoosingXpValue() and calls checkForLosingLevel, XpUpdate.lua:301-308, at the next ten-minute event);
      the Strength minute's xpStats.ignored (a non-positive Strength grant reached the listener) and the guard's
      stats.guarded polled for RUST_CAP_S; the level read after; then moddata.set admin strengthUpTimer RUST_RESET.
  W95 body.N0 and body.T re-read, record.set body.lm fOfLevel(9.5, N0, T) and body.levelDue true; after the write:
      Strength's level and XP, BeyondTen's stored XP, and a same-second pair of the server's and admin's client
      stats.get trait lists.

TASK 20 (x432, profile x43-offline: fixture default, PZTestKit, the staged copy). Phases:
  S   the record whole, the clock, Strength's XP.
  OFF the record whole (pre), Strength's XP and level (pre); admin quits; once the server lists no player the record
      whole (away), the multiplier read (time.snapshot trueMult), time.multiplier AWAY_MULT until the world age reaches
      the first hour AWAY_HOUR of a day at least AWAY_MIN_H past the departure's lastAgeH; in a finally the multiplier
      back to the value read before, read back (one retry); only with the read-back equal does admin rejoin (a fresh
      fixture restore in <run>/c1b, never under a near-stopped clock, #3788); the first minute after first sight is the
      first record read whose lastAgeH left the departure's; the record whole (first) and Strength's XP and level
      (first) then.
  B   the next world-day boundary: time.multiplier BOUNDARY_MULT (restored, read back, in a finally) until the world age
      passes the boundary; the record whole once dayIndex moves (after) and again AFTER_HOLD_S later (hold), with
      NutritionRevamp.server.metabolism.stats.days before and after.

TASK 21 (x433, profile x43-creation: fixture two, admin then bob, PZTestKit, the staged copy). Phases:
  S   the sandbox's CharacterFreePoints and NegativeTraitsPenalty, every case's traits' server definitions (trait.def:
      cost and exclusions), bob's profession (witness.chain getDescriptor.getCharacterProfession).
  Ca..Ce  five respawns of bob through x192's route (health.reduce bob 110; ISPostDeathUI onRespawn; the spawn list's
      clickNext; CoopCharacterCreation accept), each but (a) after creation.picks arms its list: (a) none; (b) Strong
      Overweight; (c) Strong VeryUnderweight; (d) Feeble Obese Overweight with D_EXTRAS over the budget; (e) Weak
      Underweight. Each landing is NutritionRevamp.server.creation.stats.created rising; then bob's profession, the
      record's body, and PAIRS same-second pairs (the server's stats.get and perk.xp Strength beside bob's client
      stats.get and perk.xp Strength). The server log's "creation: bob loses" and "creation: bob muscle=" lines are
      read after the session and cut by the created lines.

TASK 22 (x434, profile x43-growth: fixture default, PZTestKit, the staged copy, [sandbox.NR] StrengthTimeScale 30 and
StrengthIncidentalWeight 1). Phases:
  S   the record, the strength parameters the server runs (ts, incidental, xpPerSet, R), the clock.
  D   GROWTH_DAYS graded closes (one ungraded lead-in close first when the session starts at or past LEAD_HOUR). Each
      day: time.multiplier DAY_MULT (restored in a finally); GRANTS server xp.grant admin Strength GRANT_XP
      (xpPerSet x 20 / 7 / GRANTS, so the day's signal is 20/7 sets) about one game hour apart, Strength's XP read
      before each (the level-10 cap gate, Task 0's lesson: a window at or above CAP_XP is unmeasured); at hour
      SLOW_HOUR the multiplier back to the value read before; at PLACE_MIN game minutes before the boundary the record
      whole (pre), then record.set body.pDay P_GKG x the body mass and body.ebDay E_KCAL; once dayIndex moves the
      record whole (post), Strength's level, and the server's stats.get trait list.

THE GRADES (pure; each has a failing case in testing/tests/test_x43_strength_lib.py; a grade on zero samples is
unmeasured, never as_predicted):
  19_sentinel  the sentinel a table with a wrapper function in place; falsified: absent or no wrapper.
  19_write12   native Strength 10, Strength XP 337500 (the level-9 total, BeyondTen's park), BeyondTen's stored XP
               masteryXp(L) over its own costs to 12 and 13 (rel 1e-6), the mirror's body_level within 0.005 of L.
  19_grant     the native level stays 10 and body.sigDay rises by 1000 x the incidental weight (rel 1e-6; the grant
               lands outside a Fitness set); unmeasured: no capture, or a close inside the window.
  19_rust      a rust grant reached the listener and the level reads 10 after it; unmeasured: no rust grant seen.
               Reading only: which wrapper is outermost (stats.guarded rose: the mod's guard returned first).
  19_write95   native 9, XP 412500 (level 9's total plus half its cost), STRONG held and no other Strength band on
               the server and on admin's client in a same-second pair.
  20_gap       the gap at least AWAY_MIN_H, and dayIndex, sig7, p7, eb7, mass7, bandWeek, grace, Pk, lm, fm and lx equal
               across pre, away and first (exactly).
  20_xp        Strength's XP and level equal before the quit and after the rejoin.
  20_close     after the boundary dayIndex is first's + 1 (and still at hold), the server's closed-day count rose by
               one, and each ring shifted exactly once (slot i after = slot i + 1 first, i = 1..6).
  21_<case>_body    lm, fm, F0, Fc, Pk and N0 of the record equal the creation table (strength_level.trait_start under
                    the profession's boost, the plan's fat and thin table) to 1e-9.
  21_<case>_state   the server's and the client's weight equal lm + lx + fm (WEIGHT_TOL), both Strength levels
                    floor(level + 1e-9), both trait lists hold the level's band and the surviving weight pick and no
                    other band or weight trait, and no stripped trait, in a same-second pair.
  21_<case>_strips  the server log's strip lines for the case name exactly the expected strips (ruling 13-16, fix 3:
                    exclusions first, the costlier of a pair, a tie by name; then the budget, the costliest positive
                    pick first) in that order.
  22_close<k>  the close's lm and T equal the kernel's replay of the record's own pre-close body under the close's
               recorded inputs (S = body.S, p = p7[7] / the pre-close mass, E = eb7[7], tdee = max(eeDay pre, ree(lm)),
               alcohol alcDay / mass) to LM_TOL and T_TOL (ruling 8-R: live against its own replay); unmeasured when the
               replay reads tdee (the energy gate below saturation at the pre-close eeDay and EE_MARGIN above it).
  22_level<k>  the native level floor(level(lm, N0, T) + 1e-9) and its band held on the server after the close.

Reply shapes the lib reads are the harness's own (@reply lines): lua.read {ok, side, root, n, values, tables, types,
missing}; record.set {ok, side, user, path, key, keyType, before, beforeType, after, afterType}; perk.xp {perk, user,
side, xp, level, serverWorldAge} (client {perk, side, xp, level}); xp.grant {ok, perk, amount, side, xpBefore, xpAfter,
levelBefore, levelAfter}; bt.stored {ok, loaded, stored, apiVersion, perk}; stats.get {weight, traitList, ...,
worldAge, wall}; lua.call {ok, side, path, nargs, r1, r2, r3}; lua.callm {ok, side, path, method, nargs, r1, r2, r3};
lua.global {side, name, resolved, type, value}; moddata.set {user, key, value, side, keyCount, keys, serverWorldAge};
health.reduce {ok, side, requested, before, after, health, parts}; creation.picks {ok, armed, picks}; trait.def {ok,
side, trait, field, cost, free, xpBoosts, xpBoostsRead, exclusive, granted, label, description}; witness.chain {ok,
value, hops, failedAt}; time.snapshot {worldAge, hour, minutes, mult, trueMult, wall}; time.multiplier a string;
players a list of usernames or {}.

FROZEN WITH ITS FIRST RUN: once x431 has run, this file is never edited (CLAUDE.md s5); a later change is a new file.
"""
import glob
import json
import math
import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))                    # testing/
sys.path.insert(0, HERE)                                     # experiments/
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tests"))   # testing/tests/ (kernel.strength_level)

import xlib as X                                                 # noqa: E402

REPO = X.REPO
SRV = X.SRV
LIB_FILE = "x43_strength_lib.py"
NR = "NutritionRevamp"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
MOD_DIR = "mod/NutritionRevamp"
STAGE_OUT = "release/plan13-x43"
STAGE_ROOT = STAGE_OUT + "/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
STAGED_SHARED = STAGE_MOD + "/common/media/lua/shared"
STAGED_CORE = "common/media/lua/shared/NR_Core.lua"
MANIFEST_NAME = "MANIFEST.json"
HARNESS_FILES = {"PZTestKit_Server.lua": LUA_DIR + "/server/PZTestKit_Server.lua",
                 "PZTestKit_Client.lua": LUA_DIR + "/client/PZTestKit_Client.lua",
                 "PZTestKit_Core.lua": LUA_DIR + "/shared/PZTestKit_Core.lua"}
HARNESS_MARKERS = {
    "PZTestKit_Server.lua": ('TK.register("bt.stored", function(argv)', 'TK.register("record.set", function(argv)',
                             'TK.register("xp.grant", function(argv)', 'TK.register("perk.xp", function(argv)'),
    "PZTestKit_Client.lua": ('TK.register("creation.picks", function(argv)', 'TK.register("perk.xp", function(argv)'),
    "PZTestKit_Core.lua": ('TK.register("lua.read", function(argv)', 'TK.register("lua.call", function(argv)',
                           'TK.register("trait.def", function(argv)'),
}
MIN_FREE_GB = 12.0
POLL_S = 0.3
SETTLE_S = 2.0
GAME_MIN_S = 0.625                     # wall seconds a game minute at true multiplier 1, DayLength 1
CAP_XP = 487500.0                      # Strength's getTotalXpForLevel(10) (#2102)
TOTALS = (0.0, 1500.0, 4500.0, 10500.0, 19500.0, 37500.0, 67500.0, 127500.0, 217500.0, 337500.0, 487500.0)  # #2102
L_MAX = 10
BANDS = (("weak", 1), ("feeble", 4), (None, 5), ("stout", 8), ("strong", 10))   # #2157
MUSCLE = ("weak", "feeble", "stout", "strong")
WEIGHTS = ("emaciated", "veryunderweight", "underweight", "overweight", "obese")
READY_CAP_S = 90.0
MIN_RUNS = 3
STR_STATS = f"{NR}.server.strength.stats"
STR_XP = f"{NR}.server.strength.xpStats"
OPT_STR = f"{NR}.server.options.strength"
WRITE_CAP_S = 20.0
REL_TOL = 1e-6
# Task 19
W12_LEVEL = 12.3
W95_LEVEL = 9.5
W12_PARK_S = 8.0
PARK_XP = 337500.0                     # the level-9 total (BeyondTen's reservoir, its RESERVOIR_LEVEL 9)
GRANT_19 = 1000.0
MIRROR_TOL = 0.005                     # body_level carries two decimals' precision (ruling 13-19)
XP_TOL = 1.0
RUST_TIMER = "25000"                   # xpUpdate.everyTenMinutes rusts past 20000 (XpUpdate.lua:301)
RUST_RESET = "-50000"                  # vanilla's start value (XpUpdate.lua:331)
RUST_CAP_S = 30.0
REQUEST_GAP_S = 5.5                    # past NR_Server_Bus.lua's REQUEST_GAP_MS (5000)
ARRIVE_CAP_S = 8.0
PAIR_GAP_MAX_S = 1.0
# Task 20
AWAY_MULT = 30.0
AWAY_MIN_H = 72.0
AWAY_HOUR = 20.0
AWAY_POLL_S = 2.0
AWAY_CAP_S = 240.0
DEPART_CAP_S = 30.0
PRE_LATE_HOUR = 23.0                   # a pre read this late waits out the boundary first (no close inside the gap)
FIRST_CAP_S = 40.0
BOUNDARY_MULT = 8.0
BOUNDARY_CAP_S = 120.0
AFTER_HOLD_S = 6.0
GAP_FIELDS = ("dayIndex", "grace", "Pk", "lm", "fm", "lx")
RING_KEYS = ("sig7", "p7", "eb7", "mass7")
# Task 21
CLI_BOB = "client:bob"
DEATH_CAP_S = 20.0
UI_CAP_S = 30.0
CREATE_CAP_S = 15.0
LAND_CAP_S = 60.0
PAIR_DELAY_S = 4.0
WEIGHT_TOL = 0.01
BODY_TOL = 1e-9
D_EXTRAS = ("ThickSkinned", "KeenHearing", "FastHealer", "Brave", "Crafty", "Dextrous", "SpeedDemon")
CASES = (("a", ()), ("b", ("Strong", "Overweight")), ("c", ("Strong", "VeryUnderweight")),
         ("d", ("Feeble", "Obese", "Overweight") + D_EXTRAS), ("e", ("Weak", "Underweight")))
H = 1.70
H2 = H * H
FAT_FMI = {None: 4.5, "overweight": 7.5, "obese": 12.5}          # K.body.FAT_FMI (S2056), the plan's Task 9
THIN = {"underweight": (18.0, 1.5), "veryunderweight": (16.5, 1.0)}   # K.body.THIN (bmi, fmi), the plan's Task 9
EXCLUDES = {"underweight": ("weak", "feeble"), "veryunderweight": ("weak", "feeble")}   # ruling 13-46
PROFESSIONS_TXT = os.path.join("media", "scripts", "generated", "characters", "character_professions.txt")
# Task 22
GROWTH_DAYS = 3
LEAD_HOUR = 12.0
DAY_MULT = 8.0
GRANTS = 10
GRANT_GAP_H = 1.0
SETS_A_DAY = 20.0 / 7.0
SLOW_HOUR = 23.0
PLACE_MIN = 4.0
P_GKG = 2.0
E_KCAL = 260.0
EE_MARGIN = 150.0
LM_TOL = 1e-6
T_TOL = 1e-9
CLOSE_CAP_S = 30.0
DAY_CAP_S = 300.0
ECHO_RX = re.compile(r"PZTK: ")
NEVER_RX = re.compile(r"(?!x)x")
LOG_RX = re.compile(r"NutritionRevamp|BeyondTen|LuaError|STACK TRACE|lua error|attempted index|tried to call nil", re.I)
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|failed:|STACK TRACE|attempted index|tried to call nil")
STRIP_RX = re.compile(r"\[NutritionRevamp\] creation: (\S+) loses (.+?) \((.*)\)\s*$")
CREATED_RX = re.compile(r"\[NutritionRevamp\] creation: (\S+) muscle=(\S+) weight=(\S+) prof=(\S+)")

BODY_SCALARS = ("lm", "fm", "lx", "F0", "Fc", "Pk", "N0", "T", "Tgrace", "grace", "S", "sigDay", "dayIndex", "wday",
                "lastAgeH", "levelDue", "wroteL", "pDay", "ebDay", "eeDay", "inDay", "inDayClosed", "alcDay", "band",
                "fatT", "thinT", "fmRef", "tDisuse", "bornAge", "sex", "delta", "lm0dis", "at", "S")
WEEK_N = 7


def body_paths():
    """The two lua.read path lists of the record whole (each at most 64 paths)."""
    first = ["body." + k for k in dict.fromkeys(BODY_SCALARS)]
    first += [f"body.{r}.{i}" for r in ("sig7", "p7") for i in range(1, WEEK_N + 1)]
    second = [f"body.{r}.{i}" for r in ("eb7", "mass7") for i in range(1, WEEK_N + 1)]
    second += [f"body.bandWeek.{i}.{j}" for i in range(1, WEEK_N + 1) for j in (1, 2)]
    return first, second


# ---------------------------------------------------------------- pure helpers (shared with the tests)
def num(v):
    return X.num(v)


def vals(a):
    return (a or {}).get("values") or {}


def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def fmtnum(v):
    return repr(float(v))


def norm(name):
    """A trait name in one spelling: lower case, the registry prefix and every space or underscore dropped
    (Very Underweight, VERY_UNDERWEIGHT, base:very underweight and VeryUnderweight all read veryunderweight)."""
    s = str(name).lower().split(":")[-1]
    return re.sub(r"[\s_]", "", s)


def band_of(level):
    """The Strength band trait vanilla's remap holds at a level (#2157), normalised, or None."""
    lv = num(level)
    if lv is None:
        return None
    for name, top in BANDS:
        if lv <= top:
            return name
    return "strong"


def close_rel(a, b, rel=REL_TOL):
    a, b = num(a), num(b)
    if a is None or b is None:
        return False
    return abs(a - b) <= rel * max(1.0, abs(b))


def model_of(P):
    """The strength-model numbers the level reads, off the server's options read (R, M5, Fnm, b)."""
    out = {k: num((P or {}).get(k)) for k in ("R", "M5", "Fnm", "b")}
    return out if all(v is not None for v in out.values()) else None


def level_of(F, N0, T, M):
    """K.strength.level: 5 + 5 (S - 1) / (R - 1), S = ((F - Fnm) / M5)^b N0 T, 0 at or below Fnm (ruling 13-45)."""
    F, N0, T = num(F), num(N0), num(T)
    if None in (F, N0, T) or not M:
        return None
    S = 0.0 if F <= M["Fnm"] else ((F - M["Fnm"]) / M["M5"]) ** M["b"] * N0 * T
    return 5.0 + 5.0 * (S - 1.0) / (M["R"] - 1.0)


def f_of_level(L, N0, T, M):
    """K.strength.fOfLevel: the lean at which level_of is L; Fnm where that level needs S <= 0."""
    N0, T = num(N0), num(T)
    if None in (N0, T) or not M:
        return None
    S = 1.0 + (L - 5.0) * (M["R"] - 1.0) / 5.0
    if S <= 0.0:
        return M["Fnm"]
    return M["Fnm"] + M["M5"] * (S / (N0 * T)) ** (1.0 / M["b"])


def shown(L):
    """K.strength.shown: the native level floor(L + 1e-9) clamped to [0, 10] and the bar's fraction."""
    n = max(0, min(L_MAX, math.floor(L + 1e-9)))
    frac = max(0.0, L - n) if (L >= 0 and n < L_MAX) else 0.0
    return n, frac


def mastery_xp(L, cum):
    """K.strength.masteryXp over BeyondTen's cumulative costs cum[level] (ruling 13-42)."""
    f = max(L_MAX, min(15, math.floor(L + 1e-9)))
    base = cum.get(f)
    if base is None:
        return None
    if f >= 15:
        return base
    nxt = cum.get(f + 1)
    if nxt is None:
        return None
    return base + max(0.0, min(1.0, L - f)) * (nxt - base)


def pin_xp(n, frac):
    """K.strength.pinXp: level n's starting total plus frac of the level's cost, at the level-9 total at 10."""
    if n >= L_MAX:
        return TOTALS[L_MAX - 1]
    return TOTALS[n] + frac * (TOTALS[n + 1] - TOTALS[n])


def traits_of(stats):
    lst = (stats or {}).get("traitList")
    if not isinstance(lst, list):
        return None
    return [norm(t) for t in lst]


def bands_held(traits):
    return sorted(t for t in (traits or []) if t in MUSCLE)


def weights_held(traits):
    return sorted(t for t in (traits or []) if t in WEIGHTS)


def flat_body(reads):
    """The record whole off its two lua.read replies: {field or ring.slot: value} without the 'body.' prefix."""
    out, missing = {}, []
    for r in reads:
        for p, v in vals(r).items():
            out[p[5:] if p.startswith("body.") else p] = v
        for p in ((r or {}).get("missing") or {}):
            missing.append(p)
    return out, missing


def ring(b, key):
    return [b.get(f"{key}.{i}") for i in range(1, WEEK_N + 1)]


def band_week(b):
    return [(b.get(f"bandWeek.{i}.1"), b.get(f"bandWeek.{i}.2")) for i in range(1, WEEK_N + 1)]


# ---------------------------------------------------------------- Task 21's expectations (pure)
def profession_table(game_dir):
    """{profession id (normalised): (cost, Strength boost)} off the install's generated profession file (read-only)."""
    out = {}
    path = os.path.join(game_dir, PROFESSIONS_TXT)
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return out
    for m in re.finditer(r"character_profession_definition\s+([^\s{]+)\s*\{(.*?)\n\s*\}", text, re.S):
        body = m.group(2)
        c = re.search(r"\bCost\s*=\s*(-?\d+)", body)
        s = re.search(r"\bXPBoosts\s*=\s*[^,\n]*\bStrength=(-?\d+)", body)
        out[norm(m.group(1))] = (int(c.group(1)) if c else None, int(s.group(1)) if s else 0)
    return out


def profession_id(value):
    """A profession read (witness.chain's tostring of the descriptor's profession) to its normalised id."""
    if value in (None, "nil", ""):
        return None
    s = str(value).strip()
    m = re.search(r"([A-Za-z_ ]+:)?([A-Za-z_]+)\s*$", s)
    return norm(m.group(2)) if m else norm(s)


def offset(penalty, n):
    """CRE.offset: the negative-trait offset (CharacterCreationProfession.lua:918-936)."""
    if n <= 0:
        return 0
    if penalty == 2:
        return n // 3
    if penalty == 3:
        return n // 2
    if penalty == 4:
        return n - 1
    return 0


def excludes(a, b, defs):
    """Two picks exclude each other: either definition's exclusion list names the other, or the anti-stacking pairs."""
    if b in EXCLUDES.get(a, ()) or a in EXCLUDES.get(b, ()):
        return True
    ea = {norm(x) for x in (g(defs, a, "exclusive") or [])}
    eb = {norm(x) for x in (g(defs, b, "exclusive") or [])}
    return b in ea or a in eb


def expect_strips(picks, defs, prof_cost, free_points, penalty):
    """Ruling 13-16 under fix 3, on the server's definitions: no profession grant here, so every pick is a non-free
    pick; picks sorted by |cost| descending, a tie by name; each excluded by a later-sorted pick still held is stripped;
    then, while the remaining points read below 0, the first kept positive pick in that order. Returns (stripped, kept)
    in normalised names, or (None, None) when a definition's cost is unread."""
    names = [norm(p) for p in picks]
    costs = {}
    for n in names:
        c = num(g(defs, n, "cost"))
        if c is None:
            return None, None
        costs[n] = c
    order = sorted(names, key=lambda n: (-abs(costs[n]), n))
    stripped, kept, gone = [], [], set()
    for i, n in enumerate(order):
        hit = None
        for m in order[i + 1:]:
            if hit is None and m not in gone and excludes(n, m, defs):
                hit = m
        if hit is not None:
            gone.add(n)
            stripped.append(n)
        else:
            kept.append(n)

    def rem():
        spent = sum(costs[n] for n in kept)
        neg = sum(1 for n in kept if costs[n] < 0)
        return prof_cost + free_points - spent - offset(penalty, neg)
    while rem() < 0:
        at = next((n for n in kept if costs[n] > 0), None)
        if at is None:
            break
        kept.remove(at)
        stripped.append(at)
    return stripped, kept


def expect_body(kept, prof_boost):
    """The creation body of the kept picks (the plan's Task 9 table through Task 2b's reference strength_level):
    {lm, fm, F0, Fc, Pk, N0, muscle, weight, level, native, band}."""
    from kernel import strength_level as sl                   # noqa: E402 - testing/tests on the path
    muscle = next((n for n in kept if n in MUSCLE), None)
    weight = next((n for n in kept if n in ("overweight", "obese", "underweight", "veryunderweight")), None)
    key = muscle.upper() if muscle else "none"
    F, F0, Fc, Pk = sl.trait_start(key, prof=prof_boost)
    N0 = sl.LEVEL_MODEL["N0"][key]
    if weight in THIN:
        bmi, fmi = THIN[weight]
        fm = fmi * H2
        lm = min(F, bmi * H2 - fm)
    else:
        fm = FAT_FMI[weight] * H2
        lm = F
    L = sl.level(lm, N0, 1.0)
    n = max(0, min(L_MAX, math.floor(L + 1e-9)))
    return {"lm": lm, "fm": fm, "F0": F0, "Fc": Fc, "Pk": Pk, "N0": N0, "muscle": muscle, "weight": weight,
            "level": L, "native": n, "band": band_of(n)}


# ---------------------------------------------------------------- the grades (pure)
def grade_sentinel(s):
    s = s or {}
    obs = {"sentinel_keys": s.get("keys"), "wrapper": s.get("wrapper"), "orig": s.get("orig"),
           "current": s.get("current"), "bt_original": s.get("bt_original"), "answered": s.get("answered")}
    if s.get("answered") is not True:
        obs["why"] = "the sentinel read did not answer"
        return "unmeasured", obs
    if s.get("wrapper") == "function" and (num(s.get("keys")) or 0) > 0:
        return "as_predicted", obs
    obs["why"] = "no wrapper function under NR_StrengthGuardInstalled"
    return "falsified", obs


def grade_write12(w):
    w = w or {}
    M = w.get("model")
    L = level_of(g(w, "after", "lm"), g(w, "after", "N0"), g(w, "after", "T"), M)
    cum = {int(k): v for k, v in (w.get("cum") or {}).items() if num(v) is not None}
    want_stored = mastery_xp(L, cum) if L is not None else None
    obs = {"L": L, "level": w.get("level"), "xp": w.get("xp"), "stored": w.get("stored"),
           "want_stored": want_stored, "mirror": w.get("mirror"), "wrote": w.get("wrote"),
           "bt_loaded": w.get("bt_loaded"), "dayIndex": [w.get("day0"), w.get("day1")]}
    if not w.get("wrote") or L is None:
        obs["why"] = "the level write never ran or the record was unread"
        return "unmeasured", obs
    if w.get("bt_loaded") is not True:
        obs["why"] = "BeyondTen was not loaded"
        return "unmeasured", obs
    bad = []
    if num(w.get("level")) != L_MAX:
        bad.append("native level not 10")
    if num(w.get("xp")) is None or abs(num(w.get("xp")) - PARK_XP) > XP_TOL:
        bad.append("XP not the level-9 total")
    if want_stored is None or not close_rel(w.get("stored"), want_stored):
        bad.append("BeyondTen's stored XP off masteryXp(L)")
    if num(w.get("mirror")) is None or abs(num(w.get("mirror")) - L) > MIRROR_TOL + 1e-9:
        bad.append("the mirror's body_level off L")
    obs["bad"] = bad
    if bad:
        obs["why"] = "; ".join(bad)
        return "falsified", obs
    return "as_predicted", obs


def grade_grant(gr, incidental):
    gr = gr or {}
    s0, s1 = num(gr.get("sig0")), num(gr.get("sig1"))
    c0, c1 = num(gr.get("cap0")), num(gr.get("cap1"))
    landed = c0 is not None and c1 is not None and c1 - c0 >= 1      # the capture ran (BeyondTen re-parks the XP)
    want = GRANT_19 * num(incidental) if num(incidental) is not None else None
    obs = {"sig0": s0, "sig1": s1, "d_sig": (s1 - s0) if (s0 is not None and s1 is not None) else None,
           "want": want, "landed": landed, "captures": [c0, c1], "level": gr.get("level"),
           "xpBefore": gr.get("xpBefore"),
           "xpAfter": gr.get("xpAfter"), "day0": gr.get("day0"), "day1": gr.get("day1")}
    if not landed or s0 is None or s1 is None or want is None:
        obs["why"] = "the capture never ran on the grant, or sigDay was unread"
        return "unmeasured", obs
    if gr.get("day0") != gr.get("day1"):
        obs["why"] = "a day close fell inside the window (sigDay zeroed)"
        return "unmeasured", obs
    bad = []
    if num(gr.get("level")) != L_MAX:
        bad.append("the native level left 10")
    if not close_rel(obs["d_sig"], want):
        bad.append("sigDay did not rise by 1000 x incidental")
    obs["bad"] = bad
    if bad:
        obs["why"] = "; ".join(bad)
        return "falsified", obs
    return "as_predicted", obs


def grade_rust(r):
    r = r or {}
    obs = {"ignored": [r.get("ign0"), r.get("ign1")], "guarded": [r.get("grd0"), r.get("grd1")],
           "level_before": r.get("level0"), "level_after": r.get("level1"), "xp_before": r.get("xp0"),
           "xp_after": r.get("xp1"), "wroteL": r.get("wroteL")}
    ign = (num(r.get("ign1")) or 0) - (num(r.get("ign0")) or 0)
    grd = (num(r.get("grd1")) or 0) - (num(r.get("grd0")) or 0)
    obs["rust_events"], obs["guard_returns"] = ign, grd
    obs["outermost"] = ("the mod's guard (it returned first)" if grd >= 1 else
                        "not the mod's guard, or the guard did not hold" if ign >= 1 else None)
    if ign < 1 or num(r.get("level0")) != L_MAX:
        obs["why"] = "no rust grant reached the listener, or the level was not 10 when it opened"
        return "unmeasured", obs
    if num(r.get("level1")) == L_MAX:
        return "as_predicted", obs
    obs["why"] = "the rust pass dropped the parked level"
    return "falsified", obs


def grade_write95(w):
    w = w or {}
    obs = {"level": w.get("level"), "xp": w.get("xp"), "want_xp": pin_xp(9, 0.5), "stored": w.get("stored"),
           "server_traits": w.get("server_traits"), "client_traits": w.get("client_traits"),
           "pair_gap_s": w.get("pair_gap_s"), "wrote": w.get("wrote"), "L": w.get("L")}
    if not w.get("wrote") or w.get("server_traits") is None or w.get("client_traits") is None:
        obs["why"] = "the level write never ran or a trait list was unread"
        return "unmeasured", obs
    if num(w.get("pair_gap_s")) is None or num(w.get("pair_gap_s")) > PAIR_GAP_MAX_S:
        obs["why"] = "the server and client reads were not in the same second"
        return "unmeasured", obs
    bad = []
    if num(w.get("level")) != 9:
        bad.append("native level not 9")
    if num(w.get("xp")) is None or abs(num(w.get("xp")) - pin_xp(9, 0.5)) > XP_TOL:
        bad.append("XP not level 9's total plus half its cost")
    for side in ("server_traits", "client_traits"):
        if bands_held(w.get(side)) != ["strong"]:
            bad.append(f"{side} hold {bands_held(w.get(side))}, not STRONG alone")
    obs["bad"] = bad
    if bad:
        obs["why"] = "; ".join(bad)
        return "falsified", obs
    return "as_predicted", obs


def gap_diff(a, b):
    """The close-only fields and rings that differ between two record reads (a missing one listed as missing)."""
    diffs = []
    keys = list(GAP_FIELDS) + [f"{r}.{i}" for r in RING_KEYS for i in range(1, WEEK_N + 1)]
    keys += [f"bandWeek.{i}.{j}" for i in range(1, WEEK_N + 1) for j in (1, 2)]
    for k in keys:
        va, vb = (a or {}).get(k), (b or {}).get(k)
        if va is None or vb is None:
            diffs.append({"field": k, "missing": True, "a": va, "b": vb})
        elif va != vb:
            diffs.append({"field": k, "a": va, "b": vb})
    return diffs


def grade_gap(o):
    o = o or {}
    gap = num(o.get("gap_h"))
    obs = {"gap_h": gap, "rejoined": o.get("rejoined")}
    if not o.get("rejoined") or gap is None or not o.get("first"):
        obs["why"] = "admin never rejoined, or the gap or the first read is missing"
        return "unmeasured", obs
    if gap < AWAY_MIN_H:
        obs["why"] = f"the gap {gap} h is under {AWAY_MIN_H} h"
        return "unmeasured", obs
    d1 = gap_diff(o.get("pre"), o.get("away"))
    d2 = gap_diff(o.get("pre"), o.get("first"))
    obs["pre_vs_away"], obs["pre_vs_first"] = d1[:30], d2[:30]
    if any(d.get("missing") for d in d1 + d2):
        obs["why"] = "a field was unread"
        return "unmeasured", obs
    if d1 or d2:
        obs["why"] = "a close-only field moved across the gap"
        return "falsified", obs
    obs["compared"] = len(GAP_FIELDS) + len(RING_KEYS) * WEEK_N + 2 * WEEK_N
    return "as_predicted", obs


def grade_xp(o):
    o = o or {}
    a, b = o.get("xp_pre") or {}, o.get("xp_first") or {}
    obs = {"pre": {"xp": a.get("xp"), "level": a.get("level")}, "first": {"xp": b.get("xp"), "level": b.get("level")}}
    if num(a.get("xp")) is None or num(b.get("xp")) is None:
        obs["why"] = "an XP read is missing"
        return "unmeasured", obs
    if num(a.get("xp")) == num(b.get("xp")) and num(a.get("level")) == num(b.get("level")):
        return "as_predicted", obs
    obs["why"] = "the Strength XP or level moved across the gap"
    return "falsified", obs


def grade_close(o, b):
    o, b = o or {}, b or {}
    first, after, hold = o.get("first") or {}, b.get("after") or {}, b.get("hold") or {}
    d0, d1, d2 = num(first.get("dayIndex")), num(after.get("dayIndex")), num(hold.get("dayIndex"))
    c0, c1 = num(b.get("days0")), num(b.get("days1"))
    obs = {"dayIndex": [d0, d1, d2], "days": [c0, c1], "crossed": b.get("crossed")}
    if not b.get("crossed") or None in (d0, d1, d2):
        obs["why"] = "the boundary was not reached or a dayIndex is unread"
        return "unmeasured", obs
    bad = []
    if d1 != d0 + 1 or d2 != d0 + 1:
        bad.append("dayIndex did not move by exactly one")
    if c0 is not None and c1 is not None and c1 - c0 != 1:
        bad.append(f"the server closed {c1 - c0} days")
    shifts = {}
    for r in RING_KEYS:
        a1, a2 = ring(first, r), ring(after, r)
        ok = all(x is not None for x in a1 + a2) and all(a2[i] == a1[i + 1] for i in range(WEEK_N - 1))
        shifts[r] = ok
        if not ok:
            bad.append(f"{r} did not shift exactly once")
    obs["shifts"], obs["bad"] = shifts, bad
    if bad:
        obs["why"] = "; ".join(bad)
        return "falsified", obs
    return "as_predicted", obs


def grade_case_body(c):
    c = c or {}
    exp, body = c.get("expect") or {}, c.get("body") or {}
    obs = {"expect": {k: exp.get(k) for k in ("lm", "fm", "F0", "Fc", "Pk", "N0", "muscle", "weight", "native")},
           "record": {k: body.get(k) for k in ("lm", "fm", "lx", "F0", "Fc", "Pk", "N0")}}
    if not c.get("landed") or not exp or not body:
        obs["why"] = "the respawn never landed, or the record or the expectation is missing"
        return "unmeasured", obs
    bad = [k for k in ("lm", "fm", "F0", "Fc", "Pk", "N0")
           if num(body.get(k)) is None or abs(num(body.get(k)) - exp[k]) > BODY_TOL]
    obs["bad"] = bad
    if bad:
        obs["why"] = "off the creation table: " + ", ".join(bad)
        return "falsified", obs
    return "as_predicted", obs


def grade_case_state(c):
    c = c or {}
    exp, body, p = c.get("expect") or {}, c.get("body") or {}, c.get("pair") or {}
    st, ct = traits_of(p.get("server_stats")), traits_of(p.get("client_stats"))
    sl_, cl_ = num(g(p, "server_xp", "level")), num(g(p, "client_xp", "level"))
    sw, cw = num(g(p, "server_stats", "weight")), num(g(p, "client_stats", "weight"))
    mass = None
    if all(num(body.get(k)) is not None for k in ("lm", "lx", "fm")):
        mass = num(body["lm"]) + num(body["lx"]) + num(body["fm"])
    obs = {"server": {"weight": sw, "level": sl_, "bands": bands_held(st), "weights": weights_held(st)},
           "client": {"weight": cw, "level": cl_, "bands": bands_held(ct), "weights": weights_held(ct)},
           "mass": mass, "want_native": exp.get("native"), "want_band": exp.get("band"),
           "want_weight": exp.get("weight"), "stripped": c.get("want_stripped"), "pair_gap_s": p.get("gap_s")}
    if not c.get("landed") or not exp or st is None or ct is None or mass is None:
        obs["why"] = "the respawn never landed, or a read is missing"
        return "unmeasured", obs
    if num(p.get("gap_s")) is None or num(p.get("gap_s")) > PAIR_GAP_MAX_S:
        obs["why"] = "the pair was not in the same second"
        return "unmeasured", obs
    bad = []
    want_bands = [exp["band"]] if exp.get("band") else []
    want_w = [exp["weight"]] if exp.get("weight") else []
    for side, lst, lv, wt in (("server", st, sl_, sw), ("client", ct, cl_, cw)):
        if wt is None or abs(wt - mass) > WEIGHT_TOL:
            bad.append(f"{side} weight {wt} off {mass}")
        if lv != exp.get("native"):
            bad.append(f"{side} level {lv} not {exp.get('native')}")
        if bands_held(lst) != want_bands:
            bad.append(f"{side} bands {bands_held(lst)} not {want_bands}")
        if weights_held(lst) != want_w:
            bad.append(f"{side} weight traits {weights_held(lst)} not {want_w}")
        held_stripped = [t for t in (c.get("want_stripped") or []) if t in lst]
        if held_stripped:
            bad.append(f"{side} still holds stripped {held_stripped}")
    obs["bad"] = bad
    if bad:
        obs["why"] = "; ".join(bad)
        return "falsified", obs
    return "as_predicted", obs


def strips_by_case(lines, user="bob"):
    """The server log's creation lines cut into creations: each a list of stripped names (normalised) closed by its
    created line, in log order. Returns [{"strips": [...], "created": {...}}]."""
    out, cur = [], []
    for line in lines:
        m = STRIP_RX.search(line)
        if m and m.group(1) == user:
            cur.append(norm(m.group(2)))
            continue
        m = CREATED_RX.search(line)
        if m and m.group(1) == user:
            out.append({"strips": cur, "created": {"muscle": m.group(2), "weight": m.group(3), "prof": m.group(4)}})
            cur = []
    return out


def grade_case_strips(c, creation):
    c = c or {}
    want = c.get("want_stripped")
    obs = {"want": want, "logged": None if creation is None else creation.get("strips"),
           "created": None if creation is None else creation.get("created")}
    if not c.get("landed") or want is None or creation is None:
        obs["why"] = "the respawn never landed, the expectation is unread or no created line is attributed"
        return "unmeasured", obs
    if creation.get("strips") == want:
        return "as_predicted", obs
    obs["why"] = "the logged strips differ from the expected ones or their order"
    return "falsified", obs


def grade_growth_close(c):
    c = c or {}
    rep = c.get("replay") or {}
    obs = {"lm": [g(c, "pre", "lm"), g(c, "post", "lm")], "T": [g(c, "pre", "T"), g(c, "post", "T")],
           "replay": rep, "inputs": c.get("inputs"), "placed": c.get("placed"), "dayIndex": c.get("days")}
    if not c.get("closed") or not rep or rep.get("error"):
        obs["why"] = "the close was not read, or the replay did not run"
        return "unmeasured", obs
    if rep.get("tdee_sensitive"):
        obs["why"] = "the replay reads tdee: the energy gate is below saturation in the tdee band"
        return "unmeasured", obs
    lm1, T1 = num(g(c, "post", "lm")), num(g(c, "post", "T"))
    lm0 = num(g(c, "pre", "lm"))
    dF_live = (lm1 - lm0) if (lm1 is not None and lm0 is not None) else None
    dF_rep = (rep["lm"] - lm0) if lm0 is not None else None
    obs["dF_live"], obs["dF_replay"] = dF_live, dF_rep
    bad = []
    if lm1 is None or abs(lm1 - rep["lm"]) > LM_TOL:
        bad.append("lm off the replay")
    if T1 is None or abs(T1 - rep["T"]) > T_TOL:
        bad.append("T off the replay")
    obs["bad"] = bad
    if bad:
        obs["why"] = "; ".join(bad)
        return "falsified", obs
    return "as_predicted", obs


def grade_growth_level(c, M):
    c = c or {}
    L = level_of(g(c, "post", "lm"), g(c, "post", "N0"), g(c, "post", "T"), M)
    n = shown(L)[0] if L is not None else None
    traits = traits_of(c.get("stats"))
    obs = {"L": L, "want_native": n, "want_band": band_of(n) if n is not None else None,
           "native": g(c, "xp", "level"), "bands": bands_held(traits)}
    if not c.get("closed") or L is None or traits is None or num(g(c, "xp", "level")) is None:
        obs["why"] = "the close or a read is missing"
        return "unmeasured", obs
    bad = []
    if num(g(c, "xp", "level")) != n:
        bad.append("native level off floor(level + 1e-9)")
    want_b = [band_of(n)] if band_of(n) else []
    if bands_held(traits) != want_b:
        bad.append(f"bands {bands_held(traits)} not {want_b}")
    obs["bad"] = bad
    if bad:
        obs["why"] = "; ".join(bad)
        return "falsified", obs
    return "as_predicted", obs


# ---------------------------------------------------------------- the kernel replay (Task 22; ruling 8-R)
class Kernel:
    """NR_Core.lua and every NR_Kernel*.lua of a shared/ folder (the staged copy's) under lupa's Lua 5.1."""

    def __init__(self, shared_dir):
        import lupa.lua51 as lua51                          # noqa: E402
        self.rt = lua51.LuaRuntime(unpack_returned_tuples=True)
        files = [os.path.join(shared_dir, "NR_Core.lua")] + sorted(glob.glob(os.path.join(shared_dir, "NR_Kernel*.lua")))
        load = self.rt.eval("function(src, name) return assert(loadstring(src, name)) end")
        for path in files:
            with open(path, encoding="utf-8") as fh:
                load(fh.read(), "@" + os.path.basename(path))()
        self.K = self.rt.globals().NutritionRevamp.kernel

    def table(self, d):
        t = self.rt.table()
        for k, v in d.items():
            if isinstance(v, dict):
                t[k] = self.table(v)
            elif isinstance(v, (list, tuple)):
                t[k] = self.table({i + 1: x for i, x in enumerate(v)})
            else:
                t[k] = v
        return t

    def params(self, sv):
        P, _fell = self.K.strength.params(self.table(sv) if sv is not None else None)
        return P

    def ree(self, lm):
        return float(self.K.energy.ree(lm))

    def level(self, F, N0, T, P):
        return float(self.K.strength.level(F, N0, T, P))

    def day(self, pre, S, p, E, tdee, alc, P):
        """K.strength.day on a copy of the pre-close body; returns {lm, T, lx, fm}."""
        b = {k: v for k, v in pre.items() if "." not in k and not k.startswith("_") and v is not None}
        for r in ("sig7", "eb7", "mass7", "p7"):
            b[r] = [pre.get(f"{r}.{i}", 0) for i in range(1, WEEK_N + 1)]
        b["bandWeek"] = [[pre.get(f"bandWeek.{i}.1", 0), pre.get(f"bandWeek.{i}.2", 0)] for i in range(1, WEEK_N + 1)]
        body = self.table(b)
        self.K.strength.day(body, S, p, E, tdee, alc, P, P.ts)
        return {"lm": float(body.lm), "T": float(body.T), "lx": float(body.lx), "fm": float(body.fm)}


def replay_close(kern, P, pre, post):
    """The close's replay off its own recorded inputs: S = post body.S, p = post p7[7] / the pre-close mass, E = post
    eb7[7], alcohol pre alcDay / mass, tdee = max(pre eeDay, ree(lm)) and again EE_MARGIN above it."""
    try:
        w = num(pre.get("fm")) + num(pre.get("lm")) + num(pre.get("lx"))
        S = num(post.get("S"))
        p = num(post.get(f"p7.{WEEK_N}")) / w
        E = num(post.get(f"eb7.{WEEK_N}"))
        alc = (num(pre.get("alcDay")) or 0.0) / w
        ee = num(pre.get("eeDay")) or 0.0
        ree = kern.ree(num(pre.get("lm")))
        t0, t1 = max(ee, ree), max(ee + EE_MARGIN, ree)
        a = kern.day(pre, S, p, E, t0, alc, P)
        b = kern.day(pre, S, p, E, t1, alc, P)
        sens = abs(a["lm"] - b["lm"]) > 1e-12 or abs(a["T"] - b["T"]) > 1e-12
        return {"lm": a["lm"], "T": a["T"], "lx": a["lx"], "fm": a["fm"], "tdee": [t0, t1], "tdee_sensitive": sens,
                "lm_hi": b["lm"]}, {"w": w, "S": S, "p": p, "E": E, "alc": alc, "eeDay_pre": ee, "ree": ree}
    except Exception as e:                                # noqa: BLE001 - recorded, graded unmeasured
        return {"error": f"{type(e).__name__}: {e}"}, None


# ---------------------------------------------------------------- the session
class Sess:
    """The scenario over an xlib.Xs; every wait goes through xs.clock and xs.sleep, so the tests run it fast."""

    def __init__(self, xs, user="admin", cli="client", launch=None, run_dir=None, game_dir=None, shared_dir=None):
        self.xs = xs
        self.out = xs.out
        self.D = self.out.setdefault("checks", {})
        self.user = user
        self.cli = cli
        self.launch = launch
        self.run_dir = run_dir
        self.game_dir = game_dir
        self.shared_dir = shared_dir or os.path.join(REPO, *STAGED_SHARED.split("/"))
        self.last_req = None
        self.model = None
        self.P = None

    # -- plumbing
    def k(self, tag, side, cmd, args="", log=True):
        return self.xs.keep(self.xs.step(tag, side, cmd, args, log=log))

    def lread(self, tag, side, root, paths, log=True):
        return self.k(tag, side, "lua.read", " ".join([root] + list(paths)), log=log)

    def sleep_until(self, t_end):
        while self.xs.clock() < t_end:
            self.xs.check()
            self.xs.sleep(min(POLL_S, max(0.0, t_end - self.xs.clock())))

    def poll(self, tag, fn, cap_s, sleep_s=POLL_S):
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

    def body(self, tag, user=None, log=True):
        a, b = body_paths()
        r1 = self.lread(tag + "_b1", SRV, f"record:{user or self.user}", a, log=log)
        r2 = self.lread(tag + "_b2", SRV, f"record:{user or self.user}", b, log=log)
        out, missing = flat_body([r1, r2])
        out["_wall"] = r1.get("wall")
        out["_missing"] = missing[:20]
        if r1.get("error") or r2.get("error"):
            out["_error"] = r1.get("error") or r2.get("error")
        return out

    def bfield(self, tag, keys, user=None, log=False):
        r = self.lread(tag, SRV, f"record:{user or self.user}", ["body." + k for k in keys], log=log)
        v = vals(r)
        return {k: v.get("body." + k) for k in keys}

    def gread(self, tag, paths, side=SRV, log=False):
        return vals(self.lread(tag, side, "_G", paths, log=log))

    def xp(self, tag, side=SRV, user=None):
        if side == SRV:
            a = self.k(tag, SRV, "perk.xp", f"{user or self.user} Strength")
        else:
            a = self.k(tag, side, "perk.xp", "Strength")
        return {"xp": num(a.get("xp")), "level": num(a.get("level")), "wall": a.get("wall"), "error": a.get("error")}

    def snap(self, tag, log=True):
        return self.xs.snap(tag, log=log)

    def age(self, tag="age"):
        return num(self.snap(tag, log=False).get("worldAge"))

    def set_mult(self, value, tag):
        r = self.k(tag, SRV, "time.multiplier", fmtnum(value))
        s = self.snap(tag + "_t")
        tm = num(s.get("trueMult"))
        return {"reply": r.get("raw"), "trueMult": tm, "ok": tm is not None and abs(tm - value) <= 1e-6 * max(1.0, value)}

    def restore_mult(self, value, tag):
        r1 = self.set_mult(value, tag)
        if r1["ok"]:
            return {"first": r1, "ok": True}
        r2 = self.set_mult(value, tag + "_retry")
        return {"first": r1, "retry": r2, "ok": r2["ok"]}

    def mult_read(self, tag):
        m = num(self.snap(tag).get("trueMult"))
        return m if m is not None and m > 0 else None

    def wait_age(self, target, tag, cap_s, sleep_s=POLL_S):
        if target is None:
            return {"done": False, "skipped": "no target"}

        def fn():
            a = self.age(tag)
            return (a is not None and a >= target), a
        return self.poll(tag, fn, cap_s, sleep_s)

    def ready(self, tag):
        def fn():
            v = self.gread(tag, [f"{NR}.server.minute.stats.runs", f"{STR_STATS}.levelWrites"])
            b = self.bfield(tag + "_b", ["lm", "levelDue"])
            runs = num(v.get(f"{NR}.server.minute.stats.runs"))
            return (runs is not None and runs >= MIN_RUNS and num(b.get("lm")) is not None
                    and b.get("levelDue") is not True), {"runs": runs, "lm": b.get("lm"), "levelDue": b.get("levelDue")}
        return self.poll(tag, fn, READY_CAP_S, 1.0)

    def strength_P(self, tag):
        keys = ("R", "M5", "Fnm", "b", "incidental", "xpPerSet", "ts", "k")
        v = self.gread(tag, [f"{OPT_STR}.{k}" for k in keys], log=True)
        return {k: num(v.get(f"{OPT_STR}.{k}")) for k in keys}

    def request_mirror(self, tag):
        xs = self.xs
        if self.last_req is not None and xs.clock() - self.last_req < REQUEST_GAP_S:
            xs.sleep(REQUEST_GAP_S - (xs.clock() - self.last_req))
        rc0 = num(self.gread(tag + "_rc0", [f"{NR}.client.received"], side=self.cli).get(f"{NR}.client.received"))
        self.last_req = xs.clock()
        req = self.k(tag + "_req", self.cli, "lua.call", f"{NR}.client.requestMirror")

        def fn():
            v = num(self.gread(tag + "_arr", [f"{NR}.client.received"], side=self.cli).get(f"{NR}.client.received"))
            return (v is not None and rc0 is not None and v > rc0), v
        a = self.poll(tag + "_arr", fn, ARRIVE_CAP_S, 0.5)
        lv = self.gread(tag + "_lv", [f"{NR}.client.mirror.body_level", f"{NR}.client.mirror.body_sets"],
                        side=self.cli, log=True)
        return {"rc0": rc0, "request_ok": req.get("ok"), "arrived": a["done"],
                "body_level": lv.get(f"{NR}.client.mirror.body_level"),
                "body_sets": lv.get(f"{NR}.client.mirror.body_sets")}

    def write_level(self, tag, L):
        """record.set body.lm to fOfLevel(L, N0, T) (N0 and T re-read first) and body.levelDue true; waits for the
        Strength minute's levelWrites to rise and levelDue to read false."""
        w = {"L": L}
        nt = self.bfield(tag + "_nt", ["N0", "T", "lm", "dayIndex"], log=True)
        w["N0"], w["T"], w["lm_before"], w["day0"] = nt["N0"], nt["T"], nt["lm"], nt["dayIndex"]
        F = f_of_level(L, nt["N0"], nt["T"], self.model)
        w["F"] = F
        if F is None:
            w["error"] = "N0, T or the model unread"
            return w
        w0 = num(self.gread(tag + "_lw0", [f"{STR_STATS}.levelWrites"]).get(f"{STR_STATS}.levelWrites"))
        w["set_lm"] = self.k(tag + "_set_lm", SRV, "record.set", f"{self.user} body.lm {F!r}")
        w["set_due"] = self.k(tag + "_set_due", SRV, "record.set", f"{self.user} body.levelDue true")

        def fn():
            v = num(self.gread(tag + "_lw", [f"{STR_STATS}.levelWrites"]).get(f"{STR_STATS}.levelWrites"))
            due = self.bfield(tag + "_due", ["levelDue"])["levelDue"]
            return (v is not None and w0 is not None and v > w0 and due is False), {"levelWrites": v, "due": due}
        p = self.poll(tag + "_wait", fn, WRITE_CAP_S)
        w["wrote"], w["wait"] = p["done"], p
        w["after"] = self.bfield(tag + "_after", ["lm", "N0", "T", "wroteL", "levelDue", "dayIndex"], log=True)
        w["day1"] = w["after"].get("dayIndex")
        return w

    # ======================================================== Task 19
    def t19_S(self):
        P = self.D["S"] = {}
        P["players"] = self.xs.step("S_players", SRV, "players")["ack"]
        P["time"] = self.snap("S_time")
        P["ready"] = self.ready("S_ready")
        P["bt"] = self.k("S_bt", SRV, "lua.global", "BeyondTen.API_VERSION")
        s = self.lread("S_guard", SRV, "_G", ["NR_StrengthGuardInstalled", "NR_StrengthGuardInstalled.wrapper",
                                              "NR_StrengthGuardInstalled.orig", "NR_StrengthGuardInstalled.class",
                                              "xpUpdate.checkForLosingLevel",
                                              "xpUpdate._BeyondTenB42OriginalCheckForLosingLevel"])
        t = s.get("types") or {}
        P["sentinel"] = {"keys": (s.get("tables") or {}).get("NR_StrengthGuardInstalled"),
                         "wrapper": t.get("NR_StrengthGuardInstalled.wrapper"),
                         "orig": t.get("NR_StrengthGuardInstalled.orig"),
                         "class": (s.get("tables") or {}).get("NR_StrengthGuardInstalled.class"),
                         "current": t.get("xpUpdate.checkForLosingLevel"),
                         "bt_original": t.get("xpUpdate._BeyondTenB42OriginalCheckForLosingLevel"),
                         "missing": s.get("missing"), "answered": s.get("ok") is True}
        P["P"] = self.strength_P("S_P")
        self.P = P["P"]
        self.model = model_of(P["P"])
        P["sandbox"] = self.gread("S_sv", ["SandboxVars.Nutrition", "SandboxVars.DayLength",
                                           "SandboxVars.MultiplierConfig.Global",
                                           "SandboxVars.MultiplierConfig.GlobalToggle"], log=True)
        P["body"] = self.body("S_body")
        P["xp"] = self.xp("S_xp")
        P["stored"] = self.k("S_stored", SRV, "bt.stored", f"{self.user} Strength")
        cum = {}
        for lv in (10, 11, 12, 13, 14, 15):
            r = self.k(f"S_cost{lv}", SRV, "lua.call", f"BeyondTen.GetTotalMasteryCost Strength {lv}")
            cum[lv] = num(r.get("r1"))
        P["cum"] = cum

    def t19_W12(self):
        w = self.D["W12"] = self.write_level("W12", W12_LEVEL)
        w["model"] = self.model
        w["cum"] = (self.D.get("S") or {}).get("cum")
        if not w.get("wrote"):
            return

        def fn():
            x = self.xp("W12_xp")
            return (x["xp"] is not None and abs(x["xp"] - PARK_XP) <= XP_TOL), x
        p = self.poll("W12_park", fn, W12_PARK_S)
        w["xp_polls"] = p["polls"]
        w["level"], w["xp"] = g(p, "last", "level"), g(p, "last", "xp")
        st = self.k("W12_stored", SRV, "bt.stored", f"{self.user} Strength")
        w["stored"], w["bt_loaded"] = st.get("stored"), st.get("loaded")
        m = self.request_mirror("W12_mirror")
        w["mirror"], w["mirror_read"] = m.get("body_level"), m

    def t19_G(self):
        gr = self.D["G"] = {}
        b0 = self.bfield("G_b0", ["sigDay", "dayIndex"], log=True)
        gr["sig0"], gr["day0"] = b0["sigDay"], b0["dayIndex"]
        gr["cap0"] = self.gread("G_cap0", [f"{STR_XP}.captures"], log=True).get(f"{STR_XP}.captures")
        a = self.k("G_grant", SRV, "xp.grant", f"{self.user} Strength {GRANT_19:g}")
        gr["xpBefore"], gr["xpAfter"] = a.get("xpBefore"), a.get("xpAfter")
        gr["levelAfterGrant"] = a.get("levelAfter")
        self.sleep_until(self.xs.clock() + SETTLE_S)
        b1 = self.bfield("G_b1", ["sigDay", "dayIndex", "wroteL"], log=True)
        gr["sig1"], gr["day1"] = b1["sigDay"], b1["dayIndex"]
        gr["cap1"] = self.gread("G_cap1", [f"{STR_XP}.captures"], log=True).get(f"{STR_XP}.captures")
        x = self.xp("G_xp")
        gr["level"], gr["xp_after"] = x["level"], x["xp"]
        st = self.k("G_stored", SRV, "bt.stored", f"{self.user} Strength")
        gr["stored_after"] = st.get("stored")

    def t19_R(self):
        r = self.D["R"] = {}
        keys = [f"{STR_XP}.ignored", f"{STR_STATS}.guarded"]
        v0 = self.gread("R_c0", keys, log=True)
        r["ign0"], r["grd0"] = v0.get(keys[0]), v0.get(keys[1])
        x0 = self.xp("R_xp0")
        r["level0"], r["xp0"] = x0["level"], x0["xp"]
        r["wroteL"] = self.bfield("R_w", ["wroteL"], log=True)["wroteL"]
        r["set"] = self.k("R_set", SRV, "moddata.set", f"{self.user} strengthUpTimer {RUST_TIMER}")

        def fn():
            v = self.gread("R_c", keys)
            ign = num(v.get(keys[0]))
            return (ign is not None and num(r["ign0"]) is not None and ign > num(r["ign0"])), v
        p = self.poll("R_wait", fn, RUST_CAP_S, 0.5)
        r["fired"] = p["done"]
        self.sleep_until(self.xs.clock() + SETTLE_S)
        v1 = self.gread("R_c1", keys, log=True)
        r["ign1"], r["grd1"] = v1.get(keys[0]), v1.get(keys[1])
        x1 = self.xp("R_xp1")
        r["level1"], r["xp1"] = x1["level"], x1["xp"]
        st = self.k("R_stored", SRV, "bt.stored", f"{self.user} Strength")
        r["stored_after"] = st.get("stored")
        r["reset"] = self.k("R_reset", SRV, "moddata.set", f"{self.user} strengthUpTimer {RUST_RESET}")
        self.out["world_changes"]["left_in_place"].append(
            "R: admin's strengthUpTimer set to 25000 for one rust pass, then back to -50000")

    def pair(self, tag, user, cli):
        p = {"server_stats": self.k(tag + "_s", SRV, "stats.get", user),
             "client_stats": self.k(tag + "_c", cli, "stats.get")}
        p["server_xp"] = self.xp(tag + "_sx", SRV, user)
        p["client_xp"] = self.xp(tag + "_cx", cli)
        w0, w1 = num(p["server_stats"].get("wall")), num(p["client_stats"].get("wall"))
        p["gap_s"] = abs(w1 - w0) if (w0 is not None and w1 is not None) else None
        return p

    def t19_W95(self):
        w = self.D["W95"] = self.write_level("W95", W95_LEVEL)
        if not w.get("wrote"):
            return
        self.sleep_until(self.xs.clock() + SETTLE_S)
        p = self.pair("W95_pair", self.user, self.cli)
        w["pair"] = p
        w["level"], w["xp"] = g(p, "server_xp", "level"), g(p, "server_xp", "xp")
        w["server_traits"], w["client_traits"] = traits_of(p["server_stats"]), traits_of(p["client_stats"])
        w["pair_gap_s"] = p["gap_s"]
        st = self.k("W95_stored", SRV, "bt.stored", f"{self.user} Strength")
        w["stored"] = st.get("stored")

    def t19_body(self):
        return (("S", self.t19_S), ("W12", self.t19_W12), ("G", self.t19_G), ("R", self.t19_R),
                ("W95", self.t19_W95))

    def t19_grade(self):
        D, xs = self.D, self.xs
        v, o = grade_sentinel(g(D, "S", "sentinel"))
        xs.grade("19_sentinel", v, o, "no wrapper function under NR_StrengthGuardInstalled")
        v, o = grade_write12(D.get("W12"))
        xs.grade("19_write12", v, o, "level not 10, XP not 337500, stored XP or body_level off L")
        v, o = grade_grant(D.get("G"), g(D, "S", "P", "incidental"))
        xs.grade("19_grant", v, o, "level left 10 or sigDay off 1000 x incidental")
        v, o = grade_rust(D.get("R"))
        xs.grade("19_rust", v, o, "the rust pass drops the parked level 10")
        v, o = grade_write95(D.get("W95"))
        xs.grade("19_write95", v, o, "level not 9, XP not 412500, or STRONG not held alone on a side")

    # ======================================================== Task 20
    def t20_S(self):
        P = self.D["S"] = {}
        P["players"] = self.xs.step("S_players", SRV, "players")["ack"]
        P["time"] = self.snap("S_time")
        P["ready"] = self.ready("S_ready")
        P["body"] = self.body("S_body")
        P["xp"] = self.xp("S_xp")

    def players_gone(self, lst):
        if isinstance(lst, list):
            return self.user not in lst
        return isinstance(lst, dict) and not lst

    def t20_OFF(self):
        o = self.D["OFF"] = {"rejoined": False}
        a = self.age("OFF_age")
        if a is not None and (a % 24.0) >= PRE_LATE_HOUR:
            o["late_wait"] = self.wait_age((math.floor(a / 24.0) + 1) * 24.0 + 0.1, "OFF_late", 90.0, 0.5)
        o["pre_snap"] = self.snap("OFF_pre_t")
        o["pre"] = self.body("OFF_pre")
        o["xp_pre"] = self.xp("OFF_xp_pre")
        lq = num(o["pre"].get("lastAgeH"))
        c = self.xs.clients.get(self.user)
        q = {"wall0": self.xs.wall()}
        try:
            q["rc"] = c.quit() if c is not None else None
        except Exception as e:                       # noqa: BLE001 - recorded
            q["error"] = f"{type(e).__name__}: {e}"
        q["wall1"] = self.xs.wall()
        self.xs.clients.pop(self.user, None)
        o["quit"] = q

        def gone():
            lst = self.xs.step("OFF_players", SRV, "players", log=False).get("ack")
            return self.players_gone(lst), lst
        o["depart"] = self.poll("OFF_depart", gone, DEPART_CAP_S, 0.5)
        if not o["depart"]["done"]:
            self.xs.note("OFF: admin never left the server inside the cap; the clock is not raised")
            return
        o["away"] = self.body("OFF_away")
        lq = num(o["away"].get("lastAgeH")) if num(o["away"].get("lastAgeH")) is not None else lq
        o["Lq"] = lq
        o["restore_to"] = self.mult_read("OFF_mult0")
        if lq is None or o["restore_to"] is None:
            self.xs.note("OFF: lastAgeH or trueMult unread; the clock is not raised")
            return
        t = lq + AWAY_MIN_H
        d = math.floor(t / 24.0)
        target = d * 24.0 + AWAY_HOUR
        if target < t:
            target += 24.0
        o["target"] = target
        try:
            o["raise"] = self.set_mult(AWAY_MULT, "OFF_raise")
            o["away_wait"] = self.wait_age(target, "OFF_away_wait", AWAY_CAP_S, AWAY_POLL_S)
        finally:
            o["restore"] = self.restore_mult(o["restore_to"], "OFF_restore")
        if not o["restore"]["ok"]:
            self.xs.note("OFF: the multiplier did not read back the value read before; admin does not rejoin")
            return
        o["launch_snap"] = self.snap("OFF_launch_t")
        o["launch"] = self.launch(self, self.user, "c1b") if self.launch else {"error": "no launcher"}
        o["rejoined"] = bool(o["launch"].get("ready_took"))
        if not o["rejoined"]:
            return

        def moved():
            b = self.bfield("OFF_first_poll", ["lastAgeH"])
            v = num(b.get("lastAgeH"))
            return (v is not None and v != lq), v
        o["first_wait"] = self.poll("OFF_first", moved, FIRST_CAP_S, 0.5)
        o["first"] = self.body("OFF_first")
        o["xp_first"] = self.xp("OFF_xp_first")
        o["first_snap"] = self.snap("OFF_first_t")
        f_age = num(o["first"].get("lastAgeH"))
        o["gap_h"] = (f_age - lq) if (f_age is not None and lq is not None) else None
        self.out["world_changes"]["left_in_place"].append(
            "OFF: admin quit; the clock ran at AWAY_MULT and was restored; admin rejoined from a fresh fixture "
            "restore in <run>/c1b")

    def t20_B(self):
        b = self.D["B"] = {"crossed": False}
        o = self.D.get("OFF") or {}
        if not o.get("rejoined"):
            b["skipped"] = "admin did not rejoin"
            return
        days = f"{NR}.server.metabolism.stats.days"
        b["days0"] = self.gread("B_days0", [days], log=True).get(days)
        d0 = num(self.bfield("B_d0", ["dayIndex"], log=True)["dayIndex"])
        a0 = self.age("B_age0")
        b["age0"] = a0
        boundary = (math.floor(a0 / 24.0) + 1) * 24.0 if a0 is not None else None
        b["boundary"] = boundary
        b["restore_to"] = self.mult_read("B_mult0")
        if boundary is None or b["restore_to"] is None or d0 is None:
            return
        try:
            b["raise"] = self.set_mult(BOUNDARY_MULT, "B_raise")

            def moved():
                d = num(self.bfield("B_poll", ["dayIndex"])["dayIndex"])
                return (d is not None and d != d0), d
            b["wait"] = self.poll("B_wait", moved, BOUNDARY_CAP_S, 0.5)
        finally:
            b["restore"] = self.restore_mult(b["restore_to"], "B_restore")
        b["crossed"] = bool(b["wait"]["done"])
        b["after"] = self.body("B_after")
        self.sleep_until(self.xs.clock() + AFTER_HOLD_S)
        b["hold"] = self.body("B_hold")
        b["days1"] = self.gread("B_days1", [days], log=True).get(days)
        b["xp_after"] = self.xp("B_xp")

    def t20_body(self):
        return (("S", self.t20_S), ("OFF", self.t20_OFF), ("B", self.t20_B))

    def t20_grade(self):
        D, xs = self.D, self.xs
        v, o = grade_gap(D.get("OFF"))
        xs.grade("20_gap", v, o, "a close-only field or ring moved across a gap of at least 72 h")
        v, o = grade_xp(D.get("OFF"))
        xs.grade("20_xp", v, o, "the Strength XP or level moved across the gap")
        v, o = grade_close(D.get("OFF"), D.get("B"))
        xs.grade("20_close", v, o, "not exactly one close after the next boundary")

    # ======================================================== Task 21
    def mcall(self, tag, args):
        return self.k(tag, self.cli, "lua.callm", args)

    def created(self, tag):
        p = f"{NR}.server.creation.stats.created"
        return num(self.gread(tag, [p]).get(p)) or 0

    def t21_S(self):
        P = self.D["S"] = {}
        P["players"] = self.xs.step("S_players", SRV, "players")["ack"]
        P["time"] = self.snap("S_time")
        P["ready"] = self.ready("S_ready")
        P["sandbox"] = self.gread("S_sv", ["SandboxVars.CharacterFreePoints", "SandboxVars.NegativeTraitsPenalty",
                                           "SandboxVars.Nutrition", "SandboxVars.DayLength"], log=True)
        names = []
        for _c, picks in CASES:
            for t in picks:
                if t not in names:
                    names.append(t)
        defs = {}
        for t in names:
            a = self.k(f"S_def_{t}", SRV, "trait.def", t)
            defs[norm(t)] = {"cost": a.get("cost"), "exclusive": a.get("exclusive"), "free": a.get("free"),
                             "xpBoosts": a.get("xpBoosts"), "ok": a.get("ok"), "trait": a.get("trait")}
        P["defs"] = defs
        P["profession"] = self.k("S_prof", SRV, "witness.chain", f"{self.user} getDescriptor.getCharacterProfession")
        P["profession_name"] = self.k("S_profn", SRV, "witness.chain",
                                      f"{self.user} getDescriptor.getCharacterProfession.getName")
        P["prof_table"] = profession_table(self.game_dir) if self.game_dir else {}

    def respawn(self, label):
        R = {"label": label}
        R["count_before"] = self.created(label + "_c0")
        R["reduce"] = self.k(label + "_reduce", SRV, "health.reduce", f"{self.user} 110")

        def dead():
            r = self.k(label + "_isDead", SRV, "witness.chain", f"{self.user} isDead", log=False)
            return str(r.get("value")).lower() == "true", r.get("value")
        R["dead"] = self.poll(label + "_dead", dead, DEATH_CAP_S, POLL_S)["done"]
        if not R["dead"]:
            R["unmeasured"] = "the server never read the user dead"
            return R

        def ui():
            r = self.mcall(label + "_ui", "ISPostDeathUI.instance.0 getIsVisible")
            return bool(r.get("ok")), r.get("r1")
        R["ui"] = self.poll(label + "_ui", ui, UI_CAP_S, 1.0)["done"]
        if not R["ui"]:
            R["unmeasured"] = "the post-death UI never appeared"
            return R
        R["onRespawn"] = self.mcall(label + "_onRespawn", "ISPostDeathUI.instance.0 onRespawn")

        def screens():
            row = {"spawn": self.mcall(label + "_spawn", "CoopMapSpawnSelect.instance getIsVisible").get("r1"),
                   "profession": self.mcall(label + "_prof", "CharacterCreationProfession.instance getIsVisible").get(
                       "r1"),
                   "main": self.mcall(label + "_main", "CharacterCreationMain.instance getIsVisible").get("r1")}
            return (row["main"] is True and row["spawn"] is not True and row["profession"] is not True), row
        sc = self.poll(label + "_screens", screens, CREATE_CAP_S, 1.0)
        R["screens"] = sc
        if g(sc, "last", "spawn") is True:
            R["clickNext"] = self.mcall(label + "_clickNext", "CoopMapSpawnSelect.instance clickNext")
            self.sleep_until(self.xs.clock() + 3.0)
        R["accept"] = self.mcall(label + "_accept", "CoopCharacterCreation.instance accept")

        def landed():
            n = self.created(label + "_c")
            return n > R["count_before"], n
        la = self.poll(label + "_land", landed, LAND_CAP_S, POLL_S)
        R["landed"] = la["done"]
        R["landed_clock"] = self.xs.clock()
        if not R["landed"]:
            R["unmeasured"] = "the server's creation count never rose"
        return R

    def t21_case(self, label, picks):
        c = self.D[f"C{label}"] = {"picks": list(picks)}
        if picks:
            arm = self.k(f"C{label}_arm", self.cli, "creation.picks", " ".join(picks))
            c["arm"] = arm
            if arm.get("armed") is not True:
                c["unmeasured"] = "creation.picks did not arm"
                return
        R = self.respawn(f"C{label}")
        c.update({k: R.get(k) for k in ("landed", "dead", "ui", "unmeasured", "count_before")})
        c["route"] = {k: R.get(k) for k in ("onRespawn", "screens", "clickNext", "accept")}
        if picks:
            fired = self.gread(f"C{label}_fired", ["TK.picksFired.count", "TK.picksFired.error"], side=self.cli,
                               log=True)
            c["fired"] = fired
        if not R.get("landed"):
            return
        self.sleep_until(R["landed_clock"] + PAIR_DELAY_S)
        c["profession"] = self.k(f"C{label}_prof", SRV, "witness.chain",
                                 f"{self.user} getDescriptor.getCharacterProfession").get("value")
        c["profession_name"] = self.k(f"C{label}_profn", SRV, "witness.chain",
                                      f"{self.user} getDescriptor.getCharacterProfession.getName").get("value")
        c["body"] = self.body(f"C{label}_body")
        c["pair"] = self.pair(f"C{label}_pair", self.user, self.cli)

    def t21_body(self):
        return (("S", self.t21_S),) + tuple((f"C{lab}", (lambda lab=lab, p=p: self.t21_case(lab, p)))
                                            for lab, p in CASES)

    def t21_expect(self, c):
        S = self.D.get("S") or {}
        sv = S.get("sandbox") or {}
        free = num(sv.get("SandboxVars.CharacterFreePoints")) or 0
        pen = num(sv.get("SandboxVars.NegativeTraitsPenalty")) or 1
        table = S.get("prof_table") or {}
        pid, prow = None, None
        for v in (c.get("profession"), c.get("profession_name")):
            cand = profession_id(v)
            if cand in table:
                pid, prow = cand, table[cand]
                break
        c["prof"] = {"id": pid, "cost": prow[0] if prow else None, "boost": prow[1] if prow else None,
                     "free": free, "penalty": pen}
        if prow is None or prow[0] is None:
            c["expect_error"] = f"profession {c.get('profession')!r} not in the install's table"
            return
        stripped, kept = expect_strips(c["picks"], S.get("defs") or {}, prow[0], free, pen)
        if stripped is None:
            c["expect_error"] = "a pick's server cost is unread"
            return
        c["want_stripped"], c["want_kept"] = stripped, kept
        c["expect"] = expect_body(kept, prow[1])

    def t21_grade(self, log_lines=None):
        xs = self.xs
        creations = strips_by_case(log_lines or [], self.user)
        self.out.setdefault("readings", {})["creations"] = creations
        landed = [lab for lab, _p in CASES if (self.D.get(f"C{lab}") or {}).get("landed")]
        for lab, _p in CASES:
            c = self.D.get(f"C{lab}") or {}
            if c.get("landed"):
                self.t21_expect(c)
            idx = landed.index(lab) if lab in landed else None
            cr = creations[idx] if (idx is not None and len(creations) == len(landed)) else None
            v, o = grade_case_body(c)
            xs.grade(f"21_{lab}_body", v, o, "the record's body off the creation table")
            v, o = grade_case_state(c)
            xs.grade(f"21_{lab}_state", v, o, "weight, level, band or weight trait off on a side, or a strip held")
            v, o = grade_case_strips(c, cr)
            xs.grade(f"21_{lab}_strips", v, o, "the logged strips differ from ruling 13-16's cost order")

    # ======================================================== Task 22
    def t22_S(self):
        P = self.D["S"] = {}
        P["players"] = self.xs.step("S_players", SRV, "players")["ack"]
        P["time"] = self.snap("S_time")
        P["ready"] = self.ready("S_ready")
        P["P"] = self.strength_P("S_P")
        self.P = P["P"]
        self.model = model_of(P["P"])
        P["sandbox"] = self.gread("S_sv", ["SandboxVars.Nutrition", "SandboxVars.DayLength",
                                           "SandboxVars.NR.StrengthTimeScale",
                                           "SandboxVars.NR.StrengthIncidentalWeight"], log=True)
        P["body"] = self.body("S_body")
        P["xp"] = self.xp("S_xp")

    def grant_xp(self):
        xps = num((self.P or {}).get("xpPerSet"))
        return (xps * SETS_A_DAY / GRANTS) if xps else None

    def t22_day(self, k, grants):
        c = self.D[f"day{k}"] = {"grants": [], "closed": False, "graded": grants}
        a0 = self.age(f"D{k}_age0")
        if a0 is None:
            c["error"] = "the world age is unread"
            return c
        boundary = (math.floor(a0 / 24.0) + 1) * 24.0
        c["boundary"], c["age0"] = boundary, a0
        restore_to = self.mult_read(f"D{k}_mult0")
        c["restore_to"] = restore_to
        if restore_to is None:
            c["error"] = "trueMult unread"
            return c
        amt = self.grant_xp()
        try:
            c["raise"] = self.set_mult(DAY_MULT, f"D{k}_raise")
            if grants and amt:
                nxt = a0
                for i in range(GRANTS):
                    self.wait_age(nxt, f"D{k}_g{i}_wait", 60.0)
                    gate = self.xp(f"D{k}_g{i}_xp")
                    row = {"i": i, "xp_open": gate["xp"], "level_open": gate["level"]}
                    if gate["xp"] is None or gate["xp"] >= CAP_XP:
                        row["skipped"] = "at the level-10 cap or unread"
                    else:
                        a = self.k(f"D{k}_g{i}", SRV, "xp.grant", f"{self.user} Strength {amt!r}")
                        row.update({"xpBefore": a.get("xpBefore"), "xpAfter": a.get("xpAfter"),
                                    "levelAfter": a.get("levelAfter"), "ok": a.get("ok")})
                    c["grants"].append(row)
                    nxt = (self.age(f"D{k}_g{i}_age") or nxt) + GRANT_GAP_H
                    if nxt >= boundary - (24.0 - SLOW_HOUR) - 0.25:
                        nxt = boundary - (24.0 - SLOW_HOUR) - 0.25
            c["slow_wait"] = self.wait_age(boundary - (24.0 - SLOW_HOUR), f"D{k}_slow", DAY_CAP_S, 0.5)
        finally:
            c["restore"] = self.restore_mult(restore_to, f"D{k}_restore")
        c["place_wait"] = self.wait_age(boundary - PLACE_MIN / 60.0, f"D{k}_place", DAY_CAP_S / 2, 0.2)
        pre = self.body(f"D{k}_pre")
        c["pre"] = pre
        w = None
        if all(num(pre.get(x)) is not None for x in ("fm", "lm", "lx")):
            w = num(pre["fm"]) + num(pre["lm"]) + num(pre["lx"])
        c["placed"] = {"w": w}
        if w is not None:
            c["placed"]["pDay"] = self.k(f"D{k}_pDay", SRV, "record.set", f"{self.user} body.pDay {P_GKG * w!r}")
            c["placed"]["ebDay"] = self.k(f"D{k}_ebDay", SRV, "record.set", f"{self.user} body.ebDay {E_KCAL!r}")
            c["placed"]["day_after_set"] = self.bfield(f"D{k}_dset", ["dayIndex"], log=True)["dayIndex"]
        d0 = num(pre.get("dayIndex"))

        def moved():
            d = num(self.bfield(f"D{k}_dpoll", ["dayIndex"])["dayIndex"])
            return (d is not None and d0 is not None and d != d0), d
        c["close_wait"] = self.poll(f"D{k}_close", moved, CLOSE_CAP_S, 0.3)
        c["closed"] = bool(c["close_wait"]["done"])
        c["placed"]["before_close"] = c["placed"].get("day_after_set") == d0 if w is not None else False
        self.sleep_until(self.xs.clock() + SETTLE_S)
        c["post"] = self.body(f"D{k}_post")
        c["days"] = [d0, num(c["post"].get("dayIndex"))]
        c["xp"] = self.xp(f"D{k}_lvl")
        c["stats"] = self.k(f"D{k}_stats", SRV, "stats.get", self.user)
        return c

    def t22_D(self):
        a0 = self.age("D_age_start")
        lead = a0 is not None and (a0 % 24.0) >= LEAD_HOUR
        self.D["lead_in"] = lead
        if lead:
            self.t22_day(0, False)
        for k in range(1, GROWTH_DAYS + 1):
            self.xs.check()
            self.t22_day(k, True)

    def t22_body(self):
        return (("S", self.t22_S), ("D", self.t22_D))

    def t22_grade(self, kern=None):
        xs = self.xs
        P_server = self.P or {}
        try:
            kern = kern or Kernel(self.shared_dir)
            sv = {"StrengthTimeScale": 30.0, "StrengthIncidentalWeight": 1.0}
            P = kern.params(sv)
            self.out.setdefault("readings", {})["replay_P"] = {"ts": float(P.ts), "incidental": float(P.incidental),
                                                               "xpPerSet": float(P.xpPerSet), "R": float(P.R),
                                                               "server": P_server}
        except Exception as e:                       # noqa: BLE001
            kern, P = None, None
            self.out.setdefault("readings", {})["replay_error"] = f"{type(e).__name__}: {e}"
        for k in range(0, GROWTH_DAYS + 1):
            c = self.D.get(f"day{k}")
            if c is None:
                continue
            if c.get("closed") and kern is not None and c.get("pre") and c.get("post"):
                c["replay"], c["inputs"] = replay_close(kern, P, c["pre"], c["post"])
            v, o = grade_growth_close(c)
            xs.grade(f"22_close{k}", v, o, "lm off the replay by more than 1e-6 kg or T by more than 1e-9")
            v, o = grade_growth_level(c, self.model)
            xs.grade(f"22_level{k}", v, o, "native level or band off floor(level(lm, N0, T) + 1e-9)")

    def body_run(self, phases):
        for name, fn in phases:
            if self.xs.parked():
                self.out["abort"] = f"admin parked in the debugger before phase {name}"
                break
            self.xs.run_phase(name, fn)


# ---------------------------------------------------------------- the live run
def launch_real(make_client, prof, rec_fx, started, tl):
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


def staged_gate(out, xs, git_say, git_dirty):
    sys.path.insert(0, os.path.join(REPO, "tools"))
    import release_pack as RP                                       # noqa: E402
    mg = out["manifest_gate"] = X.manifest_gate(RP, REPO, MOD_DIR, STAGE_ROOT, STAGE_MOD, MANIFEST_NAME, git_say,
                                                git_dirty)
    try:
        with open(os.path.join(REPO, *STAGE_MOD.split("/"), *STAGED_CORE.split("/")), encoding="utf-8") as fh:
            m = re.search(r'version\s*=\s*"([^"]+)"', fh.read())
        mg["staged_version"] = m.group(1) if m else None
    except OSError as e:
        mg["staged_version_error"] = f"{type(e).__name__}: {e}"
    return mg


def harness_markers_ok():
    found = {}
    for fname, rel in HARNESS_FILES.items():
        try:
            with open(os.path.join(REPO, rel), encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            text = ""
        found[fname] = {mk: (mk in text) for mk in HARNESS_MARKERS[fname]}
    return found, all(all(d.values()) for d in found.values())


def read_log_lines(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return [ln.rstrip("\n") for ln in fh if "[NutritionRevamp] creation:" in ln]
    except OSError:
        return []


def main(task, profile_name, prefix, artifact, session_text, pred, budget_s, driver_file, user="admin", cli="client"):
    from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
    from pzt import fixture as fx, profile                          # noqa: E402
    from pzt.bus import resolve_side                                # noqa: E402
    from pzt.harness import lint_paths                              # noqa: E402
    from pzt.paths import new_run_dir                               # noqa: E402
    from pzt.session import Timeline, attach_clients, make_client, make_server, teardown, verify   # noqa: E402

    prof = profile.load(profile_name)
    rec_fx = fx.load(prof.fixture)
    run_id, run_dir = new_run_dir(prefix)
    tl = Timeline()
    clients, started = {}, []
    holder = {"server": None}
    out = {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
           "world_changes": {"restored": f"fixture {prof.fixture} restored into the run dir", "left_in_place": []}}
    xs = X.Xs(out, node=lambda side: resolve_side(side, holder["server"], clients), tl=tl, clients=clients,
              ask=ask, budget_s=budget_s, predictions=pred, user="admin")   # the -debug client's park is the guard
    xs.path = os.path.join(run_dir, artifact)
    S = Sess(xs, user=user, cli=cli, run_dir=run_dir, game_dir=rec_fx.get("game_dir"))
    S.launch = launch_real(make_client, prof, rec_fx, started, tl)
    doctor_clean, doctor_text = doctor()
    out.update({
        "run_id": run_id, "task": task, "session": session_text, "driver": driver_file, "lib": LIB_FILE, "user": user,
        "users": list(prof.users), "profile": prof.report(),
        "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                    "build": rec_fx.get("build")},
        "argv": sys.argv[1:], "commit": git_say("rev-parse", "--short", "HEAD"),
        "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
        "harness_lua_dirty": git_dirty(LUA_DIR)[0],
        "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
        "xlib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/xlib.py"),
        "lib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/" + LIB_FILE),
        "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
        "meta": {"staged_mod": STAGE_MOD, "staged_manifest": f"{STAGE_ROOT}/{MANIFEST_NAME}",
                 "staging": "python tools/release_pack.py stage mod/NutritionRevamp --out " + STAGE_OUT +
                            " (before the boots); the driver checks it and never stages"},
        "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                      if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict,
                                                                             re.Pattern))
                      and k not in ("REPO",)},
        "predictions": pred,
    })
    if not doctor_clean:
        xs.refuse("doctor not clean; the session was not started (CLAUDE.md s5)")
    if out["harness_lua_dirty"]:
        xs.refuse("the harness Lua is dirty; commit before the boot (CLAUDE.md s5)")
    mg = staged_gate(out, xs, git_say, git_dirty)
    want = f'"value": "{mg.get("staged_version")}"'
    vrows = [v for v in prof.verify if v.get("args") == f"{NR}.version"]
    mg["verify_rows_match"] = bool(vrows) and all(str(v.get("expect")) == want for v in vrows)
    if not (mg["ok"] and mg["verify_rows_match"]):
        xs.refuse(f"the staged copy does not match the clean tree or the verify rows: {mg!r}; not started")
    found, ok = harness_markers_ok()
    out["meta"]["harness_markers_found"] = found
    if not ok:
        xs.refuse("a repository harness file lacks a marker; not started")
    m0 = xs.mem("preboot")
    if not X.memory_ok(m0["free_gb"], MIN_FREE_GB):
        xs.refuse(f"free memory {m0['free_gb']} GB under {MIN_FREE_GB} GB; the session was not started")
    out["lint_errors"] = lint_paths(prof.sources)
    if out["lint_errors"]:
        xs.refuse("the layout lint found an ERROR in a profile mod folder; the session was not started")
    try:
        shutil.copyfile(os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME), os.path.join(run_dir, MANIFEST_NAME))
        xs.copied.append(MANIFEST_NAME)
    except OSError as e:
        out["meta"]["manifest_copy_error"] = f"{type(e).__name__}: {e}"
    server = None
    phases = {"19": S.t19_body, "20": S.t20_body, "21": S.t21_body, "22": S.t22_body}[task]
    try:
        server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None, ini=prof.ini, gclog=prof.gclog)
        holder["server"] = server
        xs.server = server
        out["server_launch_wall"] = xs.wall()
        server.start(timeout=prof.server_timeout)
        out["server_started_wall"] = xs.wall()
        tl.mark("server_started")
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
            S.body_run(phases())
    except Exception as e:                         # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)

        def read_logs():
            L = out["logs"] = {"patterns": {"log": LOG_RX.pattern}}
            if server is not None:
                L["server"], L["server_echo_excluded"] = X.grep_noecho(server.log_path, LOG_RX, 300, ECHO_RX,
                                                                         NEVER_RX)
                L["mod_error"] = [ln for ln in L["server"] if MOD_ERR_RX.search(ln)][:40]
                L["creation"] = read_log_lines(server.log_path)
                try:
                    shutil.copyfile(server.log_path, os.path.join(run_dir, "server-stdout.log"))
                    xs.copied.append("server-stdout.log")
                except OSError as e:
                    L["log_copy_error"] = f"{type(e).__name__}: {e}"
            for c in every:
                lines, _ = X.grep_noecho(c.console, LOG_RX, 80, ECHO_RX, NEVER_RX)
                L.setdefault("clients", {})[getattr(c, "username", "?")] = lines

        def grade_all():
            if task == "19":
                S.t19_grade()
            elif task == "20":
                S.t20_grade()
            elif task == "21":
                S.t21_grade((out.get("logs") or {}).get("creation") or [])
            elif task == "22":
                S.t22_grade()
            out["verdict_summary"] = {k: v.get("verdict") for k, v in out["verdicts"].items()}

        xs.finish(teardown, hard_kill, every, read_logs=read_logs, grade_all=grade_all)
        xs.mem("after")
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, artifact)
    print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                      "bus_dead": out.get("bus_dead"), "error": out.get("error"), "abort": out.get("abort"),
                      "budget_stop": out.get("budget_stop"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "summary_error": out.get("summary_error"), "logs_error": out.get("logs_error"),
                      "run_id": run_id, "run_dir": run_dir, "memory": out.get("memory"),
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str)[:8000])
    return out
