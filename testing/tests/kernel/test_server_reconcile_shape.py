"""The server adapters of Plan 8 Task 4: NR_Server_Reconcile.lua (the missed-intake minute), the store's load at
first sight (NR_Server_Store.lua, ruling T4-1), the Weight adapter's baseline reset and band mark, the intake's
wrapped-eat credit, the bus's markBand and Metabolism's unset closed day.

Every test runs in a FRESH Lua 5.1 runtime: NR_Core.lua, the shared data and kernel files, then every server/
file in the engine's load order (alphabetical), with Lua stand-ins for the engine -- an Events table whose Add
records each listener, isServer, getGameTime, print captured, and a player whose getNutrition answers a
Nutrition stand-in holding the four macro stores. Nothing here runs in the session host, so its coverage gate is
untouched (the kernel's own fillInPlace is covered in test_kernel_store.py). A stub proves the wiring, the order
and the arithmetic, never the engine: whether another mod's write reaches the stores between two slow minutes is
the live arm's (x193 D).
"""
import glob
import os

import lupa.lua51 as lua51
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LUA = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua")
SHARED = os.path.join(LUA, "shared")
SERVER = os.path.join(LUA, "server")
TOL = 1e-6

ENV = r"""
NR_T = { adds = {}, printed = {}, age = 100.0, server = true }
local function event(name)
    NR_T.adds[name] = {}
    return { Add = function(fn) local l = NR_T.adds[name]; l[#l + 1] = fn end,
             Remove = function(fn) end }
end
Events = {}
for _, n in ipairs({ "OnServerStarted", "OnInitGlobalModData", "EveryOneMinute", "EveryTenMinutes", "OnTick",
                     "OnNewGame", "OnClientCommand", "AddXP", "OnWeaponHitXp", "OnWeaponHitTree",
                     "OnGameStart", "OnServerCommand", "OnPlayerUpdate" }) do
    Events[n] = event(n)
end
isServer = function() return NR_T.server end
isClient = function() return false end
getGameTime = function()
    return { getWorldAgeHours = function(s) return NR_T.age end,
             getTimeOfDay = function(s) return math.fmod(NR_T.age, 24) end }
end
print = function(s) NR_T.printed[#NR_T.printed + 1] = tostring(s) end
"""

# A player: getNutrition answers a Nutrition stand-in whose four macro stores are plain fields (the getters read
# them, the setters write them and count), plus the weight members the Weight adapter calls.
PLAYER = r"""
function(name, cal, carb, lip, pro)
    local nut = { cal = cal, carb = carb, lip = lip, pro = pro, weight = 80, sets = 0, traitApplies = 0 }
    nut.getCalories = function(s) return s.cal end
    nut.getCarbohydrates = function(s) return s.carb end
    nut.getLipids = function(s) return s.lip end
    nut.getProteins = function(s) return s.pro end
    nut.setCalories = function(s, v) s.cal = v; s.sets = s.sets + 1 end
    nut.setCarbohydrates = function(s, v) s.carb = v; s.sets = s.sets + 1 end
    nut.setLipids = function(s, v) s.lip = v; s.sets = s.sets + 1 end
    nut.setProteins = function(s, v) s.pro = v; s.sets = s.sets + 1 end
    nut.getWeight = function(s) return s.weight end
    nut.setWeight = function(s, v) s.weight = v end
    nut.setIncWeight = function(s, v) end
    nut.setIncWeightLot = function(s, v) end
    nut.setDecWeight = function(s, v) end
    nut.applyTraitFromWeight = function(s) s.traitApplies = s.traitApplies + 1 end
    local p = { nut = nut }
    p.getUsername = function(s) return name end
    p.getNutrition = function(s) return nut end
    p.isDead = function(s) return false end
    p.isFemale = function(s) return false end
    return p
end
"""


def _load(rt, path):
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@" + os.path.basename(path))()


