r"""The replay of a live run (Plan 11f Task 2): a run's minute ring and event log stepped through the mod's real
kernels and server adapters on the lupa host, minute by minute, at the live clock.

The live run's minute ring (harness H2, `minute.ring <user> start|read|stop`, Plan 11f Task 1) writes pages
`pzt-results/minute-ring-<user>-<from>.json`, each a JSON document whose `rows_list` holds rows
{s, ev, drained, age, dtM, hour, min, on, HUNGER, THIRST, FATIGUE, BOREDOM, UNHAPPINESS, NICOTINE_WITHDRAWAL,
[norec], <paths...>}. A row is taken INSIDE the EveryOneMinute event, before the mod's queue drains that minute, so
row k reads the state drain k - 1 left. The replay models that phase: it steps one drain per ring row at the row's
own world age (so the live dtM, the gap between rows, is the replay's), and the replay row emitted after drain k is
compared with ring row k + 1, labelled with that row's `s`.

Two backends share one event engine:

- `server` (`ServerReplay`): server_host.Host (testing/tests/kernel/server_host.py) with the golden trace's stand-ins
  (golden_trace.ENV: a decorated player whose stats object answers get, set and add, a thermoregulator, traits,
  getSandboxOptions at StatsDecrease 1) and a replay clock. Each minute fires EveryOneMinute and ticks the mod's own
  queue (NR_Server_Players) until it drains, so the whole pipeline runs in its ORDER (or a named subset). Eats go
  through the intake adapter: a TKX_StudyFoods item (or any item spec) through IN.readAfterAndLand on a
  before-snapshot, so the declared-nutrients chain, the landing, the stomach, the meal pool M (fed at the landing, cleared by Kinetics) and monotony are the mod's; a raw vector
  through IN.land and IN.atEat; a drink through IN.fluidVector and IN.land's liquid lane. The start record is placed
  in the store's records table and loaded by the store's own first-sight load (K.store.load: the inputs kept, the
  derived fields rebuilt), as after a restart.
- `oracle` (`OracleReplay`): the satiety oracles' own kernel composition, one minute a step
  (test_satiety_meal_studies.py's REPLAY, ENERGY_REPLAY and SIX_LIVE_REPLAY: the stomach and the meal pool M, the 70 kg man's
  trailing-24 h energy path, the hunger function), driven by the same event lists. It exists so the event engine
  can be checked against the oracles' pins where they step kernels directly, and so a live run's distance from the
  oracle's 70 kg man can be named (ruling 11f-4).

Events are a JSON list. Each is due at `age` (game hours: applied before the first drain at or after it, at that
age), at `s` (applied before the drain of ring row s, at its age: the landing a ring path such as
`_G.NutritionRevamp.server.intake.stats.eats` first shows), or at `minute` m of a synthetic clock (applied before
step m, at its start). Kinds:
  eat      {food | fullType+cal+carb+lip+pro+hunger+declared+foodType, frac (default 1)} or {vec, lane, fullType}:
           an eat's kcal comes from the item (its script values, or the vector given) and its fraction from the item
           (the driver's before/after read) or from lastIntake.frac, never from satiety.M; the replay derives
           nothing from M
  drink    {fluid, litres} or {vec}: the liquid lane. With a day length (--day-length) a drink flagged whole
           (whole true, {fluid, litres}; maxTime its raw action length where vanilla sets no default, eatType,
           unhappy, drunk and timeMod as drink_units reads them) lands sip by sip over its action's span, as the
           game drinks it (spread_drinks); an unflagged drink, a live ring's per-sip log, lands as logged
  autodrop {g}: g grams of water added to the record's fluids.autoDrop before the drain, which the mod's own Nutrients
           step lands after Kinetics (the writer's sip; a `drink` event would land it one drain early, F-T9-4). The row
           before it is `between`, as for any event: the live ring row already shows the autoDrop the replay's lacks
  meal     {size: "maint" | "request" | kcal, comp: {p, c, f}, food, plate, sate}: an energy-oracle meal (plate, a list
           of the mod's table fullTypes, makes it those foods' whole vector sized to the kcal; server backend); "request" eats
           650 kcal x min(hungerCap, hungerTarget(0.75, es) x circadian(hour)) / 0.25 (the oracles' intake mapping,
           ruling 11c-31; research section 3.7 form 1), es the state the last drain left and hour the event's
  sleep    {asleep}
  activity {rate | raw, moving, exercising, cold}: rate is the engine MET before the stand-in's load factor, raw
           the engine's raw rate the thermoregulator answers as is (a ring row's `rate`; null hands back to rate),
           the flags, and cold the thermoregulator's getEnergyMultiplier (null hands back to 1)
  stat     {stat, value}: the stand-in's stat
  setpath  {path, value}: a record path (lua.read grammar)
  trait    {trait, on}
Mode "live" uses the ring's clock and feeds the stand-in's NICOTINE_WITHDRAWAL from each ring row before its drain
(the engine owns that stat and the writer reads it; ALLOWED_FEED is the whole list, and a graded or tolerance field is
refused as a feed); mode "arm" substitutes another event list (ruling 11f-3), on the ring's clock or a synthetic one,
and feeds nothing the arm does not name. The replay never reads a ring row's outputs (HUNGER, the record paths, the
other stats): the stand-in's stats start at --start-stats or its defaults.

The activity of a live replay (Plan 11f C-17, ruling C17-1): the engine's raw metabolic rate and the server's exercise
flag are exogenous inputs, and the mod's bill (body.met) a graded output. When the ring's rows carry the harness's
`rate` and `exe` fields (3daaca9), mode live takes the activity from them (ring_activity_events: an activity event
{s, raw, exercising} before each row's drain where either changed), and an activity event in the log that names rate,
raw or exercising is refused; --ring-activity off keeps the log's own. The row is sampled inside EveryOneMinute and the
drain reads the rate a few ticks later, so the input carries that sub-minute skew; the ring has no moving flag, so the
stand-in stays still unless the log moves it, and its load factor is the stand-in's (--player inv, maxW).

The cold multiplier of a live replay (Plan 16 Task 7, #3947): the thermoregulator's getEnergyMultiplier drives the
cold diuresis (K.fluids.COLD_DIURESIS_LH x (coldMult - 1)) and the energy bill's cold term, and the stand-in answers 1.
When the ring's rows carry the harness's `cold` field (106dafa1) or a `body.coldMult` path (x456, x457), mode live
feeds it as an exogenous input (ring_cold_events: the mod stamps it in drain k and row k + 1 reads that stamp, so the
event before drain k carries row k + 1's value); --ring-cold off answers 1, as a ring without it does.

The overlays (REPLAY_ONLY, "replay.NAME" constants): a ring recorded before a later rule change replays on its own
pipeline through a named replay-only overlay of the lost rule, set on the replay's host and never shipped or used by
the guide (CLAUDE.md section 5): DEFICIT_FLOOR (Plan 11g Task 7), HUNGER_CURVE_OFF (Plan 15 Task 6), SEED_PLATE_OFF
(Task 13 fix 1), LIQUID_SOLID_KCAL (Task 14b), RETURN_CATCHUP_H (Plan 16 Task 2), WORLD_CLOCK (Task 4) and FAT_CEILING
(Task 5), composed by build in PRE_SPLIT, PRE_FREEZE, PRE_LIQUID, PRE_PLATE and PRE_CURVE.

The ring's own bookkeeping marks each compared row (link_marks): a jump in s or ev, or a dtM above 2.05 (the server's
tick granularity alternates dtM 0.8 and 1.6 at speed 5 and 0.94-1.11 at speed 1; ruling S0-1), is a gap (the replay
still steps the real age delta; graded, its findings marked gap); a drained count that did not advance between two rows
makes the later one suspect (the drain had not finished; not graded); a row with on false is offline: that minute is
not drained (it fires with the user away) and the reconnect is the mod's own, whose resume integrates OFFLINE_CAP_M,
0 game minutes, of the offline span (Plan 16 Task 2: the store's K.resume). A row with on true and norec is the first
sight, not offline: the mod loads the record in that minute's queue slot and drains it (NR_Server_Players.lua
P.firstSight, then the writer), so the replay drains it (ruling S0-3). The diff counts each class.

The start record's read age (--start-read-age, or a top-level readAge in the start document): events at or before it
are dropped, because the record already holds them. The driver contract: the driver logs the start record's read age,
or reads the start record with no eat since the last drain.

    python tools/replay_live.py live --ring PAGE.json [PAGE.json ...] --events EV.json --start START.json
                                     --sleep-allowed true|false [--detect-autodrink]
                                     [--ring-activity auto|on|off] [--ring-cold auto|on|off]
                                     [--day-length N [--speed X]]
                                     [--start-read-age A] [--start-stats STATS.json]
                                     [--user admin] [--player CFG.json] [--out OUT.json]
    python tools/replay_live.py arm  --events EV.json [--start START.json] (--ring PAGE.json ... |
                                     --minutes N [--start-age A]) [--backend server|oracle]
                                     [--day-length N [--speed X]] [--out OUT.json]

The start record is a slot file's JSON ({gen, rec, done}), the record itself, or an H1 `lua.read` reply
({values: {path: value}}). Every server row carries `health`, the stand-in's overall health (its start 100, or the player
config's `health`, less what the mod's drain took through ReduceGeneralHealth plus what AddGeneralHealth gave back; with
`game_heal` the add rises by the game's spread, 5.05 / 17 of the argument with every part below 100, #3898, as the
mod's heal assumes; without it, in full). Output: {rows, diff, eats, offset, mode, injected, spread}; the diff grades HUNGER within
0.002, es (body.energyState) within 0.005 and satiety.L within 0.5 % (the plan's pre-registered tolerances) and skips every
row an event landed before (vanilla's own eat moves HUNGER between writes), every suspect row and every offline row.
A tolerance field compared on no row is a finding. Exits 1 when the diff has a finding.
"""
import argparse
import json
import math
import os
import struct
import sys

import dials

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
KERNEL_TESTS = os.path.join(REPO, "testing", "tests", "kernel")
STUDY_SCRIPT = os.path.join(REPO, "testing", "experiments", "TKX_StudyFoods", "common", "media", "scripts",
                            "tkx_study_foods.txt")

STATS = ("HUNGER", "THIRST", "FATIGUE", "BOREDOM", "UNHAPPINESS", "NICOTINE_WITHDRAWAL")
# The symptoms' rows (Plan 18 Task 3): the stand-in's ENDURANCE and STRESS (read into a row only, never fed or started
# from a ring), the record's symptom outputs and the added pain per part (K.effects.symptoms): `effects.pain.<i>` for
# each part index i with a target above 0, and `painTarget`, vanilla's PAIN target those parts make (the sum of added
# pain x the part's modifier, #2362; the wound terms excluded), right after the minute's write.
# The stand-in models no vanilla endurance regeneration and no stress decay (golden_trace's plain stat store): ENDURANCE
# holds the writer's last pull-down and STRESS its last rise, so a grade of the cap easing or a floor releasing reads
# effects.enduranceCap and effects.stressFloor, never these two rows (Plan 18 Task 3 review F3).
SYMPTOM_STATS = ("ENDURANCE", "STRESS")
SYMPTOM_FIELDS = ("enduranceCap", "symCap", "stressFloor", "unhappyFloor")
H_REQ = 0.25                          # the meal request, vanilla's HUNGRY level 2 (ruling 11c-17)
# The satiety model's own hunger (Plan 15 Task 6): every row carries it under this key, the server backend's from
# record.satiety.hModel (the writer's h_model, before the calibrated curve), the oracle backend's its composition. A
# study oracle reads it, never the written HUNGER, which is the curve of it (K.hungerCurve).
H_MODEL = "satiety.hModel"
KCAL_PER_H = 650.0 / H_REQ            # the intake mapping (ruling 11c-31): kcal per unit of written hunger
NEUTRAL_HOUR = 13.8333                # = satiety.CIRCADIAN_PEAK_H - 6, where circadian() is 1.0 exactly (test_replay_live_oracle.py:75 guards it)
# The feed: the stats the replay copies from each ring row into the stand-in before its drain. Only an exogenous input
# may be fed: a stat the engine moves and the mod reads but never writes. NICOTINE_WITHDRAWAL is the one such stat
# (NR_Server_Writer reads it at :442; every other stat it reads it also writes, :287-302). A graded or tolerance field
# fed from the ring would grade the ring against itself, so those names are refused by name.
ALLOWED_FEED = ("NICOTINE_WITHDRAWAL",)
GRADED_FEED = ("HUNGER", "M", "S", "L", "es", "satiety.M", "satiety.S", "satiety.L", "body.energyState", "FATIGUE",
               "THIRST", "BOREDOM", "UNHAPPINESS")
DEFAULT_FEED = ALLOWED_FEED
GAP_DTM = 2.05                        # a ring row whose dtM exceeds this is a long minute: marked gap (ruling S0-1:
                                      # tick quantization puts normal rows at 0.8-1.6, so 1.05 marked them)
OFFLINE_CAP_M = 0                     # the game minutes of an offline span the mod integrates at the reconnect: none
                                      # since Plan 16 Task 2 (the store's resume, K.resume), 60 until then
DEFAULT_TOL = {"HUNGER": ("abs", 0.002), "body.energyState": ("abs", 0.005), "satiety.L": ("rel", 0.005)}
MIXED = {"p": 0.15, "c": 0.50, "f": 0.35}
MAX_TICKS = 64


def _lua():
    if KERNEL_TESTS not in sys.path:
        sys.path.insert(0, KERNEL_TESTS)
    import lupa.lua51 as lua51
    import server_host
    import golden_trace
    return lua51, server_host, golden_trace


