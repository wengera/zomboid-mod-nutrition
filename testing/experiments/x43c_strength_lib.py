"""x43c_strength_lib -- the session engine of Plan 13 Task 22b's two live follow-ups: x435_surplus.py (the surplus growth
arm) and x436_creation.py (creation after Tasks 10b and 10c). Started from x43b_strength_lib.py (frozen with x434) and
its parent x43_strength_lib.py (frozen with x431), on testing/experiments/xlib.py. What changed from x43b:
  1. the creation expectation is the staged kernel's own K.body.create and K.body.new (lupa), never a Python table:
     Task 10b scales the fat start by the start lean (Obese FMI 10.5) and Task 10c makes a thin pick fat-only (the
     muscle pick's lean, 10 % or 6.5 % body fat, fmRef the no-pick fat), so the frozen libs' tables are stale;
  2. ruling 13-46's anti-stacking pairs are gone (Task 10c), so the expected strips read the server's definitions only;
  3. the level grade reads K.strength.heldLevel (Task 10c: a rise at the whole number, a drop only DROP_MARGIN 0.25
     below the written level), never shown's floor alone;
  4. E is placed through body.inDay (x434's defect 1: body.ebDay is recomputed each minute as inDay - eeDay,
     NR_Kernel_Energy.lua:271, :283, :400), at the last drain before the close, eeDay read in the same call window;
  5. admin is kept alive without eating (x434's defect 2): the harness's stats.set thirst 0 hunger 0 once a game hour
     (the writer reads a THIRST fall below its last write as an auto-drink sip and lands it as water, 0 kcal, so inDay
     never moves; HUNGER is rewritten from the satiety target at the next minute, capped under the starving level),
     and a death check (isDead and the overall body health) at every upkeep and every close;
  6. the server log, already in the run folder, is named for the artifact copy without a self-copy (x43's SameFileError).

Every session boots the STAGED release copy (release/plan13-x43c, `python tools/release_pack.py stage
mod/NutritionRevamp --out release/plan13-x43c`, made before the boots; the driver checks its MANIFEST against
release_pack.manifest() of a clean mod/NutritionRevamp at HEAD and refuses on a mismatch; CLAUDE.md s5, x201),
Nutrition false (ruling T18-1), DayLength 1 (a game minute is 0.625 s of wall at true multiplier 1), build 42.21.0.

THE RECORD READS: the mod's in-memory record of a user (lua.read record:<user>, never through S.get) as the body's
scalars and its seven-day rings in two lua.read calls (64 paths a call). Every field but the day accumulators (pDay,
ebDay, eeDay, inDay, alcDay, sigDay), lastAgeH, wday and energyState moves only at the day close.

x435 (profile x43c-surplus: fixture default, admin -debug, [sandbox.NR] StrengthTimeScale 30 and
StrengthIncidentalWeight 1). Phases:
  S   the record, the strength parameters the server runs (ts, incidental, xpPerSet, R), the clock, the death check.
  D   GROWTH_DAYS graded closes (one lead-in close first when the session starts at or past LEAD_HOUR). Each day:
      time.multiplier DAY_MULT (restored in a finally); once a game hour (GRANT_GAP_H) the upkeep (stats.set admin
      thirst 0 hunger 0, then the death check) and, on a graded day, server xp.grant admin Strength GRANT_XP (xpPerSet x
      20 / 7 / GRANTS, the day's signal 20/7 sets), Strength's XP read before each grant (the level-10 cap gate); at hour
      SLOW_HOUR the multiplier back to the value read before; one more upkeep; at PLACE_MIN game minutes before the
      boundary the record whole (pre) and record.set body.pDay P_GKG x the body mass; at E_PLACE_MIN game minutes
      before it body.eeDay, body.inDay and body.dayIndex read and record.set body.inDay eeDay + E_KCAL at once, then
      dayIndex read back (the set landed before the close); once dayIndex moves the record whole (post), Strength's
      level, the server's stats.get trait list and the death check. A day whose death check reads admin dead ends D.

x436 (profile x43c-creation: fixture two, admin -debug then bob, the subject, release user role). Phases:
  S   the sandbox's CharacterFreePoints and NegativeTraitsPenalty, every case's traits' server definitions (trait.def:
      cost and exclusions), bob's profession, and the display names: trait.def on bob's client for Underweight,
      VeryUnderweight, Overweight and Obese (the definition's getLabel, translated at load; a pcall'd read).
  Ca..Cg  respawns of bob through x192's route (health.reduce bob 110; ISPostDeathUI onRespawn; the spawn list's
      clickNext; CoopCharacterCreation accept), each but (a) after creation.picks arms its list (CASES). Each landing
      is NutritionRevamp.server.creation.stats.created rising; STR levelWrites read before the respawn; PAIR_DELAY_S
      after the landing body.levelDue polled false (the first minute's re-pin), then bob's profession, the record whole,
      the effects and acute reads, a same-second pair (the server's stats.get and perk.xp Strength beside bob's client
      stats.get and perk.xp Strength), levelWrites again, and the client mirror's energy fields (requestMirror).
  E1  after case (e) only: the clock raised (BOUNDARY_MULT, restored and read back in a finally) until bob's
      body.dayIndex moves (his first close), then record:bob acute.refeedRisk, acute.bmi, acute.starvedDays and
      effects.pe polled for ACUTE_CAP_S.

THE GRADES (pure; each has a failing case in testing/tests/test_x43c_strength_lib.py; a grade on zero samples is
unmeasured, never as_predicted):
  35_E<k>       the close's E (post eb7[7]) within E_TOL of E_KCAL and the inDay set landed before the close.
  35_close<k>   the close's lm and T equal the kernel's replay of the record's own pre-close body under the close's
                recorded inputs (S = post body.S, p = post p7[7] / the pre-close mass, E = post eb7[7], tdee = max(pre
                eeDay, ree(lm)), alcohol pre alcDay / mass) to LM_TOL and T_TOL (ruling 8-R); the surplus arm exercised:
                E >= 0 (the partition's surplus arm) and the growth law's grow > 0 (its path named: grow or regain, the
                gates); unmeasured when the replay reads tdee, when E < 0 or when the growth arm reads 0.
  35_level<k>   the native level K.strength.heldLevel(level(lm, N0, T), the pre-close wroteL) and its band, on the server.
  35_surplus    at least MIN_GOOD closes (k >= 1) with 35_E and 35_close as_predicted.
  36_<c>_body   lm, fm, F0, Fc, Pk, N0 and fmRef of the record equal K.body.create's spec to 1e-9; the weight lm + lx +
                fm, the body-fat share fm / (lm + fm) and fatDep (fmRef - fm) / fmRef equal the spec's (0 for a non-thin
                pick) to 1e-9.
  36_<c>_traits the record's fatT, thinT and band equal K.body.new's (the thin rung held by the body-fat axis); in a
                same-second pair, the server's and the client's weight equal lm + lx + fm, both Strength levels the
                written level, both trait lists hold its band and the rung's weight trait and no other, and no stripped
                trait.
  36_<c>_xp     after the first minute: body.levelDue false, STR levelWrites up by at least two over the respawn (the
                creation write and the re-pin), the server's Strength XP K.strength.pinXp(n, frac) to XP_TOL and the
                client's level n.
  36_<c>_strips the server log's strip lines for the case name exactly the expected strips in that order.
  36_<c>_hunger the server's body.energyState within ES_TOL of K.deficit.state(0, fatDep) and on the same ENERGY_AT rung,
                above 1 for a thin pick; the client mirror's level (body_energyLevel, else the rung of body_energyState),
                when read, on that rung.
  36_names      the client's labels of Underweight, VeryUnderweight and Overweight equal the staged UI.json's display
                names (Overly Lean, Gaunt, Overfat), Obese's stays Obese; unmeasured when no label was read.
  36_e_refeed   after (e)'s first close: acute.refeedRisk 2 and effects.pe 4 (test_weak_with_a_thin_pick_starts_
                malnourished_by_bmi).

Reply shapes the lib reads are the harness's own (@reply lines): lua.read {ok, side, root, n, values, tables, types,
missing}; record.set {ok, side, user, path, key, keyType, before, beforeType, after, afterType}; perk.xp {perk, user,
side, xp, level, serverWorldAge} (client {perk, side, xp, level}); xp.grant {ok, perk, amount, side, xpBefore, xpAfter,
levelBefore, levelAfter}; stats.get {weight, traitList, ..., worldAge, wall}; stats.set {calories, ..., hunger,
thirst, ..., applied}; lua.call {ok, side, path, nargs, r1, r2, r3}; lua.callm {ok, side, path, method, nargs, r1, r2,
r3}; health.reduce {ok, side, requested, before, after, health, parts}; creation.picks {ok, armed, picks}; trait.def
{ok, side, trait, field, cost, free, xpBoosts, xpBoostsRead, exclusive, granted, label, description}; witness.chain
{ok, value, hops, failedAt}; time.snapshot {worldAge, hour, minutes, mult, trueMult, wall}; time.multiplier a string;
players a list of usernames or {}.

FROZEN WITH ITS FIRST RUN: once x435 has run, this file is never edited (CLAUDE.md s5); a later change is a new file.
"""
import glob
import json
import math
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))                    # testing/
sys.path.insert(0, HERE)                                     # experiments/

