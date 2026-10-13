-- NR_Server_Fitness.lua -- the Fitness exercise type, read on the server (Plan 11h, C-2; spec § 2). The engine cannot
-- say which exercise a set is: getFitness():getCurrentExe() answers a Fitness$FitnessExercise whose type has no getter
-- (#2180, #2901), reflection works only on a -debug server (#2736), and the server's action stack is empty during a set
-- (#2878). The server's own Lua action holds it, though: the client sends ISFitnessAction's arguments by the parameter
-- names of its `new` (NetTimedAction.set), the server rebuilds the action through ISFitnessAction.new (#2932), which
-- sets o.exeDataType, and calls serverStart by a rawget that falls through to the class table (NetTimedAction.start).
-- So this file wraps ISFitnessAction.serverStart and serverStop once: the wrapper calls the original, then records the
-- action's exeDataType per username at the start and clears it at the stop. NR_Server_Metabolism bills the recorded
-- type's MET (K.energy.EXERCISE_MET) while the exercise flag is set, and NR_Server_Training classes a rep by it. The
-- record is also dropped at the player's departure (FIT.forget).
--
-- Shape (the intake wrappers' shape, NR_Server_Intake.lua):
--  * NEVER wrap ISFitnessAction.new: the client copies the action's arguments by the parameter names of the `new`
--    closure it finds, so a varargs wrapper sends none and Fitness breaks for every player.
--  * Each sentinel is a global of its own, never a field of NutritionRevamp, which NR_Core re-creates on every load
--    (#0943). install() saves the current method and replaces it only when it is not already the mod's wrapper, and
--    re-wraps only when the class table itself was re-created, so a reload or a second start never wraps a wrapper and
--    another mod's later save-and-replace keeps ours in its chain.
--  * The wrapper ALWAYS calls the saved original first, outside any pcall, and returns its result; the record runs
--    after it under one pcall, so a mod bug never blocks a set. It reads its logic from NutritionRevamp.server.fitness
--    at call time, so a reload of this file swaps the logic under a wrapper that stays installed.
--  * The side test is per call: this server/ file also runs in the client's Lua state (#0855), where the wrapper only
--    passes through.
--  * Every Java global (ISFitnessAction, Events) is named only inside a function behind a nil check, so the file loads
--    with no engine (testing/tests/kernel/test_exercise_grading.py).
--
-- Trust: the type is client-asserted, the same string vanilla trusts for the set's reps and XP
-- (setCurrentExercise(exeDataType)); an unknown string bills the flat Fitness class. Cadence: one call per set start
-- and stop, no clock work; the minute reads the record as one Lua table lookup (Rule 6). No @fastpath region.
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
    },
}
local FIT = NR.server.fitness

-- The sentinels: globals of their own, kept across a reload of this file and of NR_Core.
NR_FitnessServerStart_Installed = NR_FitnessServerStart_Installed or {}
NR_FitnessServerStop_Installed = NR_FitnessServerStop_Installed or {}

-- The username of the action's character, or nil.
local function username(action)
    if type(action) ~= "table" then return nil end
    local ok, name = NR.call(action.character, "getUsername")
    if ok and type(name) == "string" then return name end
    return nil
end

-- The recorded exercise type of username's current set, or nil (Metabolism's and Training's one read).
function FIT.typeOf(name)
    if name == nil then return nil end
    return FIT.exeType[name]
end

-- One wrapped call's record, after the original ran: the start records the action's exeDataType when it is a string
-- (else clears it and counts untyped); the stop clears it. An action with no readable character records nothing.
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

-- The record leaves with the player (P.onDeparture).
function FIT.forget(name)
    local nr = NutritionRevamp
    if nr == nil or nr.server == nil or nr.server.fitness == nil then return end
    nr.server.fitness.exeType[name] = nil
end

-- The wrapper closure, made once per sentinel and kept in it; it names nothing from this file's load.
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

local function installOne(S, cls, method, kind)
    local cur = cls[method]
    if cur == nil then return false end
    if cur == S.wrapper then return true end               -- already the outermost: idempotent
    if S.wrapper ~= nil and S.class == cls then return true end -- still in the chain below a later wrap
    S.orig = cur
    S.wrapper = S.wrapper or makeWrapper(S, kind)
    S.class = cls
    cls[method] = S.wrapper
    NR.log.say(2, "fitness: ISFitnessAction." .. method .. " wrapped")
    return true
end

-- Installs both wraps when ISFitnessAction exists (vanilla's shared/TimedActions file, which loads before every
-- server/ file); returns whether both are in place. Never touches ISFitnessAction.new.
function FIT.install()
    local cls = ISFitnessAction
    if cls ~= nil then
        installOne(NR_FitnessServerStart_Installed, cls, "serverStart", "start")
        installOne(NR_FitnessServerStop_Installed, cls, "serverStop", "stop")
    end
    local A, B = NR_FitnessServerStart_Installed, NR_FitnessServerStop_Installed
    FIT.wrappedStart = cls ~= nil and A.wrapper ~= nil and A.class == cls
    FIT.wrappedStop = cls ~= nil and B.wrapper ~= nil and B.class == cls
    return FIT.wrappedStart and FIT.wrappedStop
end

-- With no class to wrap, the mod installs nothing: every set bills the flat Fitness class. Logged and listed once.
function FIT.noteAbsent()
    if FIT.absentNoted then return end
    FIT.absentNoted = true
    FIT.limitations[#FIT.limitations + 1] = "ISFitnessAction was absent at the server's start, so nothing is wrapped and every Fitness set bills the flat Fitness class (6.0)"
    NR.log.say(1, "fitness: ISFitnessAction is absent; nothing wrapped, every set bills the flat Fitness class (6.0)")
end

-- At load, so the wrap is in place before the first set (the wrapper gates on the side per call), and again at
-- OnServerStarted behind the side test, which also wires the departure hook once.
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
