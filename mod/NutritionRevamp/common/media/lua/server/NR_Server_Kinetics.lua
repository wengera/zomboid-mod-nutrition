-- NR_Server_Kinetics.lua -- the slow-clock drive of the stomach (spec § 4.2, § 4.4): once per player
-- per game minute, on the players' OnTick stagger, the stomach empties over the game hours since the
-- last run, the emptied vector is absorbed, the absorbed vector accumulates into the pool, and the
-- fill is stamped on the record as record.stomachFill for the fast clock to read
-- (NR_Server_Fast.lua hands it to the kernel as inp.stomachFill).
-- Plan 2 ruling: hunger derives from stomach fill and is written to HUNGER every tick, so vanilla's
-- eat-time hunger write is overwritten within one push -- the stomach is the state, hunger the view.
-- Two companion game choices make that playable: (1) a record with no stomach yet is seeded FULL
-- (K.stomach.seedFull) -- judgement: the character ate before the apocalypse, so a new or respawned
-- character starts at vanilla's hunger 0 and empties on the gastric half-time; (2) the energy-state
-- term is stubbed at 1 in the fast adapter (inp.energyState = 1), the Plan 3 entry point. Thirst is
-- untouched in this plan: vanilla's drain stays until Plan 4 derives thirst from the water pool.
-- Every field written on the record is a number or a table of numbers (global modData holds no
-- function or Java object, #1495). Nothing runs at file scope but table setup: the registration is
-- in the OnServerStarted handler behind the side test, so the file loads with no engine.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.kinetics = { stats = { minutes = 0, players = 0 }, lastError = nil, wired = false }
local KIN = NR.server.kinetics

local function worldAge()
    if getGameTime == nil then return 0 end
    local ok, gt = pcall(getGameTime)
    local okA, age = NR.call(ok and gt or nil, "getWorldAgeHours")
    if okA and type(age) == "number" then return age end
    return 0
end

local function step(username, player, record)
    local age = worldAge()
    if record.stomach == nil then
        record.stomach = K.stomach.new()
        K.stomach.seedFull(record.stomach)            -- judgement: the character ate before the apocalypse
    end
    if record.pool == nil then
        record.pool = K.vector.new()
    end
    local last = record.kineticsAge
    local dtH = 0
    if last ~= nil then
        dtH = K.max(age - last, 0)
    end
    record.kineticsAge = age
    if dtH > 0 then
        local emptied = K.stomach.empty(record.stomach, dtH)
        local absorbed = K.stomach.absorb(emptied)
        K.stomach.toPool(record.pool, absorbed)
    end
    record.stomachFill = K.stomach.fill(record.stomach)
    KIN.stats.players = KIN.stats.players + 1
end

-- One player's minute: the (username, player, record) callback NR_Server_Players fires from P.work.
-- One pcall around the body: a failure is kept and logged on the slow clock, never raised into the
-- players walk.
function KIN.minute(username, player, record)
    if record == nil then return end
    KIN.stats.minutes = KIN.stats.minutes + 1
    local ok, err = pcall(step, username, player, record)
    if not ok then
        KIN.lastError = err
        NR.log.say(2, "kinetics: " .. tostring(username) .. " failed: " .. tostring(err))
    end
end

if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        if KIN.wired then return end
        KIN.wired = true
        local P = NR.server.players
        P.onMinute[#P.onMinute + 1] = KIN.minute
    end)
end