import xlib as X                                                 # noqa: E402

REPO = X.REPO
SRV = X.SRV
LIB_FILE = "x43c_strength_lib.py"
NR = "NutritionRevamp"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
MOD_DIR = "mod/NutritionRevamp"
STAGE_OUT = "release/plan13-x43c"
STAGE_ROOT = STAGE_OUT + "/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
STAGED_SHARED = STAGE_MOD + "/common/media/lua/shared"
STAGED_CORE = "common/media/lua/shared/NR_Core.lua"
STAGED_UI = STAGED_SHARED + "/Translate/EN/UI.json"
MANIFEST_NAME = "MANIFEST.json"
HARNESS_FILES = {"PZTestKit_Server.lua": LUA_DIR + "/server/PZTestKit_Server.lua",
                 "PZTestKit_Client.lua": LUA_DIR + "/client/PZTestKit_Client.lua",
                 "PZTestKit_Core.lua": LUA_DIR + "/shared/PZTestKit_Core.lua"}
HARNESS_MARKERS = {
    "PZTestKit_Server.lua": ('TK.register("record.set", function(argv)', 'TK.register("xp.grant", function(argv)',
                             'TK.register("perk.xp", function(argv)', 'TK.register("stats.set", function(argv)',
                             'TK.register("witness.chain", function(argv)'),
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
DROP_MARGIN = 0.25                     # K.strength.DROP_MARGIN (Plan 13 Task 10c)
BANDS = (("weak", 1), ("feeble", 4), (None, 5), ("stout", 8), ("strong", 10))   # #2157
MUSCLE = ("weak", "feeble", "stout", "strong")
WEIGHTS = ("emaciated", "veryunderweight", "underweight", "overweight", "obese")
KERNEL_WEIGHT = {"overweight": "OVERWEIGHT", "obese": "OBESE", "underweight": "UNDERWEIGHT",
                 "veryunderweight": "VERY_UNDERWEIGHT"}
FAT_WORD = {1: "overweight", 2: "obese"}                    # K.traits.WANT
THIN_WORD = {1: "underweight", 2: "veryunderweight", 3: "emaciated"}
READY_CAP_S = 90.0
MIN_RUNS = 3
STR_STATS = f"{NR}.server.strength.stats"
OPT_STR = f"{NR}.server.options.strength"
XP_TOL = 1.0
REQUEST_GAP_S = 5.5                    # past NR_Server_Bus.lua's REQUEST_GAP_MS (5000)
ARRIVE_CAP_S = 8.0
PAIR_GAP_MAX_S = 1.0
# x435
GROWTH_DAYS = 4
MIN_GOOD = 3
LEAD_HOUR = 12.0
DAY_MULT = 8.0
GRANTS = 10
GRANT_GAP_H = 1.0
SETS_A_DAY = 20.0 / 7.0
SLOW_HOUR = 23.0
PLACE_MIN = 8.0
E_PLACE_MIN = 4.0
P_GKG = 2.0
E_KCAL = 260.0
E_TOL = 20.0
EE_MARGIN = 150.0
LM_TOL = 1e-6
T_TOL = 1e-9
CLOSE_CAP_S = 30.0
DAY_CAP_S = 300.0
# x436
DEATH_CAP_S = 20.0
UI_CAP_S = 30.0
CREATE_CAP_S = 15.0
LAND_CAP_S = 60.0
PAIR_DELAY_S = 4.0
DUE_CAP_S = 10.0
WEIGHT_TOL = 0.01
BODY_TOL = 1e-9
ES_TOL = 0.02
G_EXTRAS = ("ThickSkinned", "KeenHearing", "FastHealer")
CASES = (("a", ()), ("b", ("Strong", "Obese")), ("c", ("Weak", "Overweight")), ("d", ("Underweight",)),
         ("e", ("Weak", "VeryUnderweight")), ("f", ("Feeble", "Underweight")),
         ("g", ("Obese", "Overweight") + G_EXTRAS))
REFEED_CASE = "e"
BOUNDARY_MULT = 20.0
BOUNDARY_CAP_S = 120.0
ACUTE_CAP_S = 10.0
NAME_TRAITS = ("Underweight", "VeryUnderweight", "Overweight", "Obese")
NAME_KEYS = {"underweight": "UI_NR_trait_underweightname", "veryunderweight": "UI_NR_trait_veryunderweightname",
             "overweight": "UI_NR_trait_overweightname"}
OBESE_LABEL = "Obese"                  # vanilla's own name, unchanged by Task 10c
PROFESSIONS_TXT = os.path.join("media", "scripts", "generated", "characters", "character_professions.txt")
ECHO_RX = re.compile(r"PZTK: ")
NEVER_RX = re.compile(r"(?!x)x")
LOG_RX = re.compile(r"NutritionRevamp|LuaError|STACK TRACE|lua error|attempted index|tried to call nil", re.I)
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|failed:|STACK TRACE|attempted index|tried to call nil")
STRIP_RX = re.compile(r"\[NutritionRevamp\] creation: (\S+) loses (.+?) \((.*)\)\s*$")
CREATED_RX = re.compile(r"\[NutritionRevamp\] creation: (\S+) muscle=(\S+) weight=(\S+) prof=(\S+)")

BODY_SCALARS = ("lm", "fm", "lx", "F0", "Fc", "Pk", "N0", "T", "Tgrace", "grace", "S", "sigDay", "dayIndex", "wday",
                "lastAgeH", "levelDue", "wroteL", "pDay", "ebDay", "eeDay", "inDay", "inDayClosed", "alcDay", "band",
                "fatT", "thinT", "fmRef", "tDisuse", "bornAge", "sex", "delta", "lm0dis", "at", "energyState")
WEEK_N = 7
RECORD_EXTRA = ("acute.refeedRisk", "acute.bmi", "acute.starvedDays", "effects.pe")


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
    """A trait name in one spelling: lower case, the registry prefix and every space or underscore dropped."""
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


def shown(L):
    """K.strength.shown: the native level floor(L + 1e-9) clamped to [0, 10] and the bar's fraction."""
    n = max(0, min(L_MAX, math.floor(L + 1e-9)))
    frac = max(0.0, L - n) if (L >= 0 and n < L_MAX) else 0.0
    return n, frac


def held_level(L, Lw):
    """K.strength.heldLevel (Task 10c): rises to shown's floor above Lw; drops to floor(L + DROP_MARGIN) only when
    L < Lw - DROP_MARGIN; else holds Lw; frac L - n above n and below L_MAX, else 0."""
    n, frac = shown(L)
    lw = num(Lw)
    if lw is None or not math.isfinite(lw) or n > lw:
        return n, frac
    if L < lw - DROP_MARGIN:
        n = max(0, min(L_MAX, math.floor(L + DROP_MARGIN + 1e-9)))
    else:
        n = int(max(0, min(L_MAX, lw)))
    frac = (L - n) if (L > n and n < L_MAX) else 0.0
    return n, frac


def pin_xp(n, frac):
    """K.strength.pinXp: level n's starting total plus frac of the level's cost, at most 1 below the next total; the
    level-9 total at 10."""
    if n >= L_MAX:
        return TOTALS[L_MAX - 1]
    gap = TOTALS[n + 1] - TOTALS[n]
    return TOTALS[n] + min(frac * gap, gap - 1)


def traits_of(stats):
    lst = (stats or {}).get("traitList")
    if lst == {}:
        lst = []                                         # the harness answers an empty list as {}
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


def weight_word(fatT, thinT):
    """K.traits.WANT's one weight trait of the rungs (normalised), or None."""
    t, f = num(thinT) or 0, num(fatT) or 0
    if t > 0:
        return THIN_WORD.get(int(t))
    if f > 0:
        return FAT_WORD.get(int(f))
    return None


def energy_rung(es, at):
    """K.view.rung over the ENERGY_AT ladder: the highest bound es reaches, 0 below the first."""
    v = num(es)
    if v is None:
        return 0
    n = 0
    for i, b in enumerate(at):
        if v >= b:
            n = i + 1
    return n


def staged_names(path):
    """The display names the staged UI.json gives the three renamed traits (normalised trait -> label)."""
    try:
        with open(path, encoding="utf-8") as fh:
            ui = json.load(fh)
    except (OSError, ValueError):
        return {}
    return {t: ui.get(k) for t, k in NAME_KEYS.items()}


# ---------------------------------------------------------------- the creation expectations (pure + kernel)
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
    """Two picks exclude each other: either server definition's exclusion list names the other (Task 10c removed the
    mod's own pairs, ruling 13-46's table)."""
    ea = {norm(x) for x in (g(defs, a, "exclusive") or [])}
    eb = {norm(x) for x in (g(defs, b, "exclusive") or [])}
    return b in ea or a in eb


def expect_strips(picks, defs, prof_cost, free_points, penalty):
    """Ruling 13-16 under fix 3, on the server's definitions: picks sorted by |cost| descending, a tie by name; each
    excluded by a later-sorted pick still held is stripped; then, while the remaining points read below 0, the first
    kept positive pick in that order. Returns (stripped, kept), or (None, None) when a definition's cost is unread."""
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


def expect_body(kern, kept, prof_boost):
    """The creation body of the kept picks off the staged kernel (K.body.create, then K.body.new at the male values:
    NR.SexSpecific off): {lm, fm, F0, Fc, Pk, N0, fmRef, fatT, thinT, band, mass, bf, fatDep, level, native, frac,
    strengthBand, weight, es, energyLevel, muscle, weightPick}."""
    muscle = next((n for n in kept if n in MUSCLE), None)
    pick = next((n for n in kept if n in KERNEL_WEIGHT), None)
    spec = kern.create(muscle.upper() if muscle else None, KERNEL_WEIGHT.get(pick), 1, prof_boost)
    body = kern.new(spec, 1, 0.0)
    e = {k: spec[k] for k in ("lm", "fm", "F0", "Fc", "Pk", "N0", "fmRef")}
    e.update({"fatT": body["fatT"], "thinT": body["thinT"], "band": body["band"]})
    e["mass"] = e["lm"] + e["fm"]
    e["bf"] = e["fm"] / e["mass"]
    e["fatDep"] = max(0.0, min(1.0, (e["fmRef"] - e["fm"]) / e["fmRef"])) if e["fmRef"] > 0 else 0.0
    L = kern.level(e["lm"], e["N0"], 1.0, kern.params(None))
    n, frac = shown(L)
    e.update({"level": L, "native": n, "frac": frac, "strengthBand": band_of(n),
              "weight": weight_word(e["fatT"], e["thinT"]), "muscle": muscle, "weightPick": pick})
    e["es"] = kern.state(0.0, e["fatDep"])
    e["energyLevel"] = energy_rung(e["es"], kern.energy_at())
    return e


# ---------------------------------------------------------------- the grades (pure)
def grade_E(c):
    c = c or {}
    E = num(g(c, "post", f"eb7.{WEEK_N}"))
    pl = c.get("placed") or {}
    obs = {"E": E, "want": E_KCAL, "tol": E_TOL, "set": pl.get("inDay_set"), "eeDay_read": pl.get("eeDay"),
           "before_close": pl.get("before_close")}
    if not c.get("closed") or E is None:
        obs["why"] = "the close was not read"
        return "unmeasured", obs
    if not pl.get("inDay_set") or not pl.get("before_close"):
        obs["why"] = "the inDay set did not land before the close"
        return "unmeasured", obs
    obs["miss"] = E - E_KCAL
    if abs(E - E_KCAL) <= E_TOL:
        return "as_predicted", obs
    obs["why"] = f"E {E} off {E_KCAL} by more than {E_TOL} kcal"
    return "falsified", obs


def grade_surplus_close(c):
    c = c or {}
    rep = c.get("replay") or {}
    obs = {"lm": [g(c, "pre", "lm"), g(c, "post", "lm")], "T": [g(c, "pre", "T"), g(c, "post", "T")],
           "replay": rep, "inputs": c.get("inputs"), "path": rep.get("path"), "dayIndex": c.get("days")}
    if not c.get("closed") or not rep or rep.get("error"):
        obs["why"] = "the close was not read, or the replay did not run"
        return "unmeasured", obs
    if rep.get("tdee_sensitive"):
        obs["why"] = "the replay reads tdee: the energy gate is below saturation in the tdee band"
        return "unmeasured", obs
    path = rep.get("path") or {}
    if num(g(c, "inputs", "E")) is None or num(g(c, "inputs", "E")) < 0:
        obs["why"] = "E < 0: the deficit arm ran, not the surplus arm"
        return "unmeasured", obs
    if not (num(path.get("grow")) or 0) > 0:
        obs["why"] = "the growth arm read 0: the growth law was not exercised"
        return "unmeasured", obs
    lm1, T1, lm0 = num(g(c, "post", "lm")), num(g(c, "post", "T")), num(g(c, "pre", "lm"))
    obs["dF_live"] = (lm1 - lm0) if (lm1 is not None and lm0 is not None) else None
    obs["dF_replay"] = (rep["lm"] - lm0) if lm0 is not None else None
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


def grade_held_level(c, M):
    c = c or {}
    L = level_of(g(c, "post", "lm"), g(c, "post", "N0"), g(c, "post", "T"), M)
    Lw = g(c, "pre", "wroteL")
    n = held_level(L, Lw)[0] if L is not None else None
    traits = traits_of(c.get("stats"))
    obs = {"L": L, "wroteL_pre": Lw, "want_native": n, "want_band": band_of(n) if n is not None else None,
           "native": g(c, "xp", "level"), "wroteL_post": g(c, "post", "wroteL"), "bands": bands_held(traits)}
    if not c.get("closed") or L is None or traits is None or num(g(c, "xp", "level")) is None:
        obs["why"] = "the close or a read is missing"
        return "unmeasured", obs
    bad = []
    if num(g(c, "xp", "level")) != n:
        bad.append("native level off heldLevel(level, wroteL)")
    want_b = [band_of(n)] if band_of(n) else []
    if bands_held(traits) != want_b:
        bad.append(f"bands {bands_held(traits)} not {want_b}")
    obs["bad"] = bad
    if bad:
        obs["why"] = "; ".join(bad)
        return "falsified", obs
    return "as_predicted", obs


def grade_surplus(verdicts, days):
    """At least MIN_GOOD graded closes (k >= 1) with both 35_E<k> and 35_close<k> as_predicted."""
    good = [k for k in days if k >= 1 and verdicts.get(f"35_E{k}") == "as_predicted"
            and verdicts.get(f"35_close{k}") == "as_predicted"]
    bad = [k for k in days if verdicts.get(f"35_close{k}") == "falsified" or verdicts.get(f"35_E{k}") == "falsified"]
    obs = {"good": good, "falsified_days": bad, "need": MIN_GOOD}
    if len(good) >= MIN_GOOD:
        return "as_predicted", obs
    if bad:
        obs["why"] = f"a close or its E falsified on day(s) {bad}"
        return "falsified", obs
    obs["why"] = f"{len(good)} good closes, under {MIN_GOOD}"
    return "unmeasured", obs


def grade_case_body(c):
    c = c or {}
    exp, body = c.get("expect") or {}, c.get("body") or {}
    keys = ("lm", "fm", "F0", "Fc", "Pk", "N0", "fmRef")
    obs = {"expect": {k: exp.get(k) for k in keys + ("mass", "bf", "fatDep", "muscle", "weightPick")},
           "record": {k: body.get(k) for k in keys + ("lx",)}}
    if not c.get("landed") or not exp or not body:
        obs["why"] = "the respawn never landed, or the record or the expectation is missing"
        return "unmeasured", obs
    bad = [k for k in keys if num(body.get(k)) is None or abs(num(body.get(k)) - exp[k]) > BODY_TOL]
    lm, fm, lx, ref = (num(body.get(k)) for k in ("lm", "fm", "lx", "fmRef"))
    if None not in (lm, fm, lx, ref) and lm + fm > 0 and ref > 0:
        rec = {"mass": lm + lx + fm, "bf": fm / (lm + fm), "fatDep": max(0.0, min(1.0, (ref - fm) / ref))}
        obs["derived"] = rec
        bad += [k for k in ("mass", "bf", "fatDep") if abs(rec[k] - exp[k]) > BODY_TOL]
    else:
        bad.append("derived")
    obs["bad"] = bad
    if bad:
        obs["why"] = "off K.body.create: " + ", ".join(bad)
        return "falsified", obs
    return "as_predicted", obs


def grade_case_traits(c):
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
           "record": {"fatT": body.get("fatT"), "thinT": body.get("thinT"), "band": body.get("band"),
                      "wroteL": body.get("wroteL")},
           "mass": mass, "want_native": exp.get("native"), "want_band": exp.get("strengthBand"),
           "want_weight": exp.get("weight"), "want_rungs": [exp.get("fatT"), exp.get("thinT"), exp.get("band")],
           "stripped": c.get("want_stripped"), "pair_gap_s": p.get("gap_s")}
    if not c.get("landed") or not exp or st is None or ct is None or mass is None:
        obs["why"] = "the respawn never landed, or a read is missing"
        return "unmeasured", obs
    if num(p.get("gap_s")) is None or num(p.get("gap_s")) > PAIR_GAP_MAX_S:
        obs["why"] = "the pair was not in the same second"
        return "unmeasured", obs
    bad = []
    if num(body.get("fatT")) != exp.get("fatT") or num(body.get("thinT")) != exp.get("thinT"):
        bad.append(f"record rungs {body.get('fatT')}/{body.get('thinT')} not {exp.get('fatT')}/{exp.get('thinT')}")
    if body.get("band") != exp.get("band"):
        bad.append(f"record band {body.get('band')} not {exp.get('band')}")
    want_bands = [exp["strengthBand"]] if exp.get("strengthBand") else []
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


