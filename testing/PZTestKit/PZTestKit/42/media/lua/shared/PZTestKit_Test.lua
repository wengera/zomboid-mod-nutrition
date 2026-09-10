-- PZTestKit test layer: game-time scheduled tests, one JSON result per test.
--
-- Shared/ so either side can host a test, but every nutrition scenario runs on the SERVER:
-- `Nutrition.update @42 L75` is `!GameClient.client` and the stat drains are gated on
-- GameServer.server (03-notes Q7), so a client-side test would drive a mirror that the next
-- PlayerStatsPacket overwrites (measured in slice 01: a client setCalories is gone within a
-- second). There is no getPlayer() on a dedicated server, so the test's subject is resolved BY
-- USERNAME out of getOnlinePlayers() and handed to the test as `t.player`.
--
-- Why game minutes rather than wall seconds: the point of this layer is to run days of world
-- time in minutes of wall time (`settimespeed 30`), so every schedule is expressed in game
-- minutes and driven by Events.EveryOneMinute -- which fires on the dedicated server too
-- (slice 01's server harness already polls the command bus from it). A wall-clock schedule
-- would silently measure a different number of game hours every time the multiplier changed.
--
-- Loads after PZTestKit_Core.lua: Lua files in one folder load alphabetically, Core < Test.
--
-- Harness rules obeyed here (slice 01/02/03): Java members are probed with TK.call before they
-- are called (Kahlua's "tried to call nil" escapes pcall and kills the calling event handler);
-- no `goto`; and no "%d" on a Lua number (every Lua number is a double and %d can raise) --
-- "%.0f" everywhere.

TK.tests = TK.tests or { registry = {}, running = nil, clock = 0, due = {}, hooked = false }
local T = TK.tests

-- The server has no getPlayer(); the client has no other player. Returns (player, err).
function TK.resolvePlayer(username)
    if TK.side == "server" then
        if getOnlinePlayers == nil then return nil, "no getOnlinePlayers()" end
        local list = getOnlinePlayers()
        if list == nil then return nil, "getOnlinePlayers() returned nil" end
        local n = list:size()
        for i = 0, n - 1 do
            local p = list:get(i)
            if p ~= nil and (username == nil or p:getUsername() == username) then return p end
        end
        return nil, string.format("no online player %s (%.0f online)", tostring(username), n)
    end
    if getPlayer == nil then return nil, "no getPlayer()" end
    local p = getPlayer()
    if p == nil then return nil, "getPlayer() returned nil" end
    return p
end

-- ---- test context -----------------------------------------------------------
local Ctx = {}
Ctx.__index = Ctx

function Ctx:log(msg)
    self.logLines[#self.logLines + 1] = string.format("[%.0fm] %s", T.clock, tostring(msg))
end

-- Every sample carries the game minute, the world clock and the wall clock. The (worldAge,
-- wall) pair is what the Python side fits rates against, and it is also what makes the
-- harness's own cadence measurable -- how many EveryOneMinute ticks land per wall second at a
-- given multiplier -- without a second bus round-trip.
function Ctx:sample(tbl)
    tbl = tbl or {}
    tbl.gameMinute = T.clock
    tbl.worldAge = getGameTime():getWorldAgeHours()
    tbl.wall = TK.now()
    self.samples[#self.samples + 1] = tbl
    return tbl
end

function Ctx:at(minutes, fn)
    T.due[#T.due + 1] = { at = T.clock + (minutes or 0), fn = fn }
end

-- The re-arm happens BEFORE fn runs: a callback that raises is recorded as a failure by
-- onMinute's pcall, and one bad sample must not silently stop a repeating sampler halfway
-- through a three-day run. A callback that calls t:done() clears T.due, so the re-armed tick
-- is dropped anyway.
function Ctx:every(minutes, fn)
    local function tick()
        if T.running ~= self then return end
        self:at(minutes, tick)
        fn()
    end
    self:at(minutes, tick)
end

function Ctx:assert(cond, msg)
    if not cond then
        self.failures[#self.failures + 1] = tostring(msg)
        self:log("FAIL " .. tostring(msg))
    end
    return cond
end

function Ctx:near(a, b, tol, msg)
    local ok = a ~= nil and b ~= nil and math.abs(a - b) <= tol
    return self:assert(ok, string.format("%s: %s vs %s (tol %s)", tostring(msg), tostring(a),
                                         tostring(b), tostring(tol)))
end

-- Poll `pred` once per game minute until it is true or the budget runs out. The budget is the
-- failure mode that matters in an accelerated run: a condition that never arrives must end the
-- test with a named timeout, not hang until the outer timeoutMin and lose the label.
function Ctx:eventually(pred, budgetMinutes, label)
    local deadline = T.clock + (budgetMinutes or 60)
    local function poll()
        if T.running ~= self then return end
        if pred() then self:log("eventually ok: " .. tostring(label)); return end
        if T.clock >= deadline then
            self:assert(false, "eventually timed out: " .. tostring(label))
            self:done(false, "timeout: " .. tostring(label))
            return
        end
        self:at(1, poll)
    end
    poll()
end

function Ctx:done(pass, detail)
    if T.running ~= self then return end
    T.running = nil
    T.due = {}
    local ok = false
    if pass and #self.failures == 0 then ok = true end
    TK.result("test_" .. self.name, {
        test = self.name, pass = ok, detail = detail or "", failures = self.failures,
        samples = self.samples, log = self.logLines, gameMinutes = T.clock,
        player = self.username, side = TK.side,
        startedWall = self.startedWall,
        startedWorldAge = self.startedWorldAge, endedWorldAge = getGameTime():getWorldAgeHours(),
    })
    TK.log(string.format("test %s %s (%.0f game-min, %.0f failures)", self.name,
                         ok and "PASS" or "FAIL", T.clock, #self.failures))
end

-- ---- registry and scheduler --------------------------------------------------
-- spec = { timeoutMin = <game minutes>, player = <username>, needsPlayer = <bool>,
--          run = function(t) ... end }
function TK.test(name, spec)
    T.registry[name] = spec
    return name
end

local function start(name, username)
    local spec = T.registry[name]
    if spec == nil then return "unknown" end
    if T.running then return "already running " .. T.running.name end
    local user = username or spec.player or "admin"
    local p, perr = TK.resolvePlayer(user)
    -- No result doc on this path on purpose: the ack carries the reason and the runner fails
    -- immediately, instead of the caller reading a "failed" result for a test that never ran.
    if p == nil and spec.needsPlayer ~= false then
        return perr or ("no player " .. tostring(user))
    end
    local ctx = setmetatable({ name = name, username = user, player = p, samples = {},
                               logLines = {}, failures = {}, startedWall = TK.now(),
                               startedWorldAge = getGameTime():getWorldAgeHours() }, Ctx)
    T.running, T.clock, T.due = ctx, 0, {}
    ctx:log("start " .. name .. " on " .. TK.side .. " player=" .. tostring(user))
    ctx:at(spec.timeoutMin or 600, function() ctx:done(false, "test timeout") end)
    local ok, err = pcall(spec.run, ctx)
    if not ok then ctx:done(false, "run() error: " .. tostring(err)) end
    return "started"
end
TK.startTest = start

local function onMinute()
    if not T.running then return end
    T.clock = T.clock + 1
    local due, rest = {}, {}
    for _, d in ipairs(T.due) do
        if d.at <= T.clock then due[#due + 1] = d else rest[#rest + 1] = d end
    end
    T.due = rest
    for _, d in ipairs(due) do
        if T.running == nil then break end   -- one of them finished the test: drop the batch
        local ok, err = pcall(d.fn)
        if not ok and T.running then T.running:assert(false, "callback error: " .. tostring(err)) end
    end
end

-- Hooked once. `reloadlua` re-runs this file (S7) and a second Add() would advance the clock
-- twice per game minute -- every rate fitted against it would then be half of the truth. The
-- handler registered by the previous load keeps working: it closes over TK.tests, which is the
-- same table across a reload.
if not T.hooked and Events.EveryOneMinute then
    Events.EveryOneMinute.Add(onMinute)
    T.hooked = true
end

-- ---- bus commands ------------------------------------------------------------
TK.register("test.list", function()
    local out = {}
    for k in pairs(T.registry) do out[#out + 1] = k end
    table.sort(out)
    return out
end)

-- test.run <name> [username]. The username defaults to spec.player and then "admin": on the
-- server the test needs a live IsoPlayer and the only way to name one is the account.
TK.register("test.run", function(argv) return start(argv[1], argv[2]) end)

TK.register("test.status", function()
    return { running = T.running ~= nil, name = T.running and T.running.name or false,
             clock = T.clock, due = #T.due, side = TK.side,
             samples = T.running and #T.running.samples or 0 }
end)

TK.log("test layer loaded (" .. TK.side .. ")")