def float32(x):
    return struct.unpack("f", struct.pack("f", float(x)))[0]


# --- the paths (harness H1's grammar) -------------------------------------------------------------------------------

def parse_path(path):
    """H1's grammar: segments joined by `.`, `[...]` one literal string key. Returns (segments, global) where each
    segment is (bracketed, text). Raises ValueError on a bad path."""
    glob = False
    if path.startswith("_G."):
        glob = True
        path = path[3:]
    segs = []
    i, n = 0, len(path)
    if n == 0:
        raise ValueError("empty path")
    while i < n:
        if path[i] == "[":
            j = path.find("]", i)
            if j < 0:
                raise ValueError("unclosed [")
            segs.append((True, path[i + 1:j]))
            i = j + 1
        else:
            j = path.find(".", i)
            if j < 0:
                j = n
            if j == i:
                raise ValueError("empty segment")
            segs.append((False, path[i:j]))
            i = j
        if i < n:
            if path[i] != ".":
                raise ValueError("a bracket must end a segment")
            i += 1
            if i == n:
                raise ValueError("trailing .")
    return segs, glob


def _number(text):
    try:
        x = float(text)
    except ValueError:
        return None
    return int(x) if x == int(x) else x


def walk(lua51, root, segs):
    """(True, value) or (False, None): a plain segment tries the string key, then the number."""
    node = root
    for bracketed, text in segs:
        if node is None or lua51.lua_type(node) != "table":
            return False, None
        v = node[text]
        if v is None and not bracketed:
            num = _number(text)
            if num is not None:
                v = node[num]
        node = v
    return node is not None, node


def to_py(lua51, v):
    t = lua51.lua_type(v)
    if t == "table":
        keys = list(v.keys())
        if keys and all(isinstance(k, (int, float)) for k in keys):
            ks = sorted(keys)
            if ks == list(range(1, len(ks) + 1)):
                return [to_py(lua51, v[k]) for k in ks]
        return {(k if isinstance(k, str) else str(k)): to_py(lua51, x) for k, x in v.items()}
    if isinstance(v, bytes):
        return v.decode("utf-8")
    return v


# --- the study foods (TKX_StudyFoods' item script) ----------------------------------------------------------------

def study_foods(path=STUDY_SCRIPT):
    """{fullType: spec} for every item of a module's script: the four macros as the live getters read them (float32),
    the instance hunger (script points / 100), the declared NR_Nutrients string, FoodType and the mood changes."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    while "/*" in text:
        a = text.index("/*")
        b = text.index("*/", a)
        text = text[:a] + text[b + 2:]
    module = None
    out = {}
    cur = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("module "):
            module = line.split()[1]
        elif line.startswith("item "):
            cur = {"name": line.split()[1], "props": {}}
        elif cur is not None and line == "}":
            p = cur["props"]
            full = "%s.%s" % (module, cur["name"])
            out[full] = {
                "fullType": full,
                "cal": float32(p.get("Calories", 0)), "carb": float32(p.get("Carbohydrates", 0)),
                "lip": float32(p.get("Lipids", 0)), "pro": float32(p.get("Proteins", 0)),
                "hunger": float32(p.get("HungerChange", 0)) / 100.0,
                "declared": p.get("NR_Nutrients"), "foodType": p.get("FoodType"),
                "boredom": float(p.get("BoredomChange", 0)), "unhappy": float(p.get("UnhappyChange", 0)),
                "stress": float(p.get("StressChange", 0)), "thirst": float(p.get("ThirstChange", 0)),
            }
            cur = None
        elif cur is not None and "=" in line:
            k, v = line.split("=", 1)
            cur["props"][k.strip()] = v.strip().rstrip(",").strip()
    return out


def declared_vector(spec):
    """The whole item's vector the declared chain lands (K.vector.resolve): the macros the item's own, the rest the
    NR_Nutrients string's."""
    v = {"calories": spec["cal"], "carbs": spec["carb"], "lipids": spec["lip"], "proteins": spec["pro"]}
    for pair in (spec.get("declared") or "").split(";"):
        if ":" in pair:
            k, x = pair.split(":", 1)
            v[k.strip()] = float(x)
    return v


# --- the ring ---------------------------------------------------------------------------------------------------

def load_ring(pages):
    """Rows from one or more ring pages (paths or parsed documents), merged by `s` and sorted; and the paths."""
    rows, paths = {}, []
    for page in pages:
        doc = page
        if isinstance(page, str):
            with open(page, encoding="utf-8") as fh:
                doc = json.load(fh)
        for p in doc.get("paths") or []:
            if p not in paths:
                paths.append(p)
        for r in doc.get("rows_list") or []:
            rows[r["s"]] = r
    return [rows[s] for s in sorted(rows)], paths


def estimate_offset(rows):
    """The clock's hour of day at world age 0, from the rows' hour and minute (getMinutes floors): the offset lies in
    [max x, min x + 1/60) for x = hour + min / 60 - age, mod 24. A whole hour inside the range wins (world age 0 is
    07:00 on the default fixture, #2890), else the range's low end."""
    xs = []
    for r in rows:
        if r.get("age") is None or r.get("hour") is None or r.get("min") is None:
            continue
        xs.append((r["hour"] + r["min"] / 60.0 - r["age"]) % 24.0)
    if not xs:
        return 0.0
    ref = xs[0]
    xs = [ref + ((x - ref + 12.0) % 24.0) - 12.0 for x in xs]
    lo, hi = max(xs), min(xs) + 1.0 / 60
    whole = math.ceil(lo - 1e-9)
    if whole < hi:
        return float(whole % 24)
    return lo % 24.0


# --- the start record ---------------------------------------------------------------------------------------------

def nest(values):
    """An H1 reply's {path: value} as a nested record; a numeric segment is a number key."""
    rec = {}
    for path, v in values.items():
        segs, _ = parse_path(path)
        node = rec
        for i, (br, text) in enumerate(segs):
            key = text if br or _number(text) is None else _number(text)
            if i == len(segs) - 1:
                node[key] = v
            else:
                node = node.setdefault(key, {})
    return rec


# --- the Lua glue ---------------------------------------------------------------------------------------------------

REPLAY_ENV = r"""
NR_R = { u = {}, holdHour = nil, offset = 0 }
-- the thirst traits the golden stand-in's CharacterTrait lacks (NR_Server_Nutrients.lua basalScale reads them), so a
-- trait event can set them; a stand-in holds neither unless an event or its cfg adds it
CharacterTrait.HIGH_THIRST = CharacterTrait.HIGH_THIRST or "trait:HIGH_THIRST"
CharacterTrait.LOW_THIRST = CharacterTrait.LOW_THIRST or "trait:LOW_THIRST"
function NR_R.tod(age)
    if NR_R.holdHour ~= nil then return NR_R.holdHour end
    local t = math.fmod(age + NR_R.offset, 24)
    if t < 0 then t = t + 24 end
    return t
end
getGameTime = function()
    local tod = NR_R.tod(NR_T.age)
    return { getWorldAgeHours = function(s) return NR_T.age end,
             getTimeOfDay = function(s) return tod end,
             getHour = function(s) return math.floor(tod) end,
             getMinutes = function(s) return math.floor((tod - math.floor(tod)) * 60) end }
end
-- the replay's own control of a decorated stand-in: asleep, moving, a Fitness exercise, the engine MET (rate, before
-- the load factor; raw, when set, the rate answered as is: a ring row's raw engine rate) and the thermoregulator's
-- cold multiplier (cold, when set, getEnergyMultiplier's answer: a ring row's cold; 1 otherwise, the golden stand-in's)
function NR_R.adopt(p, name, rate, inv, maxW)
    local u = { asleep = false, rate = rate, moving = false, exercising = false, raw = nil, cold = nil }
    NR_R.u[name] = u
    p.isAsleep = function(s) return u.asleep end
    p.isPlayerMoving = function(s) return u.moving end
    local fitness = { getCurrentExe = function(s) if u.exercising then return "exercise" end return nil end }
    p.getFitness = function(s) return fitness end
    local th = p:getBodyDamage():getThermoregulator()
    local f = math.min(math.max(inv / maxW, 0), 1)
    th.getMetabolicRate = function(s)
        if u.raw ~= nil then return u.raw end
        return u.rate * (1 + 0.35 * f * f)
    end
    th.getEnergyMultiplier = function(s)
        if u.cold ~= nil then return u.cold end
        return 1.0
    end
    return u
end
function NR_R.record(user)
    local NR = NutritionRevamp
    local rec = NR.server.store.get(user, NR.worldAge())
    rec.stomach = rec.stomach or NR.kernel.stomach.new()
    rec.pool = rec.pool or NR.kernel.vector.new()
    return rec
end
-- an item eaten through the intake adapter: a fresh instance's before-snapshot (IN.readBefore's shape), its raw
-- hunger after the eat, IN.readAfterAndLand (the chain, the landing guard, IN.land, monotony, lastIntake)
function NR_R.eatItem(user, spec)
    local IN = NutritionRevamp.server.intake
    local rawAfter = spec.instBase * (1 - spec.frac)
    local item = {}
    item.getHungChange = function(s) return rawAfter end
    item.getThirstChangeUnmodified = function(s) return 0 end
    local b = { item = item, username = user, rawBefore = spec.instBase, fullType = spec.fullType,
                instBase = spec.instBase, thirstBefore = 0, cal = spec.cal, carb = spec.carb, lip = spec.lip,
                pro = spec.pro, cooked = false, burnt = false, rotten = false, frozen = false,
                scriptHunger = spec.instBase, scriptThirst = 0, extraTypes = {}, craftMap = nil,
                declared = spec.declared, foodType = spec.foodType, char = NR_T.chars[user] }
    b.macros = { calories = b.cal, carbs = b.carb, lipids = b.lip, proteins = b.pro }
    NR_R.record(user)
    return IN.readAfterAndLand(b)
end
-- a vector landed as the intake lands one (IN.land), monotony booked for a food lane's type (IN.atEat); a food lane's
-- type also brings its plate volume (IN.volumeOf, Plan 15 Task 7), as the server's eat does
function NR_R.landVec(user, src, lane, fullType, foodType)
    local NR = NutritionRevamp
    local K = NR.kernel
    local rec = NR_R.record(user)
    local v = K.vector.new()
    for k, x in pairs(src) do v[k] = x end
    local ml = nil
    if lane ~= "liquid" and fullType ~= nil then ml = NR.server.intake.volumeOf(fullType) end
    NR.server.intake.land(rec, user, v, lane, ml)
    if lane ~= "liquid" and fullType ~= nil then
        NR.server.intake.atEat(rec, { fullType = fullType, foodType = foodType, char = NR_T.chars[user],
                                      username = user }, v.calories)
    end
    return v
end
function NR_R.drink(user, fluid, litres)
    local NR = NutritionRevamp
    local vec = NR.server.intake.fluidVector(NR.data.fluids.get, { { fluid, 1 } }, litres)
    return NR_R.landVec(user, vec, "liquid", nil, nil)
end
-- a meal vector of the energy oracles: macros only, kcal split by energy shares (Atwater 4/4/9)
function NR_R.mealVec(kcal, p, c, f)
    local v = NutritionRevamp.kernel.vector.new()
    v.calories = kcal
    v.proteins = kcal * p / 4
    v.carbs = kcal * c / 4
    v.lipids = kcal * f / 9
    return v
end
function NR_R.requestKcal(es, hod, H_REQ, KCAL_PER_H)
    local K = NutritionRevamp.kernel
    return KCAL_PER_H * K.min(K.hybrid.HUNGRY_4 - K.hybrid.CAP_MARGIN, K.deficit.hungerTarget(1 - H_REQ, es) * K.satiety.circadian(hod))
end
function NR_R.maint(body)
    local K = NutritionRevamp.kernel
    local w0 = body.fm + body.lm
    return K.energy.ree(body.lm) + (K.energy.COMPENDIUM.Default - K.energy.MET_REST) * w0 / 60 * 960
end
function NR_R.drained()
    local P = NutritionRevamp.server.players
    return P.queueHead > #P.queue
end
"""

# The study participant at first sight (Plan 13 Task 12): the mod builds the body from the band traits held, never a
# weight, so the replay wraps MET.ensureBody to lay a weight the caller passes explicitly (player={"weight": w}) as a
# participant's body (testing/tests/kernel/participant.py), at the player's sex and the mod's effective-sex option, and
# stamps levelDue as the mod's own first sight does. A user with no explicit weight takes the mod's own first sight,
# so a live replay reproduces the mod (Task 12 fix round 1); the stand-in's vanilla weight stays 80 kg by default.
PARTICIPANT_SIGHT = r"""
NR_R.weights = {}
local MET = NutritionRevamp.server.metabolism
local ensure = MET.ensureBody
MET.ensureBody = function(username, player, record, ageH)
    local w = NR_R.weights[username]
    if record.body ~= nil or w == nil then return ensure(username, player, record, ageH) end
    local sex = 1
    if player.isFemale ~= nil and player:isFemale() then sex = 2 end
    local opts = NutritionRevamp.server.options
    record.body = NR_participant(w, sex, ageH, opts ~= nil and opts.sexSpecific == true)
    record.body.levelDue = true
    MET.stats.creates = MET.stats.creates + 1
    return record.body
end
"""