def grade_case_xp(c):
    c = c or {}
    exp, body, p = c.get("expect") or {}, c.get("body") or {}, c.get("pair") or {}
    w0, w1 = num(c.get("levelWrites0")), num(c.get("levelWrites1"))
    xp = num(g(p, "server_xp", "xp"))
    want = pin_xp(exp["native"], exp["frac"]) if exp.get("native") is not None else None
    obs = {"levelDue": body.get("levelDue"), "due_wait": c.get("due_wait"), "levelWrites": [w0, w1],
           "xp": xp, "want_xp": want, "frac": exp.get("frac"), "client_level": g(p, "client_xp", "level"),
           "client_xp": g(p, "client_xp", "xp")}
    if not c.get("landed") or not exp or xp is None or w0 is None or w1 is None:
        obs["why"] = "the respawn never landed, or a read is missing"
        return "unmeasured", obs
    bad = []
    if body.get("levelDue") is not False:
        bad.append("levelDue not cleared after the first minute")
    if w1 - w0 < 2:
        bad.append(f"levelWrites rose {w1 - w0}, not the creation write and the re-pin")
    if want is None or abs(xp - want) > XP_TOL:
        bad.append(f"server XP {xp} off pinXp {want}")
    if num(g(p, "client_xp", "level")) != exp.get("native"):
        bad.append("the client's level off the written level")
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