def _shared_files():
    core = os.path.join(SHARED, "NR_Core.lua")
    rest = sorted(p for p in glob.glob(os.path.join(SHARED, "NR_*.lua")) if p != core)
    return [core] + rest


class Host:
    def __init__(self):
        self.rt = lua51.LuaRuntime(unpack_returned_tuples=True)
        self.rt.execute(ENV)
        for p in _shared_files():
            _load(self.rt, p)
        for p in sorted(glob.glob(os.path.join(SERVER, "NR_Server_*.lua"))):
            _load(self.rt, p)
        self.G = self.rt.globals()
        self.NR = self.G.NutritionRevamp
        self.K = self.NR.kernel
        self.T = self.G.NR_T
        # the store attaches offline once its records table is pre-set (as test_intake_shape.py does)
        self.NR.server.store.records = self.rt.table()
        for fn in self.T.adds["OnServerStarted"].values():
            fn()

    def player(self, name="admin", cal=1000.0, carb=100.0, lip=40.0, pro=60.0):
        return self.rt.eval(PLAYER)(name, cal, carb, lip, pro)

    def table(self, d):
        t = self.rt.table()
        for k, v in d.items():
            t[k] = self.table(v) if isinstance(v, dict) else v
        return t

    def printed(self):
        return list(self.T.printed.values())

    def first_sight(self, player, name="admin"):
        """The players' walk sees the player for the first time (P.minute with one online player)."""
        self.G.getOnlinePlayers = self.rt.eval(
            "function(p) return function() return { size = function(s) return 1 end, get = function(s, i) return p end } end end")(player)
        P = self.NR.server.players
        P.minute()
        sp = P.sight[name]
        if sp is not None:                    # Plan 11 Task 9: the minute marks the sight; its queue slot runs it
            P.sight[name] = None
            P.firstSight(name, sp)
        return self.NR.server.store.records[name]


@pytest.fixture
def h():
    return Host()


def RC(h):
    return h.NR.server.reconcile


def macros(t):
    return {k: t[k] for k in ("calories", "carbs", "lipids", "proteins")}


def seeded(h, cal=1000.0, carb=100.0, lip=40.0, pro=60.0):
    p = h.player(cal=cal, carb=carb, lip=lip, pro=pro)
    rec = h.first_sight(p)
    return p, rec


# --- the wiring: the minute order --------------------------------------------------------------------

def test_the_reconciliation_runs_before_kinetics_nutrients_and_the_weight_write(h):
    # the pipeline's declared ORDER (Plan 10 R2), the same order 1.0.0's splice into P.onMinute produced
    M = h.NR.server.minute
    srv = h.NR.server
    same = h.rt.eval("rawequal")
    order = [M.ORDER[i] for i in range(1, len(M.ORDER) + 1)]
    idx = {}
    for name in ("reconcile", "kinetics", "metabolism", "nutrients", "strength", "weight"):
        assert same(M.steps[name], getattr(srv, name).minute), name
        assert order.count(name) == 1, name
        idx[name] = order.index(name)
    assert idx["reconcile"] < idx["kinetics"] < idx["metabolism"] < idx["nutrients"] < idx["strength"] < idx["weight"]
    assert same(M.steps["bus"], srv.bus.flushEffects) and order.index("bus") < idx["reconcile"]
    assert len(srv.players.onMinute) == 0


def test_the_first_sight_seeds_the_baseline_from_the_stores(h):
    p, rec = seeded(h, cal=1234.5, carb=77.0, lip=12.0, pro=33.0)
    rc = rec["reconcile"]
    assert rc["count"] == 0
    assert macros(rc["baseline"]) == {"calories": 1234.5, "carbs": 77.0, "lipids": 12.0, "proteins": 33.0}


# --- the reconciliation minute -----------------------------------------------------------------------