ORACLE_LUA = r"""
NR_O = {}
function NR_O.new(M0, energy, satiety, holdEs, holdHour)
    local K = NutritionRevamp.kernel
    local o = { M = M0, es = 1, L = 0, eb24 = 0, hunger = nil, energy = energy, satiety = satiety, holdEs = holdEs,
                holdHour = holdHour, asleep = false, trait = 1 }
    o.st = K.stomach.new()
    o.body = NR_participant(70, 1, 0)               -- the energy oracles' 70 kg man (participant.py)
    local w0 = o.body.fm + o.body.lm
    o.maint = K.energy.ree(o.body.lm) + (K.energy.COMPENDIUM.Default - K.energy.MET_REST) * w0 / 60 * 960
    o.rec = { satiety = {}, body = o.body, stomach = o.st }
    return o
end
function NR_O.tod(o, ageH)
    if o.holdHour then return nil end
    return ageH % 24
end
function NR_O.mealVec(kcal, p, c, f)
    local v = NutritionRevamp.kernel.vector.new()
    v.calories = kcal
    v.proteins = kcal * p / 4
    v.carbs = kcal * c / 4
    v.lipids = kcal * f / 9
    return v
end
function NR_O.trail(o, ageH)
    if o.energy then NutritionRevamp.kernel.body.trailTo(o.body.trail, ageH) end
end
function NR_O.eat(o, src, lane, sate)
    local K = NutritionRevamp.kernel
    if o.energy then
        local v = K.vector.new()
        for k, x in pairs(src) do v[k] = x end
        K.energy.intake(o.body, v, 1)
    end
    if o.satiety and sate then
        local u = K.vector.new()
        for k, x in pairs(src) do u[k] = x end
        if lane == "liquid" then K.stomach.ingestLiquid(o.st, u) else K.stomach.ingest(o.st, u) end
        o.M = K.satiety.mealFeed(o.M, u)                 -- IN.feed's: M fed in full at the eat
    end
end
function NR_O.requestKcal(o, ageStart, H_REQ, KCAL_PER_H)
    local K = NutritionRevamp.kernel
    local c = 1
    local hod = NR_O.tod(o, ageStart)
    if hod ~= nil then c = K.satiety.circadian(hod) end
    return KCAL_PER_H * K.min(K.hybrid.HUNGRY_4 - K.hybrid.CAP_MARGIN, K.deficit.hungerTarget(1 - H_REQ, o.es) * c)
end
function NR_O.minute(o, ageH, dtM)
    local K = NutritionRevamp.kernel
    if o.energy then
        local body = o.body
        local met = K.energy.COMPENDIUM.Default
        if o.asleep then met = K.energy.COMPENDIUM.Sleeping end
        local ex0 = body.exKcalDay
        K.energy.minute(body, met, true, 1, dtM)
        o.L = K.deficit.exerciseLag(o.L, body.exKcalDay - ex0, dtM / 60)
        if o.daySeeded == nil then body.dayStartH = math.floor(ageH / 24) * 24; o.daySeeded = true end   -- the ring's first age
        if K.body.calendar(body, ageH) == 1 then             -- the mod's record calendar (Plan 16 Task 2: 24 online hours)
            K.drain.closeDay(body)                          -- the mod's day close (NR_Server_Metabolism)
            K.partition.closeDay(body)
        end
        local ee24 = K.max(K.body.trail24(body.trail, "ee"), K.energy.ree(body.lm))
        local ex24 = K.body.trail24(body.trail, "ex")
        o.eb24 = K.energy.eb24h(body)
        o.es = K.deficit.activityState(o.eb24, ex24, o.L, 0, ee24)
    end
    if o.satiety then
        K.satiety.drain(o.st, K.min(dtM, K.resume.STEP_M), o)   -- one-minute substeps, each clearing o.M, a step capped at the pipeline's bound
        local F = K.satiety.fullness(o.st)
        local x = o.es
        if o.holdEs then x = 1 end
        local c = 1
        local hod = NR_O.tod(o, ageH)
        if hod ~= nil then c = K.satiety.circadian(hod) end
        o.hunger = K.min(K.hybrid.HUNGRY_4 - K.hybrid.CAP_MARGIN, K.satiety.target(F, o.M, x) * c)
    end
    o.rec.satiety.M = o.M
    o.rec.satiety.L = o.L
    o.rec.es = o.es
    o.rec.eb24 = o.eb24
end
"""


def _due(ev, k, prev, age, seq):
    if "minute" in ev:
        return ev["minute"] == k
    if "s" in ev:
        return seq is not None and ev["s"] == seq
    a = ev["age"]
    return (prev is None or a > prev + 1e-12) and a <= age + 1e-12


def _event_age(ev, prev, age):
    if "age" in ev:
        return ev["age"]
    if "minute" in ev:
        return prev if prev is not None else age
    return age


class _Backend:
    """The event engine's half both backends share: the eat log and the request and maint meals."""

    def __init__(self):
        self.eats = []

    def apply(self, ev, at):
        kind = ev["kind"]
        fn = getattr(self, "ev_" + kind, None)
        if fn is None:
            raise ValueError("unknown event kind %r" % kind)
        fn(ev, at)

    def meal_kcal(self, ev, at):
        size = ev.get("size", "maint")
        if size == "maint":
            return self.maint() / 3.0
        if size == "request":
            return self.request_kcal(at)
        return float(size)


# The deficit drive the Plan 11f live rings were recorded under (x260b at 9fbc0ca, x263 at 77fcca7, x332 at 6a6cdb61:
# Plan 11f Task 2c fix 2's constants, before Plan 11g Task 7's refit): a ring replays at its recording build's constants
# (`constants`), so its energy state is graded against the pipeline that produced it, not against a later fit. Those
# builds added a deficit floor, 0.02 x max(0, es - 1), to the hunger target, which the shipped kernel lost in Plan 11g
# Task 7 fix 1 (ruling T7-1): "replay.DEFICIT_FLOOR" is a replay-only constant (REPLAY_ONLY) that restores the
# recording build's K.deficit.hungerTarget and K.deficit.unsated on that replay's host, so the rings' HUNGER readings
# stay those of the pipeline that produced them. Those builds also read the fat store linearly, 0.5 x fatDep (ruling
# 14), which Plan 13 Task 10c replaced by the low-fat ramp FAT_GAIN x clamp((fatDep - FAT_DEP_LO) / (FAT_DEP_HI -
# FAT_DEP_LO), 0, 1): the ramp at gain 0.5 from 0 to 1 is that linear term exactly, so the three fat constants restore it.
DEFICIT_11F = {"deficit.BALANCE_SPAN_KCAL": 3100.0, "replay.DEFICIT_FLOOR": 0.02, "deficit.EX_BYPASS_LO": 0.282,
               "deficit.EX_BYPASS_HI": 0.575, "deficit.FAT_GAIN": 0.5, "deficit.FAT_DEP_LO": 0.0,
               "deficit.FAT_DEP_HI": 1.0}

# The satiety and deficit constants the Plan 11g Task 8 live rings (x361 to x364) were recorded under (build 7093079b,
# the final model: Task 6c fix 2's meal-pool fit and Task 7's deficit refit). A ring replays at its recording build's
# constants, so a later refit never turns its fidelity test red; the snapshot is the recording build's and a later plan
# leaves it as it is (testing/tests/test_x36_gut_lib.py pins it equal to the shipped constants until a refit, by design).
GUT_11G = {"satiety.W_PROTEIN": 2.49782, "satiety.W_CARB": 1.0, "satiety.W_FAT": 0.878683, "satiety.W_NEUTRAL": 1.0,
           "satiety.MEAL_HALF_LIFE_H": 0.583749, "satiety.MEAL_REQ": 3.80654, "satiety.MEAL_STEEP": 0.0356875,
           "satiety.MEAL_SEED_MAX": 1180.0, "satiety.FULL_WEIGHT": 0.517741, "satiety.LIQUID_WEIGHT": 0.278815,
           "satiety.PROTEIN_FILL": 7.91676, "deficit.BALANCE_SPAN_KCAL": 3970.55, "deficit.EX_BYPASS_LO": 0.282,
           "deficit.EX_BYPASS_HI": 0.405}

# The recording build's hunger target and its inverse with the deficit floor F (NR_Kernel_Deficit.lua at 5af809b5,
# lines 96-104, the coefficient made a literal): set on a replay host only, never shipped.
_FLOOR_LUA = ("local K = NutritionRevamp.kernel\n"
              "K.deficit.hungerTarget = function(x, energyState) return K.clamp((1 - x) * energyState + %r * "
              "K.max(0, energyState - 1), 0, 1) end\n"
              "K.deficit.unsated = function(hunger, energyState) return (hunger - %r * K.max(0, energyState - 1)) / "
              "energyState end\n")


def _replay_floor(rt, value):
    rt.execute(_FLOOR_LUA % (float(value), float(value)))


# The writer before the calibrated hunger curve (Plan 15 Task 6): every live ring up to that build wrote the model's own
# value, capped, as HUNGER, so "replay.HUNGER_CURVE_OFF" (any true value) sets the curve, its inverse and its unfed dip to the
# identity on that replay's host and the ring's HUNGER is graded against the pipeline that produced it. Set on a replay
# host only, never shipped; the dead zone and the fasting hold go with the curve, and the starving minimum's onset
# (Plan 15 Task 5) was never reached by a recorded ring.
_CURVE_OFF_LUA = ("local K = NutritionRevamp.kernel\n"
                  "K.hungerCurve.write = function(h, state) return h end\n"
                  "K.hungerCurve.inverse = function(H) return H end\n"
                  "K.hungerCurve.dip = function(c) return 1 end\n")


def _replay_curve_off(rt, value):
    if value:
        rt.execute(_CURVE_OFF_LUA)


# The writer before the seed plate (Plan 15 Task 13 fix 1): a fresh record whose vanilla HUNGER was under the empty
# stomach's floor seeded its meal pool at the cap and landed no meal, so "replay.SEED_PLATE_OFF" (any true value) makes
# W.seedPlate land nothing on that replay's host and a ring recorded before the fix is graded against its own pipeline.
_SEED_PLATE_OFF_LUA = "NutritionRevamp.server.writer.seedPlate = function(h, record, inp, F) return F end"


def _replay_seed_plate_off(rt, value):
    if value:
        rt.execute(_SEED_PLATE_OFF_LUA)


# The reconnect before the offline freeze (Plan 16 Task 2): a return integrated min(gap, 60) game minutes as online time
# and skipped the rest, and re-stamped the open record day to the world day (ruling 13-5), so "replay.RETURN_CATCHUP_H"
# (game hours, 1 for those builds) makes the store's resume on that replay's host move every stamp by the gap less that
# catch-up and start the record day at the world day's start, and the return minute itself integrates the catch-up
# (the store never asks the players' minute to skip it), as a ring recorded before the freeze did at its reconnects.
# Set on a replay host only, never shipped.
_CATCHUP_LUA = ("local K = NutritionRevamp.kernel\n"
                "K.resume.resume = function(record, ageH)\n"
                "    local fromH = K.resume.fromH(record)\n"
                "    if not K.finite(ageH) or fromH == nil or not (ageH - fromH > %r) then return 0 end\n"
                "    local gapH = ageH - fromH - %r\n"
                "    K.resume.shift(record, gapH, fromH, ageH - %r)\n"
                "    if type(record.body) == 'table' then record.body.dayStartH = math.floor(ageH / 24) * 24 end\n"
                "    return gapH\n"
                "end\n"
                "NutritionRevamp.server.store.takeResumed = function(username) return false end\n")


def _replay_catchup(rt, value):
    v = float(value)
    rt.execute(_CATCHUP_LUA % (v, v, v))


# The daily rhythm before the body clock (Plan 16 Task 4): the hunger factor, the fatigue circ and the carry morning band
# read the world clock's hour whatever the sleep setting, so "replay.WORLD_CLOCK" (any true value) makes K.circadian.hour
# read the replay's world hour on that replay's host: a ring recorded before the body clock is graded against its own
# pipeline, and a study oracle that read the world hour runs as a sleep-on player whose body clock sits on the world hour:
# a writer-only replay has no Nutrients step to seed the body clock, and Karl's 05:00 and 06:00 wakes would reset it 1-2 h
# ahead of the world (a 23:00-07:00 night resets it onto the world hour). The sleep state itself still follows
# sleep_allowed. Set on a replay host only, never shipped.
_WORLD_CLOCK_LUA = ("NutritionRevamp.kernel.circadian.hour = function(record, sleepOn) "
                    "return NR_R.tod(NR_T.age) end\n")


def _replay_world_clock(rt, value):
    if value:
        rt.execute(_WORLD_CLOCK_LUA)


# The liquid lane before Plan 15 Task 14b (8a34a7de): its half-time grew with the solid lane's whole energy, a plate's
# included (K.stomach.liquidHalfMin(energy), 13 + 0.12 x the buffer's kcal), where it now grows with the drink-borne
# share only (stomach.liqKcal capped at the lane's energy). So "replay.LIQUID_SOLID_KCAL" (any true value) wraps
# K.stomach.drain on that replay's host to set the counter far above any lane's energy (finite, so Kinetics' guard keeps
# it) before each call: K.min(liqKcal, energy) is then the energy, the old rule exactly (the drain's only change since
# bcf99149, the last build that held the old rule, is that K.min and the counter's own update, which the next call's
# set overwrites; testing/tests/kernel/test_replay_live_fidelity.py proves it against bcf99149's own file). Set on a
# replay host only,
# never shipped, and never used by the guide (CLAUDE.md section 5, Plan 14 Task 4: an old run is drawn only where the HEAD
# replay matches); it exists so a ring recorded before that change is graded against its own pipeline.
_LIQUID_SOLID_KCAL_LUA = ("local K = NutritionRevamp.kernel\n"
                          "local drain = K.stomach.drain\n"
                          "K.stomach.drain = function(stomach, dtH)\n"
                          "    stomach.liqKcal = 1e18\n"
                          "    return drain(stomach, dtH)\n"
                          "end\n")