def grade_case_hunger(c, at):
    c = c or {}
    exp, body, m = c.get("expect") or {}, c.get("body") or {}, c.get("mirror") or {}
    es = num(body.get("energyState"))
    want, want_lv = exp.get("es"), exp.get("energyLevel")
    cl = num(m.get("body_energyLevel"))
    if cl is None or cl != math.floor(cl):
        cl = energy_rung(m.get("body_energyState"), at) if num(m.get("body_energyState")) is not None else None
    obs = {"es": es, "want_es": want, "tol": ES_TOL, "rung": energy_rung(es, at) if es is not None else None,
           "want_level": want_lv, "client_level": cl, "client_state": m.get("body_energyState"),
           "client_held": m.get("body_energyLevel"), "fatDep": exp.get("fatDep"), "thin": (exp.get("thinT") or 0) > 0}
    if not c.get("landed") or not exp or es is None or want is None:
        obs["why"] = "the respawn never landed, or the energy state is unread"
        return "unmeasured", obs
    bad = []
    if abs(es - want) > ES_TOL:
        bad.append(f"energyState {es} off {want}")
    if energy_rung(es, at) != want_lv:
        bad.append(f"rung {energy_rung(es, at)} not {want_lv}")
    if obs["thin"] and not es > 1.0:
        bad.append("a thin start not above 1")
    if cl is not None and cl != want_lv:
        bad.append(f"client level {cl} not {want_lv}")
    obs["bad"] = bad
    if bad:
        obs["why"] = "; ".join(bad)
        return "falsified", obs
    return "as_predicted", obs


