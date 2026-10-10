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
  before-snapshot, so the declared-nutrients chain, the landing, the P feed and monotony are the mod's; a raw vector
  through IN.land and IN.atEat; a drink through IN.fluidVector and IN.land's liquid lane. The start record is placed
  in the store's records table and loaded by the store's own first-sight load (K.store.load: the inputs kept, the
  derived fields rebuilt), as after a restart.
- `oracle` (`OracleReplay`): the satiety oracles' own kernel composition, one minute a step
  (test_satiety_meal_studies.py's REPLAY, ENERGY_REPLAY and SIX_LIVE_REPLAY: the stomach and pool, the 70 kg man's
  trailing-24 h energy path, the hunger function), driven by the same event lists. It exists so the event engine
  can be checked against the oracles' pins where they step kernels directly, and so a live run's distance from the
  oracle's 70 kg man can be named (ruling 11f-4).

Events are a JSON list. Each is due at `age` (game hours: applied before the first drain at or after it, at that
age), at `s` (applied before the drain of ring row s, at its age: the landing a ring path such as
`_G.NutritionRevamp.server.intake.stats.eats` first shows), or at `minute` m of a synthetic clock (applied before
step m, at its start). Kinds:
  eat      {food | fullType+cal+carb+lip+pro+hunger+declared+foodType, frac (default 1)} or {vec, lane, fullType}
  drink    {fluid, litres} or {vec}: the liquid lane
  meal     {size: "maint" | "request" | kcal, comp: {p, c, f}, food, sate}: an energy-oracle meal; "request" eats
           650 kcal x min(0.69, hungerTarget(0.75, es) x circadian(hour)) / 0.25 (the oracles' intake mapping,
           ruling 11c-31; research section 3.7 form 1), es the state the last drain left and hour the event's
  sleep    {asleep}
  activity {rate, moving, exercising}: the engine MET the thermoregulator answers, and the flags
  stat     {stat, value}: the stand-in's stat
  setpath  {path, value}: a record path (lua.read grammar)
  trait    {trait, on}
Mode "live" uses the ring's clock and feeds the stand-in's NICOTINE_WITHDRAWAL from each ring row before its drain
(the engine owns that stat and the writer reads it); mode "arm" substitutes another event list (ruling 11f-3), on the
ring's clock or a synthetic one, and feeds nothing the arm does not name.

    python tools/replay_live.py live --ring PAGE.json [PAGE.json ...] --events EV.json --start START.json
                                     [--user admin] [--player CFG.json] [--out OUT.json]
    python tools/replay_live.py arm  --events EV.json [--start START.json] (--ring PAGE.json ... |
                                     --minutes N [--start-age A]) [--backend server|oracle] [--out OUT.json]