def test_a_rise_with_no_wrapped_eat_lands_the_macros_only(h):
    p, rec = seeded(h)
    nut = p.nut
    nut.cal, nut.carb = 1300.0, 120.0
    before = {k: rec["stomach"]["buffer"][k] if rec["stomach"] is not None else 0 for k in ("calories", "carbs", "vitC")} \
        if rec["stomach"] is not None else {"calories": 0, "carbs": 0, "vitC": 0}
    RC(h).minute("admin", p, rec)
    li = rec["lastIntake"]
    assert li["source"] == "reconciled"
    assert li["note"] == h.K.reconcile.NOTE == "reconciled: macros only, nutrient vector unknown"
    assert abs(li["calories"] - 300) < TOL and abs(li["carbs"] - 20) < TOL
    assert li["lipids"] == 0 and li["proteins"] == 0
    buf = rec["stomach"]["buffer"]
    assert abs(buf["calories"] - before["calories"] - 300) < TOL
    assert abs(buf["carbs"] - before["carbs"] - 20) < TOL
    assert buf["vitC"] == before["vitC"]
    assert rec["reconcile"]["count"] == 1
    assert macros(rec["reconcile"]["baseline"]) == {"calories": 1300.0, "carbs": 120.0, "lipids": 40.0, "proteins": 60.0}
    assert RC(h).stats.landed == 1
    assert abs(h.NR.server.intake.lastIngested["admin"]["calories"] - 300) < TOL
    assert rec["stomach"]["liquid"] == 0                                 # J4: a reconciled intake reaches the solid buffer, macros only


def test_a_reconciled_rise_feeds_the_pool_by_its_weighed_kcal(h):
    # amendment 1: the reconcile path lands through IN.land, which feeds P with the delivered vector; 300 kcal of
    # 20 g carbohydrate alone takes the carbohydrate weight 1 (W_CARB), so P rises by 300 weighted kcal
    p, rec = seeded(h)
    rec.satiety = h.rt.eval("{ P = 2, S = 0, L = 0 }")
    p.nut.cal, p.nut.carb = 1300.0, 120.0
    RC(h).minute("admin", p, rec)
    assert abs(rec["satiety"]["P"] - (2 + 300)) < TOL
    p.nut.cal, p.nut.pro = 1400.0, 85.0                                  # 100 kcal more with 25 g protein
    RC(h).minute("admin", p, rec)
    assert abs(rec["satiety"]["P"] - (302 + 100 * 2.5)) < TOL            # all protein: weight 2.5 (W_PROTEIN)


def test_the_same_rise_is_not_landed_twice(h):
    p, rec = seeded(h)
    p.nut.cal = 1300.0
    RC(h).minute("admin", p, rec)
    RC(h).minute("admin", p, rec)
    assert rec["reconcile"]["count"] == 1


def test_a_fall_lands_nothing_and_resets_the_baseline(h):
    p, rec = seeded(h)
    p.nut.cal, p.nut.carb = 700.0, 80.0
    RC(h).minute("admin", p, rec)
    assert rec["lastIntake"] is None
    assert rec["reconcile"]["count"] == 0
    assert rec["reconcile"]["baseline"]["calories"] == 700.0
    assert RC(h).stats.skipped == 1


def test_a_rise_within_eps_lands_nothing(h):
    p, rec = seeded(h)
    p.nut.cal = 1000.0 + h.K.reconcile.RECONCILE_EPS * 0.8
    RC(h).minute("admin", p, rec)
    assert rec["reconcile"]["count"] == 0 and rec["lastIntake"] is None


def test_an_unreadable_store_skips_the_minute(h):
    p, rec = seeded(h)
    p.nut.cal = "x"
    RC(h).minute("admin", p, rec)
    assert rec["reconcile"]["count"] == 0
    assert RC(h).stats.noStore == 1
    assert rec["reconcile"]["baseline"]["calories"] == 1000.0


def test_a_record_with_no_baseline_is_seeded_not_landed(h):
    p, rec = seeded(h)
    rec["reconcile"] = None
    p.nut.cal = 5000.0
    RC(h).minute("admin", p, rec)
    assert rec["reconcile"]["count"] == 0 and rec["reconcile"]["baseline"]["calories"] == 5000.0
    assert rec["lastIntake"] is None