def grade_names(labels, want):
    labels, want = labels or {}, want or {}
    obs = {"labels": labels, "want": dict(want, obese=OBESE_LABEL)}
    read = {k: v for k, v in labels.items() if isinstance(v, str) and v}
    if not read or not want:
        obs["why"] = "no label was read, or the staged names are unread"
        return "unmeasured", obs
    bad = [k for k, v in obs["want"].items() if labels.get(k) != v]
    obs["bad"] = bad
    if bad:
        obs["why"] = "label(s) off the display names: " + ", ".join(bad)
        return "falsified", obs
    return "as_predicted", obs


def grade_refeed(r):
    r = r or {}
    obs = {"closed": r.get("closed"), "dayIndex": [r.get("day0"), r.get("day1")], "refeedRisk": r.get("refeedRisk"),
           "pe": r.get("pe"), "bmi": r.get("bmi"), "starvedDays": r.get("starvedDays")}
    if not r.get("closed") or num(r.get("refeedRisk")) is None or num(r.get("pe")) is None:
        obs["why"] = "the first close was not reached, or the risk or the grade is unread"
        return "unmeasured", obs
    bad = []
    if num(r.get("refeedRisk")) != 2:
        bad.append(f"refeedRisk {r.get('refeedRisk')} not 2")
    if num(r.get("pe")) != 4:
        bad.append(f"pe {r.get('pe')} not 4")
    obs["bad"] = bad
    if bad:
        obs["why"] = "; ".join(bad)
        return "falsified", obs
    return "as_predicted", obs


# ---------------------------------------------------------------- the kernel (the staged copy's, under lupa)
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

    def held(self, L, Lw):
        n, frac = self.K.strength.heldLevel(L, Lw)
        return int(n), float(frac)

    def state(self, eb, fatDep):
        return float(self.K.deficit.state(eb, fatDep))

    def energy_at(self):
        at = self.K.view.ENERGY_AT
        return tuple(float(at[i]) for i in range(1, len(at) + 1))

    def create(self, muscle, weight, sexIdx, boost):
        s = self.K.body.create(muscle, weight, self.params(None), sexIdx, boost)
        return {k: (float(s[k]) if k not in ("fatT", "thinT", "sexIdx") else int(s[k]))
                for k in ("lm", "F0", "Fc", "Pk", "N0", "fm", "fmRef", "fatT", "thinT", "sexIdx")}

    def new(self, spec, sex, ageH):
        t = self.table(spec)
        b = self.K.body.new(t, sex, ageH)
        return {"band": b.band, "fatT": int(b.fatT), "thinT": int(b.thinT), "fmRef": float(b.fmRef)}

    def _body(self, pre):
        b = {k: v for k, v in pre.items() if "." not in k and not k.startswith("_") and v is not None}
        for r in ("sig7", "eb7", "mass7", "p7"):
            b[r] = [pre.get(f"{r}.{i}", 0) for i in range(1, WEEK_N + 1)]
        b["bandWeek"] = [[pre.get(f"bandWeek.{i}.1", 0), pre.get(f"bandWeek.{i}.2", 0)] for i in range(1, WEEK_N + 1)]
        return self.table(b)

    def day(self, pre, S, p, E, tdee, alc, P):
        """K.strength.day on a copy of the pre-close body; returns {lm, T, lx, fm}."""
        body = self._body(pre)
        self.K.strength.day(body, S, p, E, tdee, alc, P, P.ts)
        return {"lm": float(body.lm), "T": float(body.T), "lx": float(body.lx), "fm": float(body.fm)}

    def path(self, pre, S, p, E, tdee, alc, P):
        """The growth law's arms on the pre-close body (K.strength.growth, a copy): grow and regain, the protein and
        energy gates, the status, and the partition arm by the sign of E."""
        body = self._body(pre)
        grow, regain = self.K.strength.growth(body, S, p, E, tdee, alc, P, P.ts)
        s = float(self.K.strength.status(body))
        fe = float(self.K.strength.fe(E, s, p, tdee, P))
        fp = float(self.K.strength.fp(p, P))
        return {"grow": float(grow), "regain": float(regain), "arm": "growth" if grow >= regain else "regain",
                "s": s, "fe": fe, "fp": fp, "partition": "surplus" if E >= 0 else "deficit",
                "saturated": fe >= 1.0 - 1e-12}