def _replay_liquid_solid_kcal(rt, value):
    if value:
        rt.execute(_LIQUID_SOLID_KCAL_LUA)


# The deficit arm before Plan 16 Task 5 (0a4baa8c, 648b4a83): fat paid a deficit up to Alpert's ceiling
# (K.partition.FAT_CEIL_KCAL x fm a day) and the overflow split by the protection prot, where it now splits the whole
# deficit by Forbes' share with no ceiling and the draw past fmMin is paid by lean. So "replay.FAT_CEILING" (any true
# value) sets K.partition.deficitLean on that replay's host to the function of 3a93d51c, the last build that held the
# old arm (NR_Kernel_Partition.lua lines 61-80, verbatim; proved against that file in test_replay_live_fidelity.py):
# Task 5's other change is a comment, so a ring recorded before it is graded against its own pipeline. Set on a replay
# host only, never shipped, never used by the guide.
_FAT_CEILING_LUA = ("local K = NutritionRevamp.kernel\n"
                    "K.partition.deficitLean = function(body, grow, S, p, E, P, ts)\n"
                    "    local RL = K.partition.RHO_LEAN\n"
                    "    local RF = K.partition.RHO_FAT\n"
                    "    local gP = K.clamp((p - P.pdef_lo) / (P.pdef_hi - P.pdef_lo), 0, 1)\n"
                    "    local prot = K.clamp(1 - P.wT * K.partition.training(S, P) - P.wP * gP, P.prot_floor, 1)\n"
                    "    local share = K.partition.forbes(body.fm, P) * prot\n"
                    "    local dW = -E / (share * RL + (1 - share) * RF)\n"
                    "    local leanLoss = share * dW\n"
                    "    local fatLoss = (1 - share) * dW\n"
                    "    local cap = K.partition.FAT_CEIL_KCAL * body.fm / RF\n"
                    "    if fatLoss > cap then\n"
                    "        local over = (fatLoss - cap) * RF\n"
                    "        fatLoss = cap + over * (1 - prot) / RF\n"
                    "        leanLoss = leanLoss + over * prot / RL\n"
                    "    end\n"
                    "    local fromX = K.min(body.lx, leanLoss)\n"
                    "    local dX = -fromX - (body.lx - fromX) / P.x_tau_d\n"
                    "    local dM = -fatLoss - grow / ts * RL / RF\n"
                    "    return -(leanLoss - fromX), dX, dM\n"
                    "end\n")


def _replay_fat_ceiling(rt, value):
    if value:
        rt.execute(_FAT_CEILING_LUA)


REPLAY_ONLY = {"replay.DEFICIT_FLOOR": _replay_floor, "replay.HUNGER_CURVE_OFF": _replay_curve_off,
               "replay.SEED_PLATE_OFF": _replay_seed_plate_off, "replay.RETURN_CATCHUP_H": _replay_catchup,
               "replay.WORLD_CLOCK": _replay_world_clock, "replay.LIQUID_SOLID_KCAL": _replay_liquid_solid_kcal,
               "replay.FAT_CEILING": _replay_fat_ceiling}
# The world-clock rhythm, for a ring recorded before Plan 16 Task 4, and for a study oracle that reads the world hour.
WORLD_CLOCK = {"replay.WORLD_CLOCK": 1}
# The deficit arm before Forbes' split, for a ring recorded before Plan 16 Task 5 (never a study oracle's: those test the
# shipped arm).
PRE_SPLIT = {"replay.FAT_CEILING": 1}
# The reconnect before the offline freeze, for a ring recorded before Plan 16 Task 2 (so before the body clock and the
# deficit split too).
PRE_FREEZE = dict({"replay.RETURN_CATCHUP_H": 1.0}, **dict(WORLD_CLOCK, **PRE_SPLIT))
# The liquid lane slowed by the solid lane's whole kcal, for a ring recorded before Plan 15 Task 14b (8a34a7de: x452-x457
# and x453b, a97fec05, and every earlier ring), so before the freeze too.
PRE_LIQUID = dict({"replay.LIQUID_SOLID_KCAL": 1}, **PRE_FREEZE)
# The writer before the seed plate, for a ring recorded before Plan 15 Task 13 fix 1 (x452-x457 and x453b, a97fec05),
# so before the liquid lane's change and the freeze too.
PRE_PLATE = dict({"replay.SEED_PLATE_OFF": 1}, **PRE_LIQUID)
# The pre-curve writer, for a ring recorded before Plan 15 Task 6 (so before the seed plate too): merged into the ring's
# own constants.
PRE_CURVE = dict({"replay.HUNGER_CURVE_OFF": 1}, **PRE_PLATE)


def set_constants(K, constants, rt=None):
    """Set each {"table.NAME": value} on the kernel table K; refuses a name the kernel does not hold as a number. A
    REPLAY_ONLY name ("replay.NAME") runs its setter on the runtime rt instead (a recording build's code the kernel has
    since lost)."""
    for name, value in (constants or {}).items():
        if name.startswith("replay."):
            if name not in REPLAY_ONLY or rt is None:
                raise ValueError("unknown replay-only constant %s" % name)
            REPLAY_ONLY[name](rt, value)
            continue
        mod, key = name.split(".")
        cur = K[mod][key] if K[mod] is not None else None
        if isinstance(cur, bool) or not isinstance(cur, (int, float)):
            raise ValueError("unknown kernel constant %s" % name)
        for dial_id in dials.linked(name):
            m2, k2 = dial_id.split(".")
            if K[m2] is not None:
                K[m2][k2] = float(value)


# The drain options a replay runs under by default (Plan 17 Task 3): the mod's own defaults, NR.DeathPace 3 (Realistic)
# and NR.HealthCombine 2 (Multiply) (media/sandbox-options.txt), and vanilla's 90-minute day (K.drain.DAY_MINUTES).
DEATH_PACE = 3
HEALTH_COMBINE = 2
DAY_MINUTES = 90