The start record is a slot file's JSON ({gen, rec, done}), the record itself, or an H1 `lua.read` reply
({values: {path: value}}). Output: {rows, diff, eats, offset, mode}; the diff grades HUNGER within 0.002, es
(body.energyState) within 0.005 and satiety.L within 0.5 % (the plan's pre-registered tolerances) and skips every
row an event landed before (vanilla's own eat moves HUNGER between writes). Exits 1 when the diff has a finding.
"""
import argparse
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
KERNEL_TESTS = os.path.join(REPO, "testing", "tests", "kernel")
STUDY_SCRIPT = os.path.join(REPO, "testing", "experiments", "TKX_StudyFoods", "common", "media", "scripts",
                            "tkx_study_foods.txt")

STATS = ("HUNGER", "THIRST", "FATIGUE", "BOREDOM", "UNHAPPINESS", "NICOTINE_WITHDRAWAL")
H_REQ = 0.25                          # the meal request, vanilla's HUNGRY level 2 (ruling 11c-17)
KCAL_PER_H = 650.0 / H_REQ            # the intake mapping (ruling 11c-31): kcal per unit of written hunger
NEUTRAL_HOUR = 13.8333                # circadian(13:50) is 1.0 exactly: the factor held (the oracles' h0 None)
DEFAULT_FEED = ("NICOTINE_WITHDRAWAL",)
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
-- the replay's own control of a decorated stand-in: asleep, moving, a Fitness exercise, the engine MET
function NR_R.adopt(p, name, rate, inv, maxW)
    local u = { asleep = false, rate = rate, moving = false, exercising = false }
    NR_R.u[name] = u
    p.isAsleep = function(s) return u.asleep end
    p.isPlayerMoving = function(s) return u.moving end
    local fitness = { getCurrentExe = function(s) if u.exercising then return "exercise" end return nil end }
    p.getFitness = function(s) return fitness end
    local th = p:getBodyDamage():getThermoregulator()
    local f = math.min(math.max(inv / maxW, 0), 1)
    th.getMetabolicRate = function(s) return u.rate * (1 + 0.35 * f * f) end
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
-- a vector landed as the intake lands one (IN.land), monotony booked for a food lane's type (IN.atEat)
function NR_R.landVec(user, src, lane, fullType, foodType)
    local NR = NutritionRevamp
    local K = NR.kernel
    local rec = NR_R.record(user)
    local v = K.vector.new()
    for k, x in pairs(src) do v[k] = x end
    NR.server.intake.land(rec, user, v, lane)
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
    return KCAL_PER_H * K.min(0.69, K.hybrid.hungerTarget(1 - H_REQ, es) * K.satiety.circadian(hod))
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

ORACLE_LUA = r"""
NR_O = {}
function NR_O.new(P0, energy, satiety, holdEs, holdHour)
    local K = NutritionRevamp.kernel
    local o = { P = P0, es = 1, L = 0, eb24 = 0, hunger = nil, energy = energy, satiety = satiety, holdEs = holdEs,
                holdHour = holdHour, asleep = false }
    o.st = K.stomach.new()
    o.body = K.body.new(70, 1, {}, 5, 1, 1, 0)       -- the energy oracles' 70 kg man
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
        o.P = K.satiety.feed(o.P, u)
        if lane == "liquid" then K.stomach.ingestLiquid(o.st, u) else K.stomach.ingest(o.st, u) end
    end
end
function NR_O.requestKcal(o, ageStart, H_REQ, KCAL_PER_H)
    local K = NutritionRevamp.kernel
    local c = 1
    local hod = NR_O.tod(o, ageStart)
    if hod ~= nil then c = K.satiety.circadian(hod) end
    return KCAL_PER_H * K.min(0.69, K.hybrid.hungerTarget(1 - H_REQ, o.es) * c)
end
function NR_O.minute(o, ageH, dtM)
    local K = NutritionRevamp.kernel
    if o.energy then
        local body = o.body
        local met = K.energy.COMPENDIUM.Default
        if o.asleep then met = K.energy.COMPENDIUM.Sleeping end
        local ex0 = body.exKcalDay
        K.energy.minute(body, met, true, 1, dtM)
        o.L = K.energy.exerciseLag(o.L, body.exKcalDay - ex0, dtM / 60)
        if math.floor(ageH / 24) > body.dayIndex then
            body.inDayClosed = body.inDay
            K.partition.closeDay(body)
        end
        local ee24 = K.max(K.body.trail24(body.trail, "ee"), K.energy.ree(body.lm))
        local ex24 = K.body.trail24(body.trail, "ex")
        o.eb24 = K.energy.eb24h(body)
        o.es = K.energy.activityState(o.eb24, ex24, o.L, 0, ee24)
    end
    if o.satiety then
        local dtH = dtM / 60
        K.stomach.drain(o.st, dtH)
        o.P = K.satiety.decay(o.P, dtH, K.satiety.HALF_LIFE_H, 1)
        local F = K.satiety.fill(K.stomach.fullnessMass(o.st), K.stomach.CAPACITY_MAX_G)
        local x = o.es
        if o.holdEs then x = 1 end
        local c = 1
        local hod = NR_O.tod(o, ageH)
        if hod ~= nil then c = K.satiety.circadian(hod) end
        o.hunger = K.min(0.69, K.hybrid.hungerTarget(K.satiety.sated(F, K.satiety.post(o.P)), x) * c)
    end
    o.rec.satiety.P = o.P
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


class ServerReplay(_Backend):
    """The mod's server adapters on server_host.Host with the golden stand-ins (see the module docstring)."""

    def __init__(self, start=None, user="admin", player=None, steps=None, hold_hour=None, hour_offset=0.0,
                 rng=None, stats=None):
        super().__init__()
        lua51, server_host, golden_trace = _lua()
        self.lua51 = lua51
        self.h = server_host.Host(extra_env=golden_trace.ENV + REPLAY_ENV)
        self.rt = self.h.rt
        self.G = self.h.G
        self.NR = self.h.NR
        self.K = self.h.K
        self.R = self.G.NR_R
        self.R.offset = float(hour_offset or 0.0)
        if hold_hour is not None:
            self.R.holdHour = float(hold_hour)
        if rng == "half":                                   # the responder constant reads 1 (z = 0)
            self.rt.execute("ZombRandFloat = function(lo, hi) return lo + (hi - lo) * 0.5 end")
        if steps is not None:
            self.NR.server.minute.ORDER = self.rt.table(*steps)
        self.users = {}
        self.user = None
        self.maint_kcal = None
        self.add_user(user, start, player, stats)

    def add_user(self, user, start=None, player=None, stats=None):
        """A stand-in player for `user`, online alone, with `start` placed in the store's records."""
        cfg = {"rate": None, "inv": 0.0, "maxW": 8.0, "traits": [], "female": False, "weight": 80.0,
               "macros": (1000.0, 100.0, 40.0, 60.0)}
        cfg.update(player or {})
        p = self.h.player(user, *cfg["macros"])
        p.nut.weight = cfg["weight"]
        lcfg = self.rt.table()
        lcfg.rate = 1.0
        lcfg.inv = cfg["inv"]
        lcfg.maxW = cfg["maxW"]
        lcfg.traits = self.rt.table(*cfg["traits"])
        lcfg.female = bool(cfg["female"])
        sv = {"HUNGER": 0.2, "THIRST": 0.1, "FATIGUE": 0.1}
        sv.update(stats or {})
        lcfg.hunger, lcfg.thirst, lcfg.fatigue = sv["HUNGER"], sv["THIRST"], sv["FATIGUE"]
        p = self.G.NR_T.decorate(p, lcfg)
        rate = cfg["rate"] if cfg["rate"] is not None else self.K.energy.COMPENDIUM.Default
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
        else:
            comp = ev.get("comp", MIXED)
            vec = self.R.mealVec(kcal, comp["p"], comp["c"], comp["f"])
            vec = self.R.landVec(self.user, vec, None, None, None)
        self._log(at, "meal", ev.get("food"), vec, b0)

    def ev_sleep(self, ev, at):
        self.R.u[self.user].asleep = bool(ev["asleep"])

    def ev_activity(self, ev, at):
        u = self.R.u[self.user]
        if "rate" in ev:
            u.rate = float(ev["rate"])
        if "moving" in ev:
            u.moving = bool(ev["moving"])
        if "exercising" in ev:
            u.exercising = bool(ev["exercising"])

    def ev_stat(self, ev, at):
        self.p.sv[ev["stat"]] = ev["value"]

    def ev_trait(self, ev, at):
        key = self.G.CharacterTrait[ev["trait"]]
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
        out = {"on": True}
        for n in STATS:
            v = self.p.sv[n]
            if v is not None:
                out[n] = v
        r = self.record()
        for path in paths:
            segs, glob = parse_path(path)
            ok, v = walk(self.lua51, self.G if glob else r, segs)
            if ok:
                out[path] = _scalar(self.lua51, v)
        return out


class OracleReplay(_Backend):
    """The oracles' kernel composition (see the module docstring); HUNGER is the displayed hunger, and the paths
    satiety.P, satiety.L, body.energyState and body.eb24 read its state."""

    ALIAS = {"body.energyState": "es", "body.eb24": "eb24", "satiety.P": "P", "satiety.L": "L"}

    def __init__(self, P0=0.0, energy=True, satiety=True, hold_es=False, hold_hour=False):
        super().__init__()
        lua51, server_host, _ = _lua()
        self.lua51 = lua51
        self.rt = lua51.LuaRuntime(unpack_returned_tuples=True)
        self.rt.execute(server_host.ENV)
        for p in server_host._shared_files():
            server_host._load(self.rt, p)
        self.rt.execute(ORACLE_LUA)
        self.G = self.rt.globals()
        self.O = self.G.NR_O
        self.o = self.O.new(float(P0), bool(energy), bool(satiety), bool(hold_es), bool(hold_hour))

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


def run(backend, ages, events, paths=(), start_age=None, seqs=None, ring_rows=None, feed=(), dtms=None):
    """Steps `backend` one drain per age in `ages`. Before drain k: the events due (see the module docstring), then
    the stats `feed` names from ring_rows[k]. Returns one row per drain: the state the drain left, with its clock
    (age, dtM, hour, min), `k`, and `events`, the count of events applied before it."""
    evs = list(events or [])
    for e in evs:
        if not any(x in e for x in ("age", "s", "minute")):
            raise ValueError("an event without age, s or minute: %r" % (e,))
    done = [False] * len(evs)
    out = []
    prev = start_age
    for k, age in enumerate(ages):
        seq = seqs[k] if seqs is not None else None
        backend.begin(age)
        n = 0
        for i, e in enumerate(evs):
            if not done[i] and _due(e, k, prev, age, seq):
                backend.apply(e, _event_age(e, prev, age))
                done[i] = True
                n += 1
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
        out.append(row)
        prev = age
    left = [e for i, e in enumerate(evs) if not done[i]]
    if left:
        raise ValueError("%d event(s) never fell due, the first %r" % (len(left), left[0]))
    return out


def synthetic_ages(minutes, start_age=0.0, dtM=1.0):
    """A synthetic clock: step m ends at start_age + (m + 1) x dtM / 60 (the oracles' minute m)."""
    return [start_age + (m + 1) * dtM / 60.0 for m in range(minutes)]


def replay_live(ring_rows, events, start, paths=None, user="admin", player=None, feed=DEFAULT_FEED, steps=None,
                hour_offset=None, hold_hour=None, ring_paths=()):
    """Mode live: the ring's clock and the live event log from the start record on (ring rows at or before the start
    record's age, and events at or before it, are dropped: the record holds them; the dropped events are kept on
    backend.dropped). Returns (rows, backend); replay row k is the state drain k left, labelled s = ring row k's s + 1
    and carrying that row's clock when it exists, and `between` set when an event fell due before drain k + 1 (it
    landed between drain k and ring row k + 1)."""
    rows = [r for r in ring_rows if r.get("age") is not None]
    if paths is None:
        paths = list(ring_paths)
    off = estimate_offset(rows) if hour_offset is None else hour_offset
    stats0 = {}
    sr = ServerReplay(start=start, user=user, player=player, steps=steps, hold_hour=hold_hour, hour_offset=off)
    sa = sr.start_age()
    use = [r for r in rows if sa is None or r["age"] > sa + 1e-9]
    if not use:
        raise ValueError("no ring row after the start record's age %r" % sa)
    for n in STATS:
        if use[0].get(n) is not None:
            stats0[n] = use[0][n]
    for n, v in stats0.items():
        sr.p.sv[n] = v
    keep, sr.dropped = [], []
    for e in events or []:
        early = ("age" in e and sa is not None and e["age"] <= sa + 1e-12) or ("s" in e and e["s"] < use[0]["s"])
        (sr.dropped if early else keep).append(e)       # an event at or before the start record is in it already
    out = run(sr, [r["age"] for r in use], keep, paths, start_age=sa, seqs=[r["s"] for r in use],
              ring_rows=use, feed=feed)
    for k, row in enumerate(out):
        row["s"] = use[k]["s"] + 1
        if k + 1 < len(use):
            nxt = use[k + 1]
            for key in ("age", "dtM", "hour", "min"):
                if key in nxt:
                    row[key] = nxt[key]
            row["between"] = out[k + 1]["events"] > 0
        else:
            row["between"] = False
    return out, sr


def replay_arm(events, start=None, ages=None, ring_rows=None, minutes=None, start_age=0.0, dtM=1.0, paths=(),
               backend="server", user="admin", player=None, steps=None, hour_offset=0.0, hold_hour=None, rng=None,
               P0=0.0, energy=True, satiety=True, hold_es=False, stats=None):
    """Mode arm: a substituted event list on the ring's clock (ring_rows) or a synthetic one (ages, or minutes from
    start_age at dtM). Returns (rows, backend)."""
    synthetic = False
    if ages is None:
        if ring_rows is not None:
            ages = [r["age"] for r in ring_rows if r.get("age") is not None]
        else:
            ages = synthetic_ages(minutes, start_age, dtM)
            synthetic = True
    if backend == "oracle":
        be = OracleReplay(P0=P0, energy=energy, satiety=satiety, hold_es=hold_es, hold_hour=hold_hour is not None)
        sa = start_age
    else:
        be = ServerReplay(start=start, user=user, player=player, steps=steps, hold_hour=hold_hour,
                          hour_offset=hour_offset, rng=rng, stats=stats)
        sa = be.start_age()
        if sa is None:
            sa = start_age
    dtms = [float(dtM)] * len(ages) if synthetic else None
    out = run(be, ages, events, paths, start_age=sa, dtms=dtms)
    for k, row in enumerate(out):
        row["s"] = k + 1
    return out, be


# --- the readings --------------------------------------------------------------------------------------------------

def diff(replay_rows, ring_rows, tol=None):
    """Replay rows against ring rows matched on s, under the tolerances {field: ("abs" | "rel", bound)}. A row with
    `between` set is skipped. Returns {fields: {field: {n, max, over, worst_s}}, findings, skipped, ok}."""
    tol = DEFAULT_TOL if tol is None else tol
    by_s = {r["s"]: r for r in ring_rows}
    fields = {f: {"n": 0, "max": 0.0, "over": 0, "worst_s": None} for f in tol}
    findings, skipped = [], []
    for r in replay_rows:
        live = by_s.get(r["s"])
        if live is None:
            continue
        if r.get("between"):
            skipped.append(r["s"])
            continue
        for f, (how, bound) in tol.items():
            a, b = r.get(f), live.get(f)
            if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) or isinstance(a, bool):
                continue
            d = abs(a - b) if how == "abs" else (abs(a - b) / abs(a) if a != 0 else (0.0 if b == 0 else math.inf))
            st = fields[f]
            st["n"] += 1
            if d > st["max"]:
                st["max"], st["worst_s"] = d, r["s"]
            if d > bound:
                st["over"] += 1
                findings.append({"s": r["s"], "field": f, "replay": a, "live": b, "d": d, "tol": [how, bound]})
    return {"fields": fields, "findings": findings, "skipped": skipped, "ok": not findings}


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
        p.add_argument("--events", required=True)
        p.add_argument("--start")
        p.add_argument("--user", default="admin")
        p.add_argument("--player")
        p.add_argument("--paths", nargs="*")
        p.add_argument("--steps", nargs="*")
        p.add_argument("--hour-offset", type=float)
        p.add_argument("--hold-hour", type=float)
        p.add_argument("--out")
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
        out, be = replay_live(rows, events, start, paths=paths, user=a.user, player=player, steps=a.steps,
                              hour_offset=a.hour_offset, hold_hour=a.hold_hour)
        d = diff(out, rows)
        offset = be.R.offset
    else:
        if not rows and a.minutes is None:
            ap.error("arm needs --ring or --minutes")
        out, be = replay_arm(events, start=start, ring_rows=rows or None, minutes=a.minutes, start_age=a.start_age,
                             paths=paths, backend=a.backend, user=a.user, player=player, steps=a.steps,
                             hour_offset=a.hour_offset or 0.0, hold_hour=a.hold_hour)
        d = diff(out, rows) if rows else None
        offset = a.hour_offset or 0.0
    doc = {"mode": a.mode, "offset": offset, "rows": out, "diff": d, "eats": be.eats}
    text = json.dumps(doc, indent=1, sort_keys=True)
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text + "\n")
    else:
        sys.stdout.write(text + "\n")
    if d is not None:
        print("replay_live: %s, %d finding(s), %d row(s) skipped" % ("ok" if d["ok"] else "FAIL", len(d["findings"]),
                                                                   len(d["skipped"])), file=sys.stderr)
        return 0 if d["ok"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