def test_a_raising_store_read_is_counted_never_raised(h):
    p, rec = seeded(h)
    p.nut.getCalories = h.rt.eval("function(s) error('boom') end")
    RC(h).minute("admin", p, rec)
    assert RC(h).stats.errors == 1


def test_the_limitations_name_the_macros_only_rule_and_the_precondition(h):
    lim = list(RC(h).limitations.values())
    assert any("macros only" in s for s in lim)
    assert any("Nutrition = false" in s for s in lim)
    assert any("baseline" in s for s in lim)


# --- the wrapped eat: the engine's own store write inside the wrap is credited to the baseline ---------

EAT = r"""
function(player, dcal, dcarb)
    local IN = NutritionRevamp.server.intake
    local hung = -0.16
    local item = {}
    item.getHungChange = function(self) return hung end
    item.getFullType = function(self) return "Base.Apple" end
    item.getBaseHunger = function(self) return -0.16 end
    item.getCalories = function(self) return dcal end
    item.getCarbohydrates = function(self) return dcarb end
    item.getLipids = function(self) return 0 end
    item.getProteins = function(self) return 0 end
    item.isCooked = function(self) return false end
    item.isBurnt = function(self) return false end
    item.isRotten = function(self) return false end
    item.isFrozen = function(self) return false end
    item.getThirstChangeUnmodified = function(self) return 0 end
    item.haveExtraItems = function(self) return false end
    item.getModData = function(self) return {} end
    item.getScriptItem = function(self)
        return { getHungerChange = function(s) return -16 end, getThirstChange = function(s) return 0 end }
    end
    local cls = {}
    -- the engine's Eat: the stores rise by the eaten macros inside the original
    cls.complete = function(self)
        hung = 0
        local n = player:getNutrition()
        n.cal = n.cal + dcal
        n.carb = n.carb + dcarb
        return true
    end
    cls.serverStop = function(self) end
    ISEatFoodAction = cls
    IN.install()
    return cls.complete({ item = item, character = player })
end
"""


def test_a_rise_from_a_wrapped_eat_is_not_reconciled(h):
    p, rec = seeded(h)
    h.NR.data.nutrients = h.table({})
    h.NR.data.nutrients.get = h.rt.eval("function(t) return nil end")
    assert h.rt.eval(EAT)(p, 95.0, 25.0) is True
    assert rec["lastIntake"]["source"] != "reconciled"
    assert abs(rec["reconcile"]["baseline"]["calories"] - 1095.0) < TOL
    assert abs(rec["reconcile"]["baseline"]["carbs"] - 125.0) < TOL
    RC(h).minute("admin", p, rec)
    assert rec["reconcile"]["count"] == 0
    assert rec["lastIntake"]["source"] != "reconciled"


def test_a_missed_intake_beside_a_wrapped_eat_is_still_reconciled(h):
    p, rec = seeded(h)
    h.NR.data.nutrients = h.table({})
    h.NR.data.nutrients.get = h.rt.eval("function(t) return nil end")
    p.nut.cal = p.nut.cal + 200.0          # another mod's write before the eat, the same minute
    h.rt.eval(EAT)(p, 95.0, 25.0)
    RC(h).minute("admin", p, rec)
    assert rec["reconcile"]["count"] == 1
    assert abs(rec["lastIntake"]["calories"] - 200.0) < TOL


# --- the Weight adapter: the legacy write resets the baseline; the band mark ---------------------------

def _body(h, rec, fm=15.0, lm=65.0):
    body = h.K.body.new(80.0, 1, h.table({}), 5, 1.0, 1.0, h.T.age)
    body["fm"], body["lm"] = fm, lm
    rec["body"] = body
    return body