class ServerReplay(_Backend):
    """The mod's server adapters on server_host.Host with the golden stand-ins (see the module docstring). `constants`
    ({"table.NAME": value}) sets kernel constants after the host loads (set_constants), as the recording build had them.
    `death_pace` and `health_combine` are the server's NR.DeathPace and NR.HealthCombine and `day_minutes` its day length
    in real minutes (getDayLengthMinutes), by default 3, 2 and 90: the sandbox stand-in answers them, so the mod's own
    options poll and minute hoist write K.drain.OPT from them at every minute, as on a live server. Every row carries
    the stand-in's overall health (`health`); `game_heal` gives the stand-in's AddGeneralHealth the game's spread
    (Plan 17 Task 4, as tools/mod_guide_series.py's guide replay does)."""

    def __init__(self, start=None, user="admin", player=None, steps=None, hold_hour=None, hour_offset=0.0,
                 rng=None, stats=None, sleep_allowed=None, constants=None, sex_specific=False,
                 death_pace=DEATH_PACE, health_combine=HEALTH_COMBINE, day_minutes=DAY_MINUTES, game_heal=False):
        super().__init__()
        self.injected = []
        self.game_heal = bool(game_heal)
        lua51, server_host, golden_trace = _lua()
        self.lua51 = lua51
        self.h = server_host.Host(extra_env=golden_trace.ENV + REPLAY_ENV)
        self.rt = self.h.rt
        self.G = self.h.G
        self.NR = self.h.NR
        self.K = self.h.K
        set_constants(self.K, constants, self.rt)
        import participant
        self.rt.execute(participant.PARTICIPANT + PARTICIPANT_SIGHT)
        self.R = self.G.NR_R
        self.R.offset = float(hour_offset or 0.0)
        if hold_hour is not None:
            self.R.holdHour = float(hold_hour)
        if rng == "half":                                   # the responder constant reads 1 (z = 0)
            self.rt.execute("ZombRandFloat = function(lo, hi) return lo + (hi - lo) * 0.5 end")
        if steps is not None:
            self.NR.server.minute.ORDER = self.rt.table(*steps)
        if sleep_allowed is not None:
            # the live server's SleepAllowed and SleepNeeded, answered by a getServerOptions stand-in the options poll
            # reads every minute (NR.server.readSleep; the host has none, so the mod reads an unset option as sleep on)
            self.rt.execute("getServerOptions = function() return { getBoolean = function(s, k) return %s end } end;"
                            " NutritionRevamp.server.options.sleepOn = NutritionRevamp.server.readSleep()"
                            % ("true" if sleep_allowed else "false"))
        # the server's sandbox leaves, set in place (the options poll reads them every minute)
        self.rt.execute("SandboxVars = SandboxVars or {}; SandboxVars.NR = SandboxVars.NR or {}")
        if sex_specific:                                    # NR.SexSpecific on: a female stand-in reads the female values
            self.rt.execute("SandboxVars.NR.SexSpecific = true")
            self.NR.server.options.sexSpecific = True
        self.set_drain_options(death_pace, health_combine, day_minutes)
        self.users = {}
        self.user = None
        self.maint_kcal = None
        self.add_user(user, start, player, stats)

    def set_drain_options(self, death_pace=DEATH_PACE, health_combine=HEALTH_COMBINE, day_minutes=DAY_MINUTES):
        """The server's NR.DeathPace, NR.HealthCombine and day length from the next minute on (an admin's live change):
        the sandbox leaves and the sandbox stand-in's getDayLengthMinutes answer them, and the mod's options poll and
        minute hoist write K.drain.OPT."""
        for name, v in (("death_pace", death_pace), ("health_combine", health_combine), ("day_minutes", day_minutes)):
            if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v:
                raise ValueError("%s must be a number: %r" % (name, v))
        if int(death_pace) not in (1, 2, 3) or int(health_combine) not in (1, 2, 3) or not day_minutes > 0:
            raise ValueError("drain options out of range: %r" % ((death_pace, health_combine, day_minutes),))
        self.rt.execute("SandboxVars.NR.DeathPace = %d; SandboxVars.NR.HealthCombine = %d" % (death_pace, health_combine))
        self.rt.eval("function(d) NutritionRevamp.sandbox().getDayLengthMinutes = function(s) return d end end")(
            float(day_minutes))
        self.drain_options = (int(death_pace), int(health_combine), float(day_minutes))

    def add_user(self, user, start=None, player=None, stats=None):
        """A stand-in player for `user`, online alone, with `start` placed in the store's records. The player config's
        `health` (absent: 100) is the stand-in's overall health at the start."""
        cfg = {"rate": None, "inv": 0.0, "maxW": 8.0, "traits": [], "female": False, "weight": 80.0,
               "macros": (1000.0, 100.0, 40.0, 60.0)}
        cfg.update(player or {})
        p = self.h.player(user, *cfg["macros"])
        p.nut.weight = cfg["weight"]
        if "weight" in (player or {}):                   # an explicit weight: first sight lays that participant's body
            self.R.weights[user] = cfg["weight"]
        lcfg = self.rt.table()
        lcfg.rate = 1.0
        lcfg.inv = cfg["inv"]
        lcfg.maxW = cfg["maxW"]
        lcfg.traits = self.rt.table(*cfg["traits"])
        lcfg.female = bool(cfg["female"])
        if cfg.get("health") is not None:
            lcfg.health = float(cfg["health"])
        sv = {"HUNGER": 0.2, "THIRST": 0.1, "FATIGUE": 0.1}
        sv.update(stats or {})
        lcfg.hunger, lcfg.thirst, lcfg.fatigue = sv["HUNGER"], sv["THIRST"], sv["FATIGUE"]
        p = self.G.NR_T.decorate(p, lcfg)
        if self.game_heal:                               # the game's spread: overall health rises 5.05 / 17 of the add
            self.rt.eval("function(bd) bd.AddGeneralHealth = function(s, v) "
                         "s.st.added = s.st.added + v / NutritionRevamp.kernel.drain.PART_SPREAD end end")(
                p.getBodyDamage(p))
        # an idle player's engine MET: the engine's Default class, 1.5 (a live idle player reads 1.50, #2875), which
        # the mod's classOf reads as Default and bills at COMPENDIUM.Default (standing quietly); never the Compendium
        # value 1.3 itself, which classOf reads as DrivingCar and bills at 1.4 (finding F-1)
        rate = cfg["rate"] if cfg["rate"] is not None else self.K.energy.CLASS_MET.Default
        self.R.adopt(p, user, rate, cfg["inv"], cfg["maxW"])
        for k, v in sv.items():
            p.sv[k] = v
        raw = self.lua_record(start)
        if raw is not None:
            self.NR.server.store.records[user] = raw
        self.users[user] = p
        self.user = user
        self.p = p
        self.h.online(p)
        self.maint_kcal = None
        return p

    def lua_record(self, start):
        """A start record as the store's load meets it: a slot file's JSON decoded by the mod's own K.json."""
        if start is None:
            return None
        if isinstance(start, str):
            text = start
        else:
            doc = start
            if isinstance(doc, dict) and "values" in doc and "rec" not in doc:
                doc = nest(doc["values"])
            text = json.dumps(doc)
        t = self.K.json.decode(text)
        if isinstance(t, tuple):                         # decode answers (value, err)
            if t[0] is None:
                raise ValueError("the start record does not decode: %s" % (t[1],))
            t = t[0]
        if self.lua51.lua_type(t) == "table" and t["rec"] is not None and t["done"] is not None:
            t = t["rec"]
        return t

    def table(self, d):
        t = self.rt.table()
        for k, v in d.items():
            t[k] = v
        return t

    def record(self):
        return self.NR.server.store.records[self.user]

    def start_age(self):
        r = self.record()
        if r is None:
            return None
        for path in (("satiety", "t"), ("kineticsAge",), ("lastSeen",)):
            node = r
            for k in path:
                node = node[k] if node is not None and self.lua51.lua_type(node) == "table" else None
            if isinstance(node, (int, float)):
                return float(node)
        return None

    # the events
    def _set_age(self, at):
        self.G.NR_T.age = at

    def _added(self):
        a = self.p.wst.added
        return (a["BOREDOM"] or 0.0), (a["UNHAPPINESS"] or 0.0)

    def _log(self, at, kind, full, vec, b0):
        b1 = self._added()
        cal = None if vec is None else vec["calories"]
        self.eats.append({"age": at, "kind": kind, "fullType": full, "kcal": cal,
                          "boredom": b1[0] - b0[0], "unhappy": b1[1] - b0[1]})

    def ev_eat(self, ev, at):
        self._set_age(at)
        b0 = self._added()
        if "vec" in ev:
            vec = self.R.landVec(self.user, self.table(ev["vec"]), ev.get("lane"), ev.get("fullType"),
                                 ev.get("foodType"))
            self._log(at, "eat", ev.get("fullType"), vec, b0)
            return
        spec = dict(study_foods()[ev["food"]]) if "food" in ev else {}
        for k in ("fullType", "cal", "carb", "lip", "pro", "hunger", "declared", "foodType"):
            if k in ev:
                spec[k] = ev[k]
        lspec = self.rt.table()
        for k in ("fullType", "cal", "carb", "lip", "pro", "declared", "foodType"):
            if spec.get(k) is not None:
                lspec[k] = spec[k]
        lspec.instBase = spec["hunger"]
        lspec.frac = float(ev.get("frac", 1.0))
        vec = self.R.eatItem(self.user, lspec)
        self._log(at, "eat", spec["fullType"], vec, b0)

    def ev_drink(self, ev, at):
        self._set_age(at)
        b0 = self._added()
        if "vec" in ev:
            vec = self.R.landVec(self.user, self.table(ev["vec"]), "liquid", None, None)
        else:
            vec = self.R.drink(self.user, ev["fluid"], float(ev["litres"]))
        self._log(at, "drink", ev.get("fluid"), vec, b0)

    def ev_autodrop(self, ev, at):
        """The writer's auto-drink sip as the mod lands it: `g` grams of water ADDED to the record's fluids.autoDrop
        (in thirst units, g / (LITRES_PER_THIRST x 1000)), so the Nutrients step of the drain that follows lands it
        as liquid after Kinetics has emptied the stomach (NR_Server_Nutrients.lua:423-433). It books nothing a
        drink does (no IN.land, no landed guard, no eats log row)."""
        g = ev.get("g")
        if isinstance(g, bool) or not isinstance(g, (int, float)) or not g >= 0:
            raise ValueError("autodrop needs g, a water mass in grams >= 0: %r" % (ev,))
        self._set_age(at)
        f = self.record()["fluids"]
        if f is None:
            raise ValueError("autodrop: the record has no fluids table")
        per = self.NR.server.nutrients.LITRES_PER_THIRST * 1000.0
        f["autoDrop"] = (f["autoDrop"] or 0.0) + float(g) / per

    def maint(self):
        if self.maint_kcal is None:
            body = self.record()["body"]
            if body is None:
                raise ValueError("a maint meal before the record has a body")
            self.maint_kcal = self.R.maint(body)
        return self.maint_kcal

    def request_kcal(self, at):
        r = self.record()
        es = 1.0
        if r is not None and r["body"] is not None and isinstance(r["body"]["energyState"], (int, float)):
            es = r["body"]["energyState"]
        return self.R.requestKcal(es, self.R.tod(at), H_REQ, KCAL_PER_H)

    def ev_meal(self, ev, at):
        self._set_age(at)
        kcal = self.meal_kcal(ev, at)
        b0 = self._added()
        if "food" in ev:
            spec = study_foods()[ev["food"]]
            per = {k: v * kcal / spec["cal"] for k, v in declared_vector(spec).items()}
            vec = self.R.landVec(self.user, self.table(per), None, ev["food"], spec.get("foodType"))
        elif "plate" in ev:
            vec = self.R.landVec(self.user, self.table(self.plate_vector(ev["plate"], kcal)), None, None, None)
        else:
            comp = ev.get("comp", MIXED)
            vec = self.R.mealVec(kcal, comp["p"], comp["c"], comp["f"])
            vec = self.R.landVec(self.user, vec, None, None, None)
        self._log(at, "meal", ev.get("food"), vec, b0)

    def plate_vector(self, foods, kcal):
        """A plate of real foods sized to kcal: the sum of each fullType's whole vector in the mod's table
        (NR.data.nutrients.get), every key scaled by kcal over the plate's own kcal, so the meal carries the foods'
        macros and micronutrients in their proportions."""
        tot = {}
        for ft in foods:
            t = self.NR.data.nutrients.get(ft)
            if t is None:
                raise ValueError("plate: %s is not in the mod's table" % ft)
            for k, v in t.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    tot[k] = tot.get(k, 0.0) + float(v)
        if not tot.get("calories"):
            raise ValueError("plate: no calories in %r" % (foods,))
        f = kcal / tot["calories"]
        return {k: v * f for k, v in tot.items()}

    def ev_sleep(self, ev, at):
        self.R.u[self.user].asleep = bool(ev["asleep"])

    def ev_activity(self, ev, at):
        u = self.R.u[self.user]
        if "rate" in ev:
            u.rate = float(ev["rate"])
        if "raw" in ev:
            u.raw = None if ev["raw"] is None else float(ev["raw"])
        if "moving" in ev:
            u.moving = bool(ev["moving"])
        if "exercising" in ev:
            u.exercising = bool(ev["exercising"])
        if "cold" in ev:
            u.cold = None if ev["cold"] is None else float(ev["cold"])

    def ev_stat(self, ev, at):
        self.p.sv[ev["stat"]] = ev["value"]

    def ev_trait(self, ev, at):
        key = self.G.CharacterTrait[ev["trait"]]
        if key is None:
            raise ValueError("trait: the stand-in's CharacterTrait has no %r" % (ev["trait"],))
        self.p.st.traits[key] = True if ev.get("on", True) else None

    def ev_setpath(self, ev, at):
        segs, glob = parse_path(ev["path"])
        root = self.G if glob else self.record()
        ok, parent = walk(self.lua51, root, segs[:-1]) if len(segs) > 1 else (True, root)
        if not ok or self.lua51.lua_type(parent) != "table":
            raise ValueError("setpath: no parent table for %s" % ev["path"])
        br, text = segs[-1]
        key = text
        if not br and parent[text] is None and _number(text) is not None and parent[_number(text)] is not None:
            key = _number(text)
        parent[key] = ev["value"]

    def begin(self, age):
        pass

    def feed(self, row, names):
        for n in names:
            if n in row and row[n] is not None:
                self.p.sv[n] = row[n]

    def step(self, age):
        if getattr(self, "away", False):
            self.h.online(self.p)                       # back: the mod sights the player at this minute
            self.away = False
        elif not getattr(self, "began", False) and self.record() is not None:
            # the start record continues the live server's: its first minute is no return and no stall, so lastSeen
            # reads this minute, the store's resume moves nothing and each adapter steps from its own stamp, as the
            # live pipeline's next minute did (Plan 16 Task 2)
            self.record().lastSeen = age
        self.began = True
        self._minute(age)

    def step_offline(self, age):
        """An offline minute: the minute fires with the user absent from the online players, so the mod drains
        nothing of the user's (its own disconnect handling runs as live)."""
        if not getattr(self, "away", False):
            self.h.online()
            self.away = True
        self.began = True
        self._minute(age)

    def _minute(self, age):
        T = self.G.NR_T
        T.age = age
        T.m = (T.m or 0) + 1
        self.h.minute()
        for _ in range(MAX_TICKS):
            self.h.tick(1)
            if self.R.drained():
                return
        raise RuntimeError("the queue did not drain in %d ticks" % MAX_TICKS)

    def row(self, paths):
        out = {"on": not getattr(self, "away", False)}
        for n in STATS:
            v = self.p.sv[n]
            if v is not None:
                out[n] = v
        bd = self.p.getBodyDamage(self.p)
        out["health"] = float(bd.getOverallBodyHealth(bd))
        r = self.record()
        sat = r["satiety"] if r is not None else None
        if sat is not None and isinstance(sat["hModel"], (int, float)):
            out[H_MODEL] = sat["hModel"]
        self._symptoms(r, out)
        for path in paths:
            if path in self.DERIVED:
                body = r["body"] if r is not None else None
                if body is not None:
                    out[path] = self.DERIVED[path](self.K, body)
                continue
            segs, glob = parse_path(path)
            ok, v = walk(self.lua51, self.G if glob else r, segs)
            if ok:
                out[path] = _scalar(self.lua51, v)
        return out

    def _symptoms(self, r, out):
        """The symptom rows (SYMPTOM_STATS, SYMPTOM_FIELDS, effects.pain.<i>, painTarget) into out."""
        for n in SYMPTOM_STATS:
            v = self.p.sv[n]
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[n] = v
        E = r["effects"] if r is not None else None
        if E is None or self.lua51.lua_type(E) != "table":
            return
        for k in SYMPTOM_FIELDS:
            v = E[k]
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out["effects." + k] = v
        P, mod = E["pain"], self.K.effects.PAIN_MOD
        if P is None:
            return
        total = 0.0
        for i in range(self.K.effects.PAIN_PARTS):
            v = P[i]
            if isinstance(v, (int, float)) and v > 0:
                out["effects.pain.%d" % i] = v
                total += v * mod[i]
        out["painTarget"] = total

    # a path the record does not store, read as the mod reads it: body.eb24 is K.energy.eb24h(record.body), the
    # trailing-24 h balance the metabolism step hands to K.deficit.activityState (the oracle backend's alias of the same
    # name reads its own)
    DERIVED = {"body.eb24": lambda K, body: K.energy.eb24h(body)}


class OracleReplay(_Backend):
    """The oracles' kernel composition (see the module docstring); HUNGER is the displayed hunger, and the paths
    satiety.M, satiety.L, body.energyState and body.eb24 read its state."""

    ALIAS = {"body.energyState": "es", "body.eb24": "eb24", "satiety.M": "M", "satiety.L": "L"}

    def __init__(self, M0=0.0, energy=True, satiety=True, hold_es=False, hold_hour=False):
        super().__init__()
        lua51, server_host, _ = _lua()
        self.lua51 = lua51
        self.rt = lua51.LuaRuntime(unpack_returned_tuples=True)
        self.rt.execute(server_host.ENV)
        for p in server_host._shared_files():
            server_host._load(self.rt, p)
        import participant
        self.rt.execute(participant.PARTICIPANT)
        self.rt.execute(ORACLE_LUA)
        self.G = self.rt.globals()
        self.O = self.G.NR_O
        self.o = self.O.new(float(M0), bool(energy), bool(satiety), bool(hold_es), bool(hold_hour))
        self.traits = set()

    def table(self, d):
        t = self.rt.table()
        for k, v in d.items():
            t[k] = v
        return t

    def _eat(self, at, kind, full, src, lane, sate):
        self.O.eat(self.o, src, lane, sate)
        self.eats.append({"age": at, "kind": kind, "fullType": full, "kcal": src["calories"] or 0.0,
                          "boredom": 0.0, "unhappy": 0.0})

    def ev_eat(self, ev, at):
        if "vec" in ev:
            vec = ev["vec"]
        else:
            vec = declared_vector(study_foods()[ev["food"]])
        self._eat(at, "eat", ev.get("fullType", ev.get("food")), self.table(vec), ev.get("lane"),
                  ev.get("sate", True))

    def ev_drink(self, ev, at):
        self._eat(at, "drink", None, self.table(ev["vec"]), "liquid", ev.get("sate", True))

    def maint(self):
        return self.o.maint

    def request_kcal(self, at):
        return self.O.requestKcal(self.o, at, H_REQ, KCAL_PER_H)

    def ev_meal(self, ev, at):
        kcal = self.meal_kcal(ev, at)
        comp = ev.get("comp", MIXED)
        v = self.O.mealVec(kcal, comp["p"], comp["c"], comp["f"])
        self._eat(at, "meal", ev.get("food"), v, None, ev.get("sate", True))

    def ev_sleep(self, ev, at):
        self.o.asleep = bool(ev["asleep"])

    def ev_trait(self, ev, at):
        """The appetite traits' factor on M's clearance, K.satiety.trait as KIN.mealTrait reads the player's (the
        stand-in's sandbox multiplier is 1); the oracle's composition reads no other trait."""
        if ev.get("on", True):
            self.traits.add(ev["trait"])
        else:
            self.traits.discard(ev["trait"])
        self.o.trait = self.G.NutritionRevamp.kernel.satiety.trait("HEARTY_APPETITE" in self.traits,
                                                                   "LIGHT_EATER" in self.traits)

    def feed(self, row, names):
        pass

    def start_age(self):
        return None

    def begin(self, age):
        self.O.trail(self.o, age)                       # the window to the minute's end, before its eats land

    def step(self, age, dtM=1.0):
        self.O.minute(self.o, age, dtM)

    def row(self, paths):
        out = {"on": True}
        if self.o.hunger is not None:
            out["HUNGER"] = self.o.hunger
            out[H_MODEL] = self.o.hunger                    # the composition has no curve: its hunger is the model's
        for path in paths:
            if path in self.ALIAS:
                out[path] = self.o[self.ALIAS[path]]
            else:
                segs, _ = parse_path(path)
                ok, v = walk(self.lua51, self.o.rec, segs)
                if ok:
                    out[path] = _scalar(self.lua51, v)
        return out


