-- NR_Server_Fitness.lua: the Fitness exercise type, read on the server (C-2, docs/reference/research-notes.md). The
-- engine cannot say which exercise a set is (#2180; reflection only on a -debug server, #2736; the action stack is
-- empty, #2878), but the server rebuilds the action through ISFitnessAction.new (#2932), which sets o.exeDataType,
-- and calls serverStart off the class table. So serverStart and serverStop are wrapped to record the type per
-- username, which NR_Server_Metabolism bills (FIT.typeOf).
-- Shape (NR_Server_Intake.lua's):
--  * NEVER wrap ISFitnessAction.new: the client copies the action's arguments by the parameter names of the `new`
--    closure it finds, so a varargs wrapper sends none and Fitness breaks for every player.
--  * A sentinel global of its own (#0943); install() never wraps a wrapper.
--  * The wrapper ALWAYS calls the saved original first, outside any pcall; the record runs after it under one pcall.
--  * The side test is per call (#0855); the client only passes through.
-- Trust: the type is client-asserted, the same string vanilla trusts for the set's reps and XP; an unknown string
-- bills the flat Fitness class. One call per set start and stop (Rule 6).
local NR = NutritionRevamp
NR.server.fitness = {
    exeType = {},
    stats = { starts = 0, stops = 0, untyped = 0, passthrough = 0, failures = 0 },
    lastError = nil,
    wrappedStart = false,
    wrappedStop = false,
    wired = false,
    absentNoted = false,
    limitations = {
        "the exercise type is the one the client sent for the set (vanilla trusts the same string for the reps and XP); a set the wrapper did not see start (a reconnect mid-set, a boot mid-set, another mod that replaces ISFitnessAction.serverStart without calling the original) or a modded exercise with no EXERCISE_MET entry bills the flat Fitness class (6.0), counted in the metabolism stats' exeFallbacks",
        "a set the client abandons without a stop (another mod, a modified client) keeps the server's exercise flag set, as vanilla's server keeps the set running, and bills its type until the client disconnects; no set is capped at its asked length",
    },
}
local FIT = NR.server.fitness

-- Globals of their own, kept across a reload of this file and of NR_Core.
NR_FitnessServerStart_Installed = NR_FitnessServerStart_Installed or {}
NR_FitnessServerStop_Installed = NR_FitnessServerStop_Installed or {}

local function username(action)
    if type(action) ~= "table" then return nil end
    local ok, name = NR.call(action.character, "getUsername")
    if ok and type(name) == "string" then return name end
    return nil
end

-- Metabolism's and Strength's one read.
function FIT.typeOf(name)
    if name == nil then return nil end
    return FIT.exeType[name]
end

-- A non-string type clears and counts untyped; an action with no readable character records nothing.
function FIT.mark(action, kind)
    local name = username(action)
    if name == nil then return end
    if kind == "start" then
        local t = action.exeDataType
        if type(t) == "string" then
            FIT.exeType[name] = t
            FIT.stats.starts = FIT.stats.starts + 1
        else
            FIT.exeType[name] = nil
            FIT.stats.untyped = FIT.stats.untyped + 1
        end
        return
    end
    FIT.exeType[name] = nil
    FIT.stats.stops = FIT.stats.stops + 1
end

function FIT.forget(name)
    local nr = NutritionRevamp
    if nr == nil or nr.server == nil or nr.server.fitness == nil then return end
    nr.server.fitness.exeType[name] = nil
end

-- Made once per sentinel; it names nothing from this file's load.
local function makeWrapper(S, kind)
    return function(self, ...)
        local result = S.orig(self, ...)                   -- every path, first, never inside a pcall
        local nr = NutritionRevamp
        local fit = nil
        if nr ~= nil and nr.server ~= nil then fit = nr.server.fitness end
        if fit ~= nil and nr.isServer ~= nil and nr.isServer() then
            local ok, err = pcall(fit.mark, self, kind)
            if not ok then
                fit.stats.failures = fit.stats.failures + 1
                fit.lastError = err
            end
        elseif fit ~= nil then
            fit.stats.passthrough = fit.stats.passthrough + 1 -- the client
        end
        return result
    end
end

-- ISFitnessAction loads before every server/ file. Never touches ISFitnessAction.new.
function FIT.install()
    local cls = ISFitnessAction
    if cls ~= nil then
        NR.installWrap(NR_FitnessServerStart_Installed, cls, "serverStart", makeWrapper, "start",
            "fitness: ISFitnessAction.serverStart")
        NR.installWrap(NR_FitnessServerStop_Installed, cls, "serverStop", makeWrapper, "stop",
            "fitness: ISFitnessAction.serverStop")
    end
    local A, B = NR_FitnessServerStart_Installed, NR_FitnessServerStop_Installed
    FIT.wrappedStart = cls ~= nil and A.wrapper ~= nil and A.class == cls
    FIT.wrappedStop = cls ~= nil and B.wrapper ~= nil and B.class == cls
    return FIT.wrappedStart and FIT.wrappedStop
end

-- Every set then bills the flat Fitness class. Logged and listed once.
function FIT.noteAbsent()
    if FIT.absentNoted then return end
    FIT.absentNoted = true
    FIT.limitations[#FIT.limitations + 1] = "ISFitnessAction was absent at the server's start, so nothing is wrapped and every Fitness set bills the flat Fitness class (6.0)"
    NR.log.say(1, "fitness: ISFitnessAction is absent; nothing wrapped, every set bills the flat Fitness class (6.0)")
end

-- At load, and again at OnServerStarted behind the side test, which also wires the departure hook once.
FIT.install()

if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        if not FIT.install() and ISFitnessAction == nil then FIT.noteAbsent() end
        if FIT.wired then return end
        local P = NR.server.players
        if P == nil or P.onDeparture == nil then return end
        FIT.wired = true
        P.onDeparture[#P.onDeparture + 1] = FIT.forget
    end)
end
