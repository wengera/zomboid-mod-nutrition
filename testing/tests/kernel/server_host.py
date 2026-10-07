"""The shared server test host (Plan 10 Task R0; specified in the Plan 11 draft's Task 1 Step 2).

A FRESH Lua 5.1 runtime per Host: the ENV stand-ins (an Events table whose Add records each listener, isServer,
getGameTime off NR_T.age, print captured), NR_Core.lua, the shared data and kernel files, then every server/ file
in the engine's load order (alphabetical); OnServerStarted is fired once with the store's records table pre-set.
The ENV and PLAYER strings are test_server_reconcile_shape.py's, moved verbatim (that test keeps its own copies),
with PLAYER gaining a `dead` argument: the player's mutable field p.deadFlag starts at it and isDead reads it.
Nothing here runs in the kernel session host, so the kernel coverage gate is untouched.
"""
import glob
import os

import lupa.lua51 as lua51

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LUA = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua")
SHARED = os.path.join(LUA, "shared")
SERVER = os.path.join(LUA, "server")

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
# them, the setters write them and count), plus the weight members the Weight adapter calls. isDead reads the
# mutable p.deadFlag, which starts at the `dead` argument.
PLAYER = r"""
function(name, cal, carb, lip, pro, dead)
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
    local p = { nut = nut, deadFlag = dead == true }
    p.getUsername = function(s) return name end
    p.getNutrition = function(s) return nut end
    p.isDead = function(s) return s.deadFlag end
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
    def __init__(self, extra_env=""):
        self.rt = lua51.LuaRuntime(unpack_returned_tuples=True)
        self.rt.execute(ENV + extra_env)
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

    def player(self, name="admin", cal=1000.0, carb=100.0, lip=40.0, pro=60.0, dead=False):
        return self.rt.eval(PLAYER)(name, cal, carb, lip, pro, dead)

    def online(self, *players):
        lst = self.rt.table(*players)
        self.G.getOnlinePlayers = self.rt.eval(
            "function(l) return function() return { size = function(s) return #l end, "
            "get = function(s, i) return l[i + 1] end } end end")(lst)

    def fire(self, event, *args):
        for fn in self.T.adds[event].values():
            fn(*args)

    def minute(self):
        self.fire("EveryOneMinute")

    def tick(self, n=1):
        for _ in range(n):
            self.fire("OnTick")

    def record(self, name):
        return self.NR.server.store.records[name]

    def printed(self):
        return list(self.T.printed.values())