def replay_close(kern, P, pre, post):
    """The close's replay off its own recorded inputs: S = post body.S, p = post p7[7] / the pre-close mass, E = post
    eb7[7], alcohol pre alcDay / mass, tdee = max(pre eeDay, ree(lm)) and again EE_MARGIN above it; the path read at
    the first tdee."""
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
                "lm_hi": b["lm"], "path": kern.path(pre, S, p, E, t0, alc, P)}, \
            {"w": w, "S": S, "p": p, "E": E, "alc": alc, "eeDay_pre": ee, "ree": ree}
    except Exception as e:                                # noqa: BLE001 - recorded, graded unmeasured
        return {"error": f"{type(e).__name__}: {e}"}, None


# ---------------------------------------------------------------- the session
class Sess:
    """The scenario over an xlib.Xs; every wait goes through xs.clock and xs.sleep, so the tests run it fast."""

    def __init__(self, xs, user="admin", cli="client", run_dir=None, game_dir=None, shared_dir=None):
        self.xs = xs
        self.out = xs.out
        self.D = self.out.setdefault("checks", {})
        self.user = user
        self.cli = cli
        self.run_dir = run_dir
        self.game_dir = game_dir
        self.shared_dir = shared_dir or os.path.join(REPO, *STAGED_SHARED.split("/"))
        self.ui_path = os.path.join(REPO, *STAGED_UI.split("/"))
        self.last_req = None
        self.model = None
        self.P = None
        self.dead = False

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

    def rfield(self, tag, paths, user=None, log=True):
        return vals(self.lread(tag, SRV, f"record:{user or self.user}", list(paths), log=log))

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

    def level_writes(self, tag):
        p = f"{STR_STATS}.levelWrites"
        return num(self.gread(tag, [p], log=True).get(p))

    def death(self, tag, user=None):
        """The death check: isDead and the overall body health, server-side."""
        u = user or self.user
        d = self.k(tag + "_dead", SRV, "witness.chain", f"{u} isDead", log=False)
        h = self.k(tag + "_hp", SRV, "witness.chain", f"{u} getBodyDamage.getOverallBodyHealth", log=False)
        row = {"dead": str(d.get("value")).lower() == "true", "dead_raw": d.get("value"), "health": num(h.get("value")),
               "health_raw": h.get("value"), "wall": d.get("wall")}
        if u == self.user and row["dead"]:
            self.dead = True
        return row

    def upkeep(self, tag):
        """thirst and hunger held low through the harness setter (never by eating), then the death check."""
        s = self.k(tag + "_set", SRV, "stats.set", f"{self.user} thirst 0 hunger 0", log=False)
        row = {"applied": s.get("applied"), "thirst_after": s.get("thirst"), "hunger_after": s.get("hunger"),
               "error": s.get("error")}
        row["death"] = self.death(tag)
        return row

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
        keys = ("body_energyLevel", "body_energyState", "body_level", "body_band")
        lv = self.gread(tag + "_lv", [f"{NR}.client.mirror.{k}" for k in keys], side=self.cli, log=True)
        out = {"rc0": rc0, "request_ok": req.get("ok"), "arrived": a["done"]}
        out.update({k: lv.get(f"{NR}.client.mirror.{k}") for k in keys})
        return out

    def pair(self, tag, user, cli):
        p = {"server_stats": self.k(tag + "_s", SRV, "stats.get", user),
             "client_stats": self.k(tag + "_c", cli, "stats.get")}
        p["server_xp"] = self.xp(tag + "_sx", SRV, user)
        p["client_xp"] = self.xp(tag + "_cx", cli)
        w0, w1 = num(p["server_stats"].get("wall")), num(p["client_stats"].get("wall"))
        p["gap_s"] = abs(w1 - w0) if (w0 is not None and w1 is not None) else None
        return p

    def body_run(self, phases):
        for name, fn in phases:
            if self.xs.parked():
                self.out["abort"] = f"admin parked in the debugger before phase {name}"
                break
            self.xs.run_phase(name, fn)

    # ======================================================== x435: the surplus arm
    def t35_S(self):
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
        P["death"] = self.death("S")

    def grant_xp(self):
        xps = num((self.P or {}).get("xpPerSet"))
        return (xps * SETS_A_DAY / GRANTS) if xps else None

    def place_E(self, k, c, d0):
        """At E_PLACE_MIN before the boundary: eeDay read and inDay set to eeDay + E_KCAL in the same call window."""
        pl = c["placed"]
        f = self.bfield(f"D{k}_ee", ["eeDay", "inDay", "dayIndex"], log=True)
        ee = num(f.get("eeDay"))
        pl.update({"eeDay": ee, "inDay_before": f.get("inDay"), "day_at_read": f.get("dayIndex")})
        if ee is None or num(f.get("dayIndex")) != d0:
            pl["why"] = "eeDay unread or the close already ran"
            return
        r = self.k(f"D{k}_inDay", SRV, "record.set", f"{self.user} body.inDay {ee + E_KCAL!r}")
        pl["inDay_reply"] = r
        pl["inDay_set"] = r.get("ok") is True
        pl["day_after_set"] = self.bfield(f"D{k}_dset", ["dayIndex"], log=True)["dayIndex"]
        pl["before_close"] = num(pl["day_after_set"]) == d0

    def t35_day(self, k, grants):
        c = self.D[f"day{k}"] = {"grants": [], "upkeep": [], "closed": False, "graded": grants, "placed": {}}
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
        last_hour = boundary - (24.0 - SLOW_HOUR) - 0.25
        try:
            c["raise"] = self.set_mult(DAY_MULT, f"D{k}_raise")
            nxt = a0
            for i in range(GRANTS):
                if nxt >= last_hour and i > 0:
                    break
                self.wait_age(nxt, f"D{k}_g{i}_wait", 60.0)
                up = self.upkeep(f"D{k}_g{i}")
                c["upkeep"].append(up)
                if self.dead:
                    c["error"] = "admin dead"
                    return c
                if grants and amt:
                    gate = self.xp(f"D{k}_g{i}_xp")
                    row = {"i": i, "xp_open": gate["xp"], "level_open": gate["level"]}
                    if gate["xp"] is None or gate["xp"] >= CAP_XP:
                        row["skipped"] = "at the level-10 cap or unread"
                    else:
                        a = self.k(f"D{k}_g{i}", SRV, "xp.grant", f"{self.user} Strength {amt!r}")
                        row.update({"xpBefore": a.get("xpBefore"), "xpAfter": a.get("xpAfter"),
                                    "levelAfter": a.get("levelAfter"), "ok": a.get("ok")})
                    c["grants"].append(row)
                nxt = min((self.age(f"D{k}_g{i}_age") or nxt) + GRANT_GAP_H, last_hour)
            c["slow_wait"] = self.wait_age(boundary - (24.0 - SLOW_HOUR), f"D{k}_slow", DAY_CAP_S, 0.5)
        finally:
            c["restore"] = self.restore_mult(restore_to, f"D{k}_restore")
        c["upkeep"].append(self.upkeep(f"D{k}_last"))
        if self.dead:
            c["error"] = "admin dead"
            return c
        c["place_wait"] = self.wait_age(boundary - PLACE_MIN / 60.0, f"D{k}_place", DAY_CAP_S / 2, 0.2)
        pre = self.body(f"D{k}_pre")
        c["pre"] = pre
        d0 = num(pre.get("dayIndex"))
        w = None
        if all(num(pre.get(x)) is not None for x in ("fm", "lm", "lx")):
            w = num(pre["fm"]) + num(pre["lm"]) + num(pre["lx"])
        c["placed"]["w"] = w
        if w is not None and d0 is not None:
            c["placed"]["pDay"] = self.k(f"D{k}_pDay", SRV, "record.set", f"{self.user} body.pDay {P_GKG * w!r}")
            c["e_wait"] = self.wait_age(boundary - E_PLACE_MIN / 60.0, f"D{k}_ewait", DAY_CAP_S / 2, 0.1)
            self.place_E(k, c, d0)

        def moved():
            d = num(self.bfield(f"D{k}_dpoll", ["dayIndex"])["dayIndex"])
            return (d is not None and d0 is not None and d != d0), d
        c["close_wait"] = self.poll(f"D{k}_close", moved, CLOSE_CAP_S, 0.3)
        c["closed"] = bool(c["close_wait"]["done"])
        self.sleep_until(self.xs.clock() + SETTLE_S)
        c["post"] = self.body(f"D{k}_post")
        c["days"] = [d0, num(c["post"].get("dayIndex"))]
        c["xp"] = self.xp(f"D{k}_lvl")
        c["stats"] = self.k(f"D{k}_stats", SRV, "stats.get", self.user)
        c["death_after"] = self.death(f"D{k}_after")
        return c

    def t35_D(self):
        a0 = self.age("D_age_start")
        lead = a0 is not None and (a0 % 24.0) >= LEAD_HOUR
        self.D["lead_in"] = lead
        if lead:
            self.t35_day(0, False)
        for k in range(1, GROWTH_DAYS + 1):
            if self.dead:
                self.xs.note(f"D: admin dead before day {k}; the remaining days are not run")
                break
            self.xs.check()
            self.t35_day(k, True)

    def t35_body(self):
        return (("S", self.t35_S), ("D", self.t35_D))

    def t35_grade(self, kern=None):
        xs = self.xs
        try:
            kern = kern or Kernel(self.shared_dir)
            P = kern.params({"StrengthTimeScale": 30.0, "StrengthIncidentalWeight": 1.0})
            self.out.setdefault("readings", {})["replay_P"] = {"ts": float(P.ts), "incidental": float(P.incidental),
                                                               "xpPerSet": float(P.xpPerSet), "R": float(P.R),
                                                               "server": self.P or {}}
        except Exception as e:                       # noqa: BLE001
            kern, P = None, None
            self.out.setdefault("readings", {})["replay_error"] = f"{type(e).__name__}: {e}"
        days = []
        for k in range(0, GROWTH_DAYS + 1):
            c = self.D.get(f"day{k}")
            if c is None:
                continue
            days.append(k)
            if c.get("closed") and kern is not None and c.get("pre") and c.get("post"):
                c["replay"], c["inputs"] = replay_close(kern, P, c["pre"], c["post"])
            v, o = grade_E(c)
            xs.grade(f"35_E{k}", v, o, f"E at the close off +{E_KCAL:g} by more than {E_TOL:g} kcal")
            v, o = grade_surplus_close(c)
            xs.grade(f"35_close{k}", v, o, "lm off the replay by more than 1e-6 kg or T by more than 1e-9")
            v, o = grade_held_level(c, self.model)
            xs.grade(f"35_level{k}", v, o, "native level or band off heldLevel(level(lm, N0, T), wroteL)")
        verdicts = {k: v.get("verdict") for k, v in self.out["verdicts"].items()}
        v, o = grade_surplus(verdicts, days)
        xs.grade("35_surplus", v, o, f"fewer than {MIN_GOOD} surplus closes reproduce the replay at E +{E_KCAL:g}")

    # ======================================================== x436: creation
    def mcall(self, tag, args):
        return self.k(tag, self.cli, "lua.callm", args)

    def created(self, tag):
        p = f"{NR}.server.creation.stats.created"
        return num(self.gread(tag, [p]).get(p)) or 0

    def t36_S(self):
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
                             "xpBoosts": a.get("xpBoosts"), "ok": a.get("ok"), "trait": a.get("trait"),
                             "label": a.get("label")}
        P["defs"] = defs
        labels = {}
        for t in NAME_TRAITS:
            a = self.k(f"S_label_{t}", self.cli, "trait.def", t)
            labels[norm(t)] = a.get("label")
        P["labels"] = labels
        P["want_names"] = staged_names(self.ui_path)
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

    def t36_case(self, label, picks):
        c = self.D[f"C{label}"] = {"picks": list(picks)}
        if picks:
            arm = self.k(f"C{label}_arm", self.cli, "creation.picks", " ".join(picks))
            c["arm"] = arm
            if arm.get("armed") is not True:
                c["unmeasured"] = "creation.picks did not arm"
                return
        c["levelWrites0"] = self.level_writes(f"C{label}_lw0")
        R = self.respawn(f"C{label}")
        c.update({k: R.get(k) for k in ("landed", "dead", "ui", "unmeasured", "count_before")})
        c["route"] = {k: R.get(k) for k in ("onRespawn", "screens", "clickNext", "accept")}
        if picks:
            c["fired"] = self.gread(f"C{label}_fired", ["TK.picksFired.count", "TK.picksFired.error"], side=self.cli,
                                    log=True)
        if not R.get("landed"):
            return
        self.sleep_until(R["landed_clock"] + PAIR_DELAY_S)

        def due():
            v = self.bfield(f"C{label}_due", ["levelDue"])["levelDue"]
            return v is False, v
        c["due_wait"] = self.poll(f"C{label}_due", due, DUE_CAP_S, 0.5)
        c["profession"] = self.k(f"C{label}_prof", SRV, "witness.chain",
                                 f"{self.user} getDescriptor.getCharacterProfession").get("value")
        c["profession_name"] = self.k(f"C{label}_profn", SRV, "witness.chain",
                                      f"{self.user} getDescriptor.getCharacterProfession.getName").get("value")
        c["body"] = self.body(f"C{label}_body")
        c["record"] = self.rfield(f"C{label}_rec", RECORD_EXTRA)
        c["pair"] = self.pair(f"C{label}_pair", self.user, self.cli)
        c["levelWrites1"] = self.level_writes(f"C{label}_lw1")
        c["mirror"] = self.request_mirror(f"C{label}_mirror")

    def t36_first_close(self):
        r = self.D["E1"] = {"closed": False}
        ce = self.D.get(f"C{REFEED_CASE}") or {}
        if not ce.get("landed"):
            r["skipped"] = f"case ({REFEED_CASE}) did not land"
            return
        d0 = num(self.bfield("E1_d0", ["dayIndex"], log=True)["dayIndex"])
        r["day0"] = d0
        r["restore_to"] = self.mult_read("E1_mult0")
        if d0 is None or r["restore_to"] is None:
            r["skipped"] = "dayIndex or trueMult unread"
            return
        try:
            r["raise"] = self.set_mult(BOUNDARY_MULT, "E1_raise")

            def moved():
                d = num(self.bfield("E1_poll", ["dayIndex"])["dayIndex"])
                return (d is not None and d != d0), d
            r["wait"] = self.poll("E1_wait", moved, BOUNDARY_CAP_S, 0.5)
        finally:
            r["restore"] = self.restore_mult(r["restore_to"], "E1_restore")
        r["closed"] = bool(r["wait"]["done"])
        if not r["closed"]:
            return
        r["day1"] = num(self.bfield("E1_d1", ["dayIndex"], log=True)["dayIndex"])

        def read():
            v = self.rfield("E1_rec", RECORD_EXTRA, log=False)
            ok = num(v.get("acute.refeedRisk")) is not None and num(v.get("acute.bmi")) not in (None, 0)
            return ok, v
        p = self.poll("E1_read", read, ACUTE_CAP_S, 0.5)
        v = p["last"] or {}
        r.update({"refeedRisk": v.get("acute.refeedRisk"), "bmi": v.get("acute.bmi"),
                  "starvedDays": v.get("acute.starvedDays"), "pe": v.get("effects.pe"), "polls": p["polls"]})
        r["body"] = self.body("E1_body")
        self.out["world_changes"]["left_in_place"].append(
            "E1: the clock raised to bob's first close after case (e), then restored")

    def t36_body(self):
        out = [("S", self.t36_S)]
        for lab, p in CASES:
            out.append((f"C{lab}", (lambda lab=lab, p=p: self.t36_case(lab, p))))
            if lab == REFEED_CASE:
                out.append(("E1", self.t36_first_close))
        return tuple(out)

    def t36_expect(self, c, kern):
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
        c["expect"] = expect_body(kern, kept, prow[1])

    def t36_grade(self, log_lines=None, kern=None):
        xs = self.xs
        try:
            kern = kern or Kernel(self.shared_dir)
            at = kern.energy_at()
        except Exception as e:                       # noqa: BLE001
            kern, at = None, ()
            self.out.setdefault("readings", {})["kernel_error"] = f"{type(e).__name__}: {e}"
        creations = strips_by_case(log_lines or [], self.user)
        self.out.setdefault("readings", {})["creations"] = creations
        landed = [lab for lab, _p in CASES if (self.D.get(f"C{lab}") or {}).get("landed")]
        for lab, _p in CASES:
            c = self.D.get(f"C{lab}") or {}
            if c.get("landed") and kern is not None:
                self.t36_expect(c, kern)
            idx = landed.index(lab) if lab in landed else None
            cr = creations[idx] if (idx is not None and len(creations) == len(landed)) else None
            v, o = grade_case_body(c)
            xs.grade(f"36_{lab}_body", v, o, "the record's body off K.body.create")
            v, o = grade_case_traits(c)
            xs.grade(f"36_{lab}_traits", v, o, "a rung, the weight, the level, a band or weight trait off, or a strip held")
            v, o = grade_case_xp(c)
            xs.grade(f"36_{lab}_xp", v, o, "levelDue held, no re-pin, or the XP off pinXp after the first minute")
            v, o = grade_case_strips(c, cr)
            xs.grade(f"36_{lab}_strips", v, o, "the logged strips differ from ruling 13-16's cost order")
            v, o = grade_case_hunger(c, at)
            xs.grade(f"36_{lab}_hunger", v, o, "the start energy state off K.deficit.state(0, fatDep) or its rung")
        S = self.D.get("S") or {}
        v, o = grade_names(S.get("labels"), S.get("want_names"))
        xs.grade("36_names", v, o, "a label off the staged display names")
        v, o = grade_refeed(self.D.get("E1"))
        xs.grade(f"36_{REFEED_CASE}_refeed", v, o, "after the first close the refeeding risk not 2 or the PE grade not 4")