def _scalar(lua51, v):
    if isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, bytes):
        return v.decode("utf-8")
    t = lua51.lua_type(v)
    return "table" if t == "table" else t


# --- the engine ---------------------------------------------------------------------------------------------------

def _clock_row(age, prev, tod):
    out = {"age": age}
    if prev is not None:
        out["dtM"] = (age - prev) * 60
    if tod is not None:
        out["hour"] = int(math.floor(tod))
        out["min"] = int(math.floor((tod - math.floor(tod)) * 60))
    return out


def check_feed(feed):
    """Raises ValueError unless every name in `feed` is an exogenous input (ALLOWED_FEED)."""
    for n in feed or ():
        if n in GRADED_FEED:
            raise ValueError("feed %r is a graded or tolerance field: the replay would grade the ring against itself; "
                             "the feed takes only %s" % (n, ", ".join(ALLOWED_FEED)))
        if n not in ALLOWED_FEED:
            raise ValueError("feed %r is not an exogenous input; the feed takes only %s" % (n, ", ".join(ALLOWED_FEED)))


def run(backend, ages, events, paths=(), start_age=None, seqs=None, ring_rows=None, feed=(), dtms=None,
        offline=()):
    """Steps `backend` one drain per age in `ages`. Before drain k: the events due (see the module docstring), then
    the stats `feed` names from ring_rows[k] (exogenous inputs only, check_feed). Returns one row per drain: the state
    the drain left, with its clock (age, dtM, hour, min), `k`, and `events`, the count of events applied before it.
    A k in `offline` is not drained: its events still fall due, nothing is fed, the backend's step_offline runs (the
    minute with the user away) when it has one, and the row carries on = false and offline. The first drained row
    after such a window carries gapM, the game minutes since the last drain, and clampM, min(gapM, OFFLINE_CAP_M): the
    offline minutes the mod's own reconnect integrates (none: its resume freezes the absence)."""
    check_feed(feed)
    offline = set(offline or ())
    evs = list(events or [])
    for e in evs:
        if not any(x in e for x in ("age", "s", "minute")):
            raise ValueError("an event without age, s or minute: %r" % (e,))
    done = [False] * len(evs)
    # minute-keyed events fall due only at their own step, so they are bucketed; the rest are scanned while pending.
    # Either way the events due before a drain apply in the list's order (a long replay need not scan every event at
    # every minute)
    by_minute = {}
    pending = []
    for i, e in enumerate(evs):
        if "minute" in e:
            by_minute.setdefault(e["minute"], []).append(i)
        else:
            pending.append(i)

    def due(k, prev, age, seq):
        idx = list(by_minute.get(k, ()))
        idx.extend(i for i in pending if _due(evs[i], k, prev, age, seq))
        if len(idx) > len(by_minute.get(k, ())):
            got = set(idx)
            pending[:] = [i for i in pending if i not in got]
        return sorted(idx)

    out = []
    prev = start_age
    last = start_age
    away = False
    for k, age in enumerate(ages):
        seq = seqs[k] if seqs is not None else None
        if k in offline:
            n = nr = 0
            for i in due(k, prev, age, seq):
                backend.apply(evs[i], _event_age(evs[i], prev, age))
                done[i] = True
                n += 1
                nr += evs[i].get("label") == RING_ACTIVITY_LABEL
            if hasattr(backend, "step_offline"):
                backend.step_offline(age)
            row = backend.row(paths)
            tod = backend.R.tod(age) if isinstance(backend, ServerReplay) else None
            row.update(_clock_row(age, prev, tod))
            row.update({"k": k, "events": n, "ringEvents": nr, "on": False, "offline": True})
            out.append(row)
            prev = age
            away = True
            continue
        backend.begin(age)
        n = nr = 0
        for i in due(k, prev, age, seq):
            backend.apply(evs[i], _event_age(evs[i], prev, age))
            done[i] = True
            n += 1
            nr += evs[i].get("label") == RING_ACTIVITY_LABEL
        if ring_rows is not None and feed:
            backend.feed(ring_rows[k], feed)
        if isinstance(backend, OracleReplay):
            if dtms is not None:
                backend.step(age, dtms[k])
            else:
                backend.step(age, 1.0 if prev is None else (age - prev) * 60)
        else:
            backend.step(age)
        row = backend.row(paths)
        tod = backend.R.tod(age) if isinstance(backend, ServerReplay) else None
        row.update(_clock_row(age, prev, tod))
        row["k"] = k
        row["events"] = n
        row["ringEvents"] = nr
        if away and last is not None:
            row["gapM"] = (age - last) * 60
            row["clampM"] = min(row["gapM"], OFFLINE_CAP_M)
        away = False
        out.append(row)
        prev = age
        last = age
    left = [e for i, e in enumerate(evs) if not done[i]]
    if left:
        raise ValueError("%d event(s) never fell due, the first %r" % (len(left), left[0]))
    return out


# A drink sip by sip (Plan 16 Task 7, spec section 4.3; carries section 1). Vanilla drinks over its action's length:
# the server's AnimEventEmulator calls ISDrinkFluidAction.updateEat about every 100 ms with the action's progress,
# server wall time over its duration (#0085), and a networked action's server length is 20 real ms a unit of its
# adjusted duration (#3766). A fluid whose properties carry no HungerChange (Water) drinks in 460 units whatever the
# volume and a popcan in 160 (vanilla shared/TimedActions/ISDrinkFluidAction.lua ISDrinkFluidAction.new, the
# `hungerConsumed == 0` line 167 and the `popcan` lines 168-169), and ISBaseTimedAction.adjustMaxTime (lines 99-123)
# multiplies the length by (1 + Unhappy level / 4) x (1 + Drunk level / 4) x the body temperature's
# getTimedActionTimeModifier (the hand-pain term is skipped: the drink sets ignoreHandsWounds). The mod lands each sip
# as it is drunk (NR_Server_Intake.lua IN.installDrink), so a drink's water reaches the liquid lane over its wall
# span, which the game clock turns into game minutes at the day length and the speed: 14.7 game minutes at DayLength
# 1, 2.5 at the default 4 (x452b's 0.5 L landed over 15 ring rows at DayLength 1).
DRINK_UNIT_MS = 20.0                 # #3766: 20 real ms a unit of a networked action's adjusted duration
DRINK_SIP_MS = 100.0                 # the AnimEventEmulator's drinkFluid cadence (ISDrinkFluidAction.serverStart)
DRINK_MAX_TIME = 460                 # ISDrinkFluidAction.new: hungerConsumed 0 (no HungerChange) reads 460
DRINK_POPCAN_MAX_TIME = 160          # ISDrinkFluidAction.new: an item whose eat type is popcan reads 160
DRINK_NO_HUNGER = ("Water", "TaintedWater", "CarbonatedWater")   # media/scripts/generated/fluids.txt: no HungerChange
# The sandbox DayLength index -> real minutes a game day (media/lua/shared/Translate/EN/Sandbox.json, the
# Sandbox_DayLength options: 15 and 30 minutes, then 1, 1.5, 2 and 3 to 23 hours, then real time).
DAY_LENGTH_REAL_MIN = {1: 15.0, 2: 30.0, 3: 60.0, 4: 90.0, 5: 120.0, 27: 1440.0}
DAY_LENGTH_REAL_MIN.update({n: (n - 3) * 60.0 for n in range(6, 27)})


def _level(ev, key):
    v = ev.get(key, 0)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 4:
        raise ValueError("%s must be a moodle level 0-4: %r" % (key, ev))
    return float(v)


def drink_units(ev):
    """A whole drink's adjusted action length in units, as vanilla sets it (see the block above): the event's maxTime
    (vanilla's raw length; a fluid with a HungerChange needs it, 232 x its eating loop from the container's hunger),
    else DRINK_POPCAN_MAX_TIME for eatType popcan, else DRINK_MAX_TIME for a fluid with no HungerChange; then
    adjustMaxTime's factors from the event's `unhappy` and `drunk` moodle levels (0-4, default 0) and its `timeMod`
    (getTimedActionTimeModifier, default 1)."""
    mt = ev.get("maxTime")
    if mt is None:
        if ev.get("eatType") == "popcan":
            mt = DRINK_POPCAN_MAX_TIME
        elif ev.get("fluid") in DRINK_NO_HUNGER:
            mt = DRINK_MAX_TIME
        else:
            raise ValueError("a whole drink of %r needs maxTime (vanilla's action length; only a fluid with no "
                             "HungerChange reads %d, a popcan %d): %r"
                             % (ev.get("fluid"), DRINK_MAX_TIME, DRINK_POPCAN_MAX_TIME, ev))
    if isinstance(mt, bool) or not isinstance(mt, (int, float)) or not mt > 0:
        raise ValueError("maxTime must be a positive action length: %r" % (ev,))
    mod = ev.get("timeMod", 1.0)
    if isinstance(mod, bool) or not isinstance(mod, (int, float)) or not mod > 0:
        raise ValueError("timeMod must be a positive multiplier: %r" % (ev,))
    mt = float(mt)
    if mt > 1:                                       # adjustMaxTime adjusts only a length above 1
        mt = mt * (1 + _level(ev, "unhappy") / 4) * (1 + _level(ev, "drunk") / 4) * float(mod)
    return mt


def drink_span_h(ev, day_length, speed=1.0):
    """A whole drink's span in game hours: drink_units times DRINK_UNIT_MS of wall time, at the day length's real
    seconds a game minute over the true time multiplier `speed`."""
    if day_length not in DAY_LENGTH_REAL_MIN:
        raise ValueError("unknown DayLength %r (the sandbox index, 1-27)" % (day_length,))
    if isinstance(speed, bool) or not isinstance(speed, (int, float)) or not speed > 0:
        raise ValueError("speed must be a positive true time multiplier: %r" % (speed,))
    real_s = drink_units(ev) * DRINK_UNIT_MS / 1000.0
    real_s_per_game_min = DAY_LENGTH_REAL_MIN[day_length] * 60.0 / 1440.0
    return real_s * speed / real_s_per_game_min / 60.0


def whole_drinks(events):
    """The indices of the whole drinks in `events`: a drink event of {fluid, litres} flagged whole true (never a vec,
    a sip the writer or a driver already booked). A flagged drink whose label another drink event shares is refused:
    a live ring's drinks are logged per ring row their sips landed on (x45g_lib.build_events and every earlier lib's:
    the eats-or-sips rows of x263, x264, x265, x363, x447, x452 and x452b), and one that landed on a single row carries
    a label of its own, so only the caller that wrote the event knows it is a whole drink; nothing is spread unless
    flagged, and a ring's own log never is."""
    out, labels = [], {}
    for e in events:
        if e.get("kind") == "drink" and e.get("label") is not None:
            labels[e["label"]] = labels.get(e["label"], 0) + 1
    for i, e in enumerate(events):
        if e.get("kind") != "drink" or e.get("whole") is not True:
            continue
        if "vec" in e or "litres" not in e:
            raise ValueError("a whole drink needs {fluid, litres}, never a vec: %r" % (e,))
        if e.get("label") is not None and labels[e["label"]] > 1:
            raise ValueError("a whole drink shares its label with another drink event (a per-sip log): %r" % (e,))
        out.append(i)
    return out


def spread_drinks(events, ages, seqs=None, start_age=None, day_length=None, speed=1.0):
    """Each whole drink (whole_drinks) replaced by its sips over its span (drink_span_h): sip j of n (n the span's
    DRINK_SIP_MS cadence, j from 0) carries litres / n and falls at the drink's start plus span x j / n, and the sips
    falling before one drain are landed as one drink event keyed to that step (`minute`, the step index), the drain
    that first follows them; the first at the step the drink itself fell due, so a vanishing span lands as before.
    A sip past the clock's last step lands at the last. A drink that never falls due is left as it is (run refuses it).
    Without a day length nothing is spread. Returns (events, report): one report row a spread drink {label, step,
    steps, litres, spanM}."""
    evs = list(events or [])
    if day_length is None:
        return evs, []
    idx = set(whole_drinks(evs))
    if not idx:
        return evs, []
    ages = list(ages)
    out, report = [], []
    for i, e in enumerate(evs):
        if i not in idx:
            out.append(e)
            continue
        k0 = None
        for k, age in enumerate(ages):
            prev = start_age if k == 0 else ages[k - 1]
            if _due(e, k, prev, age, seqs[k] if seqs is not None else None):
                k0 = k
                break
        if k0 is None:
            out.append(e)
            continue
        prev0 = start_age if k0 == 0 else ages[k0 - 1]
        a0 = _event_age(e, prev0, ages[k0])
        if a0 is None:
            a0 = ages[k0]
        span = drink_span_h(e, day_length, speed)
        n = max(1, int(round(drink_units(e) * DRINK_UNIT_MS / DRINK_SIP_MS)))
        litres = float(e["litres"]) / n
        buckets = {}
        k = k0
        for j in range(n):
            a = a0 + span * j / n
            while k + 1 < len(ages) and ages[k] < a - 1e-12:
                k += 1
            buckets[k] = buckets.get(k, 0) + 1
        for k in sorted(buckets):
            sip = {key: v for key, v in e.items() if key not in ("age", "s", "minute", "litres", "whole")}
            sip.update({"minute": k, "litres": litres * buckets[k]})
            out.append(sip)
        report.append({"label": e.get("label"), "step": k0, "steps": len(buckets), "litres": float(e["litres"]),
                       "spanM": span * 60.0})
    return out, report