def test_legacy_mirror_on_the_write_becomes_the_baseline(h):
    p, rec = seeded(h)
    _body(h, rec)
    h.NR.server.options.legacyMirror = True
    h.NR.server.weight.minute("admin", p, rec)
    assert p.nut.sets == 4
    bl = macros(rec["reconcile"]["baseline"])
    assert bl == {"calories": p.nut.cal, "carbs": p.nut.carb, "lipids": p.nut.lip, "proteins": p.nut.pro}
    RC(h).minute("admin", p, rec)
    assert rec["reconcile"]["count"] == 0


def test_legacy_mirror_off_keeps_the_observed_baseline(h):
    p, rec = seeded(h)
    _body(h, rec)
    h.NR.server.options.legacyMirror = False
    h.NR.server.weight.minute("admin", p, rec)
    assert p.nut.sets == 0
    assert rec["reconcile"]["baseline"]["calories"] == 1000.0
    p.nut.cal = 1300.0
    RC(h).minute("admin", p, rec)
    assert rec["reconcile"]["count"] == 1
    assert abs(rec["lastIntake"]["calories"] - 300.0) < TOL


def test_a_band_change_marks_the_bus(h):
    p, rec = seeded(h)
    body = _body(h, rec, fm=40.0, lm=70.0)       # 110 kg: not the 80 kg band the body was built at
    old = body["band"]
    B = h.NR.server.bus
    B.effects.dirty["admin"] = None
    marks = B.effects.stats.marks
    h.NR.server.weight.minute("admin", p, rec)
    assert body["band"] != old
    assert B.effects.dirty["admin"] is True
    assert B.effects.stats.marks == marks + 1 and B.effects.stats.bandMarks >= 1
    B.effects.dirty["admin"] = None
    h.NR.server.weight.minute("admin", p, rec)           # the band unchanged: no mark
    assert B.effects.dirty["admin"] is None


def test_mark_band_is_the_effects_mark(h):
    B = h.NR.server.bus
    B.markBand("bob")
    assert B.effects.dirty["bob"] is True
    lim = list(B.limitations.values())
    assert any("band" in s and "effects" in s for s in lim)


# --- the store: the load at every first sight, in place -----------------------------------------------

def test_a_stored_record_reloads_in_place_at_every_first_sight(h):
    t = h.NR.server.store.records
    t["admin"] = h.K.store.new("admin", 2.0)
    p = h.player()
    rec = h.first_sight(p)
    rec["junk"] = 1                                       # a derived field the live minute laid
    h.NR.server.store.get("admin", 3.0)
    assert rec["junk"] == 1                               # the same sight: no reload
    for fn in h.NR.server.players.onDeparture.values():   # the player leaves
        fn("admin", None, None)
    h.NR.server.players.online = h.rt.table()
    again = h.first_sight(p)
    assert h.G.rawequal(again, rec) and rec["junk"] is None


def test_a_new_record_is_made_by_the_kernel(h):
    p = h.player(name="carol")
    rec = h.first_sight(p, "carol")
    assert rec["username"] == "carol" and rec["resets"] == 0


def test_a_respawn_reset_marks_the_record_loaded_and_reseeds_the_baseline(h):
    p, rec = seeded(h)
    p.nut.cal = 400.0
    for fn in h.T.adds["OnNewGame"].values():
        fn(p, None)
    new = h.NR.server.store.records["admin"]
    assert new["resets"] == 1
    assert h.NR.server.players.online["admin"] is None        # Plan 11 Task 9: evicted at OnNewGame (#3358)
    h.first_sight(p)                                          # the next minute re-sights it in its queue slot
    assert new["reconcile"]["baseline"]["calories"] == 400.0
    new["junk"] = 1
    h.NR.server.store.get("admin", 101.0)
    assert new["junk"] == 1


# --- Metabolism: a new character's body leaves the closed day unset ---------------------------------------

def test_ensure_body_of_a_new_character_leaves_the_closed_day_unset(h):
    p = h.player()
    rec = h.table({"username": "admin"})
    body = h.NR.server.metabolism.ensureBody("admin", p, rec, 50.0)
    assert body["inDayClosed"] is None