# ---------------------------------------------------------------- the live run
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


def keep_server_log(log_path, run_dir, copied):
    """Name the server log for the artifact copy: it already sits in the run folder as server-stdout.log (pzt.session
    writes it there), so it is named, never copied onto itself; a log elsewhere is copied in."""
    dst = os.path.join(run_dir, "server-stdout.log")
    if os.path.abspath(log_path) != os.path.abspath(dst):
        shutil.copyfile(log_path, dst)
    copied.append("server-stdout.log")


def main(task, profile_name, prefix, artifact, session_text, pred, budget_s, driver_file, user="admin", cli="client"):
    from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
    from pzt import fixture as fx, profile                          # noqa: E402
    from pzt.bus import resolve_side                                # noqa: E402
    from pzt.harness import lint_paths                              # noqa: E402
    from pzt.paths import new_run_dir                               # noqa: E402
    from pzt.session import Timeline, attach_clients, make_server, teardown, verify   # noqa: E402

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
    phases = {"35": S.t35_body, "36": S.t36_body}[task]
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
                    keep_server_log(server.log_path, run_dir, xs.copied)
                except OSError as e:
                    L["log_copy_error"] = f"{type(e).__name__}: {e}"
            for c in every:
                lines, _ = X.grep_noecho(c.console, LOG_RX, 80, ECHO_RX, NEVER_RX)
                L.setdefault("clients", {})[getattr(c, "username", "?")] = lines

        def grade_all():
            if task == "35":
                S.t35_grade()
            else:
                S.t36_grade((out.get("logs") or {}).get("creation") or [])
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