def synthetic_ages(minutes, start_age=0.0, dtM=1.0):
    """A synthetic clock: step m ends at start_age + (m + 1) x dtM / 60 (the oracles' minute m)."""
    return [start_age + (m + 1) * dtM / 60.0 for m in range(minutes)]


def offline_row(r):
    """A ring row taken with the user away (on false): no drain ran for it. An online row with no record yet (norec)
    is the first sight, which the mod drains in that minute (ruling S0-3), so it is not offline."""
    return r.get("on") is False


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def link_marks(use):
    """One {gap, suspect, offline} per replay row k, read off the ring's own bookkeeping between ring rows k and k + 1
    (replay row k is compared with ring row k + 1):
      gap      s does not advance by 1 (a row lost), ev does not advance by 1 (a sample that raised: a minute the ring
               never saw), or row k + 1's dtM exceeds GAP_DTM (a long minute; the quantized
               0.8 / 1.6 rows are not). The replay still steps the real age
               delta; the row is graded and its findings carry gap.
      suspect  drained (the mod's count of drains begun) did not advance from row k to row k + 1: the drain after row
               k had not run when row k + 1 was read. Not graded.
      offline  row k or row k + 1 is offline_row: no drain k, or a row read with the user away. Not graded; an
               offline row is never also suspect.
    The last row has no successor: it is marked offline when it is offline_row."""
    out = []
    for k, a in enumerate(use):
        m = {"gap": False, "suspect": False, "offline": offline_row(a)}
        if k + 1 < len(use):
            b = use[k + 1]
            m["offline"] = m["offline"] or offline_row(b)
            if _num(a.get("s")) and _num(b.get("s")) and b["s"] != a["s"] + 1:
                m["gap"] = True
            if _num(a.get("ev")) and _num(b.get("ev")) and b["ev"] != a["ev"] + 1:
                m["gap"] = True
            if _num(b.get("dtM")) and b["dtM"] > GAP_DTM:
                m["gap"] = True
            if not m["offline"] and _num(a.get("drained")) and _num(b.get("drained")) and b["drained"] <= a["drained"]:
                m["suspect"] = True
        out.append(m)
    return out


AUTODRINK_LIQUID = "stomach.liquid"
AUTODRINK_EATS = "_G.NutritionRevamp.server.intake.stats.eats"
AUTODRINK_SIPS = "_G.NutritionRevamp.server.intake.stats.sips"
AUTODRINK_MIN_G = 5.0              # a liquid-lane rise below this is not a drink (decay only lowers the lane)
AUTODRINK_WINDOW = 3               # rows before a rise within which a logged event or an intake counter explains it


def parse_bool(text):
    t = str(text).strip().lower()
    if t in ("true", "1", "yes"):
        return True
    if t in ("false", "0", "no"):
        return False
    raise ValueError("expected true or false, got %r" % (text,))


def resolve_sleep_allowed(flag, start):
    """The live server sleep option (SleepAllowed and SleepNeeded both true): the explicit input, else the start
    document sleepAllowed. Required: the host has no getServerOptions, and an unset option would read as allowed."""
    if flag is not None:
        return bool(flag)
    if isinstance(start, dict) and "sleepAllowed" in start:
        return bool(start["sleepAllowed"])
    raise ValueError("the sleep option is required: pass sleep_allowed (--sleep-allowed true|false) or carry "
                     "sleepAllowed in the start document; the live server SleepAllowed and SleepNeeded decide "
                     "whether its sleep state froze")


def detect_autodrinks(ring_rows, events, min_g=AUTODRINK_MIN_G, window=AUTODRINK_WINDOW):
    """Finding F-T4-2: the engine auto-drink (the server setAutoDrink(false) does not hold, #2941) drinks from a
    carried container and the writer folds it as a sip (#2965); a driver logs no event for it and no intake counter
    moves. It is read off the ring liquid lane (stomach.liquid): a rise of at least min_g between two rows with no
    logged event keyed to a ring row within `window` rows before it and no rise of intake.stats.eats or .sips in
    those rows. Each is a drink event of that water mass (1 g per mL) at that row. This reads a ring OUTPUT to make an
    input, so replay_live takes it only on request (detect_autodrink=True)."""
    rows = [r for r in ring_rows if r.get("s") is not None]
    if not any(AUTODRINK_LIQUID in r for r in rows):
        raise ValueError("the ring has no %s path: arm the minute ring on it to detect auto-drinks" % AUTODRINK_LIQUID)
    keyed = [e["s"] for e in events or [] if "s" in e]
    out = []
    for i in range(1, len(rows)):
        a, b = rows[i - 1], rows[i]
        la, lb = a.get(AUTODRINK_LIQUID), b.get(AUTODRINK_LIQUID)
        if la is None or lb is None or lb - la < min_g:
            continue
        w = rows[max(0, i - window):i + 1]
        if any(b["s"] - window <= s <= b["s"] for s in keyed):
            continue
        if any((w[-1].get(k) or 0) != (w[0].get(k) or 0) for k in (AUTODRINK_EATS, AUTODRINK_SIPS)):
            continue
        out.append({"s": b["s"], "kind": "drink", "fluid": "Water", "litres": (lb - la) / 1000.0,
                    "label": "autodrink"})
    return out


RING_ACTIVITY_KEYS = ("rate", "raw", "exercising")


RING_ACTIVITY_LABEL = "ring-activity"


def ring_activity_events(rows):
    """The live activity read off the ring's exogenous fields (Plan 11f C-17): for each row, in order, that carries the
    harness's raw engine `rate` or exercise flag `exe` and is not offline, an event {s, kind activity, raw, exercising}
    due before that row's drain, emitted where either value changed since the last event (a row missing a field keeps
    the last value). Never reads body.met or any other output the mod writes."""
    out = []
    last_raw, last_exe = None, None
    for r in rows:
        if offline_row(r) or r.get("s") is None:
            continue
        raw = r.get("rate")
        exe = r.get("exe")
        if raw is None and exe is None:
            continue
        raw = last_raw if raw is None else float(raw)
        exe = last_exe if exe is None else bool(exe)
        if out and raw == last_raw and exe == last_exe:
            continue
        ev = {"s": r["s"], "kind": "activity", "label": RING_ACTIVITY_LABEL}
        if raw is not None:
            ev["raw"] = raw
        if exe is not None:
            ev["exercising"] = exe
        out.append(ev)
        last_raw, last_exe = raw, exe
    return out


def ring_carries_activity(rows):
    """Whether any ring row carries the harness's raw `rate` or exercise flag `exe` (3daaca9)."""
    return any(r.get("rate") is not None or r.get("exe") is not None for r in rows)


# The ring's cold multiplier (Plan 16 Task 8, 106dafa1: the harness's `cold` field, the record's body.coldMult; a ring
# armed on the `body.coldMult` start path carries the same leaf, x456 and x457): the field first, the path where the
# row lacks the field.
RING_COLD_KEYS = ("cold", "body.coldMult")


def _ring_cold(r):
    for key in RING_COLD_KEYS:
        v = r.get(key)
        if _num(v):
            return float(v)
    return None


def ring_carries_cold(rows):
    """Whether any ring row carries the cold multiplier (RING_COLD_KEYS)."""
    return any(_ring_cold(r) is not None for r in rows)


def ring_cold_events(rows):
    """The thermoregulator's cold multiplier read off the ring (Plan 16 Task 7; #3947): the mod stamps body.coldMult
    from getEnergyMultiplier in drain k's Metabolism step and reads it back in the same drain's Nutrients step (the cold
    diuresis, the shivering glycogen draw), and ring row k + 1 is read before drain k + 1, so row k + 1's value is the
    one drain k used. For each online row k whose successor is online and carries the value, an event {s: row k's s,
    kind activity, cold} due before row k's drain, emitted where the value changed since the last event (the last row,
    and a row before an offline one, keep the last value). The stand-in's getEnergyMultiplier answers it, which also
    scales the energy bill (K.energy.minute's coldK) exactly as live. It reads the record's copy of an exogenous input
    one row ahead, never an output the mod derives."""
    out = []
    last = None
    for k in range(len(rows) - 1):
        a, b = rows[k], rows[k + 1]
        if offline_row(a) or offline_row(b) or a.get("s") is None:
            continue
        v = _ring_cold(b)
        if v is None or v == last:
            continue
        out.append({"s": a["s"], "kind": "activity", "cold": v, "label": RING_ACTIVITY_LABEL})
        last = v
    return out


def replay_live(ring_rows, events, start, paths=None, user="admin", player=None, feed=DEFAULT_FEED, steps=None,
                hour_offset=None, hold_hour=None, ring_paths=(), start_read_age=None, start_stats=None,
                sleep_allowed=None, detect_autodrink=False, ring_activity=None, constants=None, ring_cold=None,
                day_length=None, speed=1.0, death_pace=DEATH_PACE, health_combine=HEALTH_COMBINE,
                day_minutes=DAY_MINUTES, game_heal=False):
    """Mode live: the ring's clock and the live event log from the start record on. Ring rows at or before the start
    record's own age (its last drain) are dropped, and events at or before its READ age are dropped, because the
    record holds them (kept on backend.dropped). The read age is `start_read_age`, else a top-level `readAge` the
    start document carries, else the record's own age. The driver contract: the driver logs the start record's read
    age, or reads the record with no eat since the last drain. An s-keyed event on the first ring row after the
    record is refused when the read age lies past the record's age (it cannot say which side of the read it fell).

    The stand-in's stats start at `start_stats` (a driver-logged {stat: value}) or the stand-in's defaults, never at a
    ring row's outputs; the feed copies only exogenous inputs (check_feed). The ring's bookkeeping marks the replay
    rows (link_marks): offline rows are not drained (run's offline), suspect rows are not graded, gap rows are graded
    and marked. Returns (rows, backend); replay row k is the state drain k left, labelled with ring row k + 1's s (the
    last row: its own s + 1) and carrying that row's clock when it exists, and `between` set when an event fell due
    before drain k + 1 (it landed between drain k and ring row k + 1).

    `sleep_allowed` (or `sleepAllowed` in the start document) is REQUIRED: the live server SleepAllowed and
    SleepNeeded, which the host cannot read (F-T4-1). `detect_autodrink` (opt-in) injects the unlogged liquid-lane
    rises of detect_autodrinks as drink events, named on backend.injected.

    `ring_activity` (None: on when the ring carries the harness's `rate` or `exe`): the activity comes from the ring's
    exogenous fields (ring_activity_events, named on backend.ring_activity), and an activity event in `events` that
    names rate, raw or exercising is refused (the inputs would come from two places). False keeps the log's own.

    `ring_cold` (None: on when the ring carries the cold multiplier, the harness's `cold` field or a `body.coldMult`
    path): the thermoregulator's getEnergyMultiplier answers the ring's value (ring_cold_events, named on
    backend.ring_cold), and an activity event in `events` that names cold is refused. False answers 1, as before.

    `day_length` (the server's sandbox DayLength index; None: no spreading) and `speed` (the true time multiplier,
    1 by default) spread each whole drink over its action's span, sip by sip (spread_drinks, named on backend.spread);
    only a drink flagged whole is spread, never a ring's per-sip log (whole_drinks refuses a flagged drink whose label
    another drink shares).

    `constants` ({"table.NAME": value}, e.g. DEFICIT_11F) replays at the recording build's kernel constants.

    `death_pace`, `health_combine` and `day_minutes` (ServerReplay's: the server's NR.DeathPace, NR.HealthCombine and
    day length in real minutes, by default 3, 2 and 90) are the drain options the live server ran under; `game_heal`
    (ServerReplay's) gives the stand-in's AddGeneralHealth the game's spread, so a replay that heals reads the game's
    health (a ring's `health` field, harness Plan 17 Task 4, is compared with the row's `health`)."""
    rows = [r for r in ring_rows if r.get("age") is not None]
    if isinstance(start, dict) and "sleepAllowed" in start:
        start = dict(start)
        carried_sleep = start.pop("sleepAllowed")
        if sleep_allowed is None:
            sleep_allowed = carried_sleep
    sleep_allowed = resolve_sleep_allowed(sleep_allowed, None)
    injected = detect_autodrinks(rows, events) if detect_autodrink else []
    if injected:
        events = sorted(list(events or []) + injected, key=lambda e: e.get("s", 0))
    if paths is None:
        paths = list(ring_paths)
    off = estimate_offset(rows) if hour_offset is None else hour_offset
    if isinstance(start, dict) and "readAge" in start:
        start = dict(start)
        carried = start.pop("readAge")
        if start_read_age is None:
            start_read_age = carried
    sr = ServerReplay(start=start, user=user, player=player, steps=steps, hold_hour=hold_hour, hour_offset=off,
                      stats=start_stats, sleep_allowed=sleep_allowed, constants=constants, death_pace=death_pace,
                      health_combine=health_combine, day_minutes=day_minutes, game_heal=game_heal)
    sr.injected = injected
    if ring_activity is None:
        ring_activity = ring_carries_activity(rows)
    sr.ring_activity = []
    if ring_activity:
        for e in events or []:
            if e.get("kind") == "activity" and any(k in e for k in RING_ACTIVITY_KEYS):
                raise ValueError("an activity event naming %s while the activity comes from the ring's rate and exe: "
                                 "%r (pass ring_activity=False to keep the log's)" % (", ".join(RING_ACTIVITY_KEYS), e))
    if ring_cold is None:
        ring_cold = ring_carries_cold(rows)
    sr.ring_cold = []
    if ring_cold:
        for e in events or []:
            if e.get("kind") == "activity" and "cold" in e:
                raise ValueError("an activity event naming cold while the cold multiplier comes from the ring: %r "
                                 "(pass ring_cold=False to keep the log's)" % (e,))
    sa = sr.start_age()
    use = [r for r in rows if sa is None or r["age"] > sa + 1e-9]
    if not use:
        raise ValueError("no ring row after the start record's age %r" % sa)
    read = sa if start_read_age is None else float(start_read_age)
    if read is not None and sa is not None and read < sa - 1e-9:
        raise ValueError("the start record's read age %r precedes its own age %r" % (read, sa))
    straddle = read is not None and sa is not None and read > sa + 1e-12
    keep, sr.dropped = [], []
    for e in events or []:
        if straddle and "s" in e and e["s"] == use[0]["s"]:
            raise ValueError("an s-keyed event on ring row %r, the first after the start record, may precede its read "
                             "at %r: key it by age" % (e["s"], read))
        early = ("age" in e and read is not None and e["age"] <= read + 1e-12) or ("s" in e and e["s"] < use[0]["s"])
        (sr.dropped if early else keep).append(e)       # an event at or before the read is in the record already
    if ring_activity:
        sr.ring_activity = ring_activity_events(use)
        keep = keep + sr.ring_activity
    if ring_cold:
        sr.ring_cold = ring_cold_events(use)
        keep = keep + sr.ring_cold
    marks = link_marks(use)
    offline = [k for k, r in enumerate(use) if offline_row(r)]
    ages, seqs = [r["age"] for r in use], [r["s"] for r in use]
    keep, sr.spread = spread_drinks(keep, ages, seqs, sa, day_length, speed)
    out = run(sr, ages, keep, paths, start_age=sa, seqs=seqs, ring_rows=use, feed=feed, offline=offline)
    for k, row in enumerate(out):
        if k + 1 < len(use):
            nxt = use[k + 1]
            row["s"] = nxt["s"]
            for key in ("age", "dtM", "hour", "min"):
                if key in nxt:
                    row[key] = nxt[key]
            # a ring-derived activity event lands at its own row on the ring's own timing: no landing ambiguity
            row["between"] = out[k + 1]["events"] - out[k + 1]["ringEvents"] > 0
        else:
            row["s"] = use[k]["s"] + 1
            row["between"] = False
        for key, v in marks[k].items():
            if v:
                row[key] = True
    return out, sr


def replay_arm(events, start=None, ages=None, ring_rows=None, minutes=None, start_age=0.0, dtM=1.0, paths=(),
               backend="server", user="admin", player=None, steps=None, hour_offset=0.0, hold_hour=None, rng=None,
               M0=0.0, energy=True, satiety=True, hold_es=False, stats=None, sleep_allowed=None, sex_specific=False,
               constants=None, day_length=None, speed=1.0, death_pace=DEATH_PACE, health_combine=HEALTH_COMBINE,
               day_minutes=DAY_MINUTES, game_heal=False):
    """Mode arm: a substituted event list on the ring's clock (ring_rows) or a synthetic one (ages, or minutes from
    start_age at dtM). `constants` (the server backend's, set_constants; e.g. WORLD_CLOCK) and the drain options
    (`death_pace`, `health_combine`, `day_minutes`) and `game_heal` as ServerReplay takes them.
    `day_length` and `speed` spread each whole drink sip by sip (spread_drinks, named on backend.spread), as
    replay_live's do. Returns (rows, backend)."""
    synthetic = False
    if ages is None:
        if ring_rows is not None:
            ages = [r["age"] for r in ring_rows if r.get("age") is not None]
        else:
            ages = synthetic_ages(minutes, start_age, dtM)
            synthetic = True
    if backend == "oracle":
        be = OracleReplay(M0=M0, energy=energy, satiety=satiety, hold_es=hold_es, hold_hour=hold_hour is not None)
        sa = start_age
    else:
        be = ServerReplay(start=start, user=user, player=player, steps=steps, hold_hour=hold_hour,
                          hour_offset=hour_offset, rng=rng, stats=stats, sleep_allowed=sleep_allowed, sex_specific=sex_specific,
                          constants=constants, death_pace=death_pace, health_combine=health_combine,
                          day_minutes=day_minutes, game_heal=game_heal)
        sa = be.start_age()
        if sa is None:
            sa = start_age
    dtms = [float(dtM)] * len(ages) if synthetic else None
    events, be.spread = spread_drinks(events, ages, None, sa, day_length, speed)
    out = run(be, ages, events, paths, start_age=sa, dtms=dtms)
    for k, row in enumerate(out):
        row["s"] = k + 1
    return out, be


# --- the readings --------------------------------------------------------------------------------------------------

def diff(replay_rows, ring_rows, tol=None):
    """Replay rows against ring rows matched on s, under the tolerances {field: ("abs" | "rel", bound)}. A row with
    `between` (an event landed before it), `suspect` or `offline` set is not graded; a `gap` row is graded and its
    findings carry gap. A field compared on no row is itself a finding (n 0). Returns {fields: {field: {n, max, over,
    worst_s}}, findings, skipped (the between rows), suspect, offline, gap, classes: {gap, suspect, offline, between}
    (the counts), ok}."""
    tol = DEFAULT_TOL if tol is None else tol
    by_s = {r["s"]: r for r in ring_rows}
    fields = {f: {"n": 0, "max": 0.0, "over": 0, "worst_s": None} for f in tol}
    findings, skipped, suspect, offline, gap = [], [], [], [], []
    for r in replay_rows:
        live = by_s.get(r["s"])
        if live is None:
            continue
        if r.get("offline"):
            offline.append(r["s"])
            continue
        if r.get("suspect"):
            suspect.append(r["s"])
            continue
        if r.get("between"):
            skipped.append(r["s"])
            continue
        if r.get("gap"):
            gap.append(r["s"])
        for f, (how, bound) in tol.items():
            a, b = r.get(f), live.get(f)
            if not _num(a) or not _num(b):
                continue
            d = abs(a - b) if how == "abs" else (abs(a - b) / abs(a) if a != 0 else (0.0 if b == 0 else math.inf))
            st = fields[f]
            st["n"] += 1
            if d > st["max"]:
                st["max"], st["worst_s"] = d, r["s"]
            if d > bound:
                st["over"] += 1
                fd = {"s": r["s"], "field": f, "replay": a, "live": b, "d": d, "tol": [how, bound]}
                if r.get("gap"):
                    fd["gap"] = True
                findings.append(fd)
    for f, st in fields.items():
        if st["n"] == 0:
            findings.append({"field": f, "n": 0, "why": "compared on 0 rows"})
    classes = {"gap": len(gap), "suspect": len(suspect), "offline": len(offline), "between": len(skipped)}
    return {"fields": fields, "findings": findings, "skipped": skipped, "suspect": suspect, "offline": offline,
            "gap": gap, "classes": classes, "ok": not findings}


def request_minute(rows, after_age, level=H_REQ, field="HUNGER", fasted=False):
    """Minutes from after_age to the first row past it whose field is back at `level` (fasted: after it first fell
    below), as the oracles' request(); None if never."""
    seen_below = not fasted
    for r in rows:
        if r["age"] <= after_age + 1e-12 or r.get(field) is None:
            continue
        x = r[field]
        if not seen_below:
            if x < level - 1e-12:
                seen_below = True
            continue
        if x >= level - 1e-12:
            return (r["age"] - after_age) * 60
    return None


def intake_by_day(eats, day0_age=0.0):
    """kcal eaten per day from the eat log, day d holding the eats at ages [day0 + 24 d, day0 + 24 (d + 1))."""
    out = {}
    for e in eats:
        if e.get("kcal") is None:
            continue
        d = int(math.floor((e["age"] - day0_age) / 24.0 + 1e-12))
        out[d] = out.get(d, 0.0) + e["kcal"]
    return out


# --- the command line ---------------------------------------------------------------------------------------------

def _read_json(path):
    if path is None:
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="mode", required=True)
    for name in ("live", "arm"):
        p = sub.add_parser(name)
        p.add_argument("--ring", nargs="*", default=[])
        p.add_argument("--events", required=True,
                       help="the event list (JSON); an eat's kcal and fraction come from the item or from "
                            "lastIntake.frac, never from satiety.M")
        p.add_argument("--start")
        p.add_argument("--user", default="admin")
        p.add_argument("--player")
        p.add_argument("--paths", nargs="*")
        p.add_argument("--steps", nargs="*")
        p.add_argument("--hour-offset", type=float)
        p.add_argument("--hold-hour", type=float)
        p.add_argument("--out")
        p.add_argument("--day-length", type=int,
                       help="the server's sandbox DayLength index: spreads each drink flagged whole sip by sip "
                            "over its action's span (without it a whole drink lands in its minute); an unflagged "
                            "drink (a ring's per-sip log) lands as logged")
        p.add_argument("--speed", type=float, default=1.0,
                       help="the true time multiplier the drinks ran at (1 by default; getMultiplier is not it, #3762)")
        p.add_argument("--death-pace", type=int, choices=(1, 2, 3), default=DEATH_PACE,
                       help="the server's NR.DeathPace: 1 Vanilla, 2 Shortened, 3 Realistic (the default)")
        p.add_argument("--health-combine", type=int, choices=(1, 2, 3), default=HEALTH_COMBINE,
                       help="the server's NR.HealthCombine: 1 Worst only, 2 Multiply (the default), 3 Add")
        p.add_argument("--day-minutes", type=float, default=DAY_MINUTES,
                       help="the server's day length in real minutes (getDayLengthMinutes; 90 by default)")
        if name == "live":
            p.add_argument("--start-read-age", type=float,
                           help="the world age (hours) the start record was read at, logged by the driver: events "
                                "at or before it are dropped (the record holds them); without it the start record "
                                "must be read with no eat since the last drain")
            p.add_argument("--start-stats",
                           help="the stand-in's starting stats (JSON {stat: value}) logged by the driver; never "
                                "read from the ring")
            p.add_argument("--sleep-allowed", type=parse_bool,
                           help="REQUIRED (or sleepAllowed in the start document): the live server SleepAllowed and "
                                "SleepNeeded, true|false; false freezes the sleep state as live did")
            p.add_argument("--ring-activity", choices=("auto", "on", "off"), default="auto",
                           help="the activity from the ring's raw engine rate and exercise flag (auto: when the ring "
                                "carries them; Plan 11f C-17)")
            p.add_argument("--ring-cold", choices=("auto", "on", "off"), default="auto",
                           help="the thermoregulator's cold multiplier from the ring's cold field or body.coldMult "
                                "path, one row ahead (auto: when the ring carries it; Plan 16 Task 7)")
            p.add_argument("--detect-autodrink", action="store_true",
                           help="opt in: inject each unlogged liquid-lane rise in the ring as a drink event of its "
                                "water mass (the engine auto-drink, F-T4-2); named under `injected`")
        if name == "arm":
            p.add_argument("--minutes", type=int)
            p.add_argument("--start-age", type=float, default=0.0)
            p.add_argument("--backend", choices=("server", "oracle"), default="server")
    a = ap.parse_args(argv)
    rows, ring_paths = load_ring(a.ring) if a.ring else ([], [])
    events = _read_json(a.events)
    start = _read_json(a.start)
    player = _read_json(a.player)
    paths = a.paths if a.paths is not None else ring_paths
    if a.mode == "live":
        if not rows:
            ap.error("live needs --ring")
        if a.sleep_allowed is None and not (isinstance(start, dict) and "sleepAllowed" in start):
            ap.error("live needs --sleep-allowed true|false (or sleepAllowed in the start document): the live "
                     "server sleep option")
        out, be = replay_live(rows, events, start, paths=paths, user=a.user, player=player, steps=a.steps,
                              hour_offset=a.hour_offset, hold_hour=a.hold_hour, start_read_age=a.start_read_age,
                              start_stats=_read_json(a.start_stats), sleep_allowed=a.sleep_allowed,
                              detect_autodrink=a.detect_autodrink,
                              ring_activity={"auto": None, "on": True, "off": False}[a.ring_activity],
                              ring_cold={"auto": None, "on": True, "off": False}[a.ring_cold],
                              day_length=a.day_length, speed=a.speed, death_pace=a.death_pace,
                              health_combine=a.health_combine, day_minutes=a.day_minutes)
        d = diff(out, rows)
        offset = be.R.offset
    else:
        if not rows and a.minutes is None:
            ap.error("arm needs --ring or --minutes")
        out, be = replay_arm(events, start=start, ring_rows=rows or None, minutes=a.minutes, start_age=a.start_age,
                             paths=paths, backend=a.backend, user=a.user, player=player, steps=a.steps,
                             hour_offset=a.hour_offset or 0.0, hold_hour=a.hold_hour, day_length=a.day_length,
                             speed=a.speed, death_pace=a.death_pace, health_combine=a.health_combine,
                             day_minutes=a.day_minutes)
        d = diff(out, rows) if rows else None
        offset = a.hour_offset or 0.0
    doc = {"mode": a.mode, "offset": offset, "rows": out, "diff": d, "eats": be.eats,
           "injected": list(getattr(be, "injected", [])), "spread": list(getattr(be, "spread", []))}
    text = json.dumps(doc, indent=1, sort_keys=True)
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text + "\n")
    else:
        sys.stdout.write(text + "\n")
    if d is not None:
        c = d["classes"]
        print("replay_live: %s, %d finding(s), %d between, %d suspect, %d offline, %d gap"
              % ("ok" if d["ok"] else "FAIL", len(d["findings"]), c["between"], c["suspect"], c["offline"], c["gap"]),
              file=sys.stderr)
        return 0 if d["ok"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
