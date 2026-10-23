-- NR_Server_IntakeGuard.lua: the server's refusal of an eat at Overfull 4.
-- Why: vanilla refuses an eat at FOOD_EATEN level 3 in client Lua alone (#3599), and an eat added to an empty queue (a
-- script, the hotbar) reaches the server, which meets no cap (#3936). The food-timer bridge holds FOOD_EATEN at 3
-- exactly while the record reads Overfull 4, so the menu refusal and this one read the same level.
-- The refusal path (42.21): NetTimedAction.start lays the time data before serverStart, so a forceComplete inside
-- serverStart holds; the action then performs on the next update, where complete returning false is the Reject and
-- the client stops with the item untouched. A server-side stop after the forceComplete would eat the WHOLE item
-- (getProgress reads 1 once endTime == startTime), so serverStop is guarded too. The message is vanilla's server-side
-- halo route (HaloTextHelper.addText), drawn untranslated by the client.
-- Three wraps on ISEatFoodAction, never `new` (the client sends the action's arguments by the `new` closure's parameter
-- names, so a varargs wrapper would send none): serverStart (vanilla defines none, so absentOk installs it over nil),
-- complete and serverStop. A wrap laid AROUND this one (a later mod such as QualityCooking) still runs its own work.
-- THE STATED EXCEPTION: the intake's wrappers ALWAYS call the saved original (#1067). These three do not, on a refused
-- action alone, on purpose: refusing the eat is the point.
-- Each sentinel is a global of its own (NR_Core re-creates NutritionRevamp on every load, #0943); the side test is per
-- call, because this server/ file also runs in the client's Lua state (#0855), where serverStart passes through.
-- Wrap order: this file must wrap OUTSIDE the intake's capture. Lua files run sorted case-insensitively (#0850), and
-- "nr_server_intake.lua" sorts before "nr_server_intakeguard.lua", so the file's name is load-bearing
-- (testing/tests/kernel/test_intake_guard.py holds the order).
-- The rim guard: a raising check runs the original (the eat proceeds); a raise after the mark leaves the action refused.
-- Cadence (Rule 6): once per eat start; 2 Java calls below Overfull 4.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.eatGuard = {
    stats = { checks = 0, refused = 0, held = 0, stopped = 0, failures = 0, passthrough = 0, unforced = 0,
              haloMissing = 0 },
    lastError = nil,
    wrappedStart = false,
    wrappedComplete = false,
    wrappedStop = false,
    outer = false,
    wired = false,
    limitations = {
        "an eat is refused on the server at Overfull 4 in Mode 1 (Managed) only, for a food whose hunger change is below 0 (vanilla's own menu test: a cigarette, a tea with no food value and every drink from a fluid container stay allowed); in Overlay vanilla owns its Well Fed timer and its menu refusal",
        "the refused eat's animation starts on the client and stops within a server frame and a round trip; the client's queue is cleared by the stop, so actions queued after the eat are dropped",
        "the refusal's message is vanilla's Tooltip_CantEatMore as halo text in the SERVER's language: the halo packet carries the server's string and the client draws it untranslated",
        "a later mod that replaces ISEatFoodAction.complete, serverStop or serverStart without calling the saved original removes the refusal silently, and a mod that puts its eat on the server some other way (a direct Eat call) is not refused",
        "an eat by a player whose record is not in memory yet (before the first sight's load) is not refused",
        "a mod loaded after NutritionRevamp wraps ISEatFoodAction.complete around the guard, so its own work still runs on a refused eat: QualityCooking's complete wrapper applies its cooking buff whatever the result, so a refused tiered dish can still give its buff (nothing is eaten)",
    },
}
local G = NR.server.eatGuard

NR_EatGuardStart_Installed = NR_EatGuardStart_Installed or {}
NR_EatGuardComplete_Installed = NR_EatGuardComplete_Installed or {}
NR_EatGuardStop_Installed = NR_EatGuardStop_Installed or {}

G.TEXT_KEY = "Tooltip_CantEatMore"            -- vanilla's menu refusal (ISInventoryPaneContextMenu.lua:503)
G.TEXT_FALLBACK = "Too full to eat more."     -- vanilla's EN text of the key (shared/Translate/EN/Tooltip.json:264)

-- A sating food (getHungChange below 0, the menu's test) and the eater's in-memory record at Overfull REFUSE_AT; the
-- record is read as held, never loaded, so a record not in memory refuses nothing.
function G.refuses(action)
    if type(action) ~= "table" then return false end
    if NR.runningMode() ~= 1 then return false end
    local char, item = action.character, action.item
    if char == nil or item == nil then return false end
    local okU, name = NR.call(char, "getUsername")
    if not okU or type(name) ~= "string" then return false end
    local S = NR.server.store
    local recs = S ~= nil and S.records or nil
    local record = recs ~= nil and recs[name] or nil
    if type(record) ~= "table" then return false end
    if K.view.overfullOf(record) < K.view.REFUSE_AT then return false end
    local okH, hung = NR.call(item, "getHungChange")
    return okH and type(hung) == "number" and hung < 0
end

-- Else vanilla's EN text.
function G.text()
    local f = getText
    if f ~= nil then
        local ok, t = pcall(f, G.TEXT_KEY)
        if ok and type(t) == "string" and t ~= "" and t ~= G.TEXT_KEY then return t end
    end
    return G.TEXT_FALLBACK
end

-- Each step under its own pcall. A missing netAction is counted: the action then ends at its own time, still refused.
function G.refuse(action)
    local okF, present = pcall(NR.call, action.netAction, "forceComplete")
    if not (okF and present) then G.stats.unforced = G.stats.unforced + 1 end
    local H = HaloTextHelper
    if H == nil or H.addBadText == nil then
        G.stats.haloMissing = G.stats.haloMissing + 1
        return
    end
    local okH = pcall(H.addBadText, action.character, G.text())
    if not okH then G.stats.haloMissing = G.stats.haloMissing + 1 end
end

local function fail(where, err)
    G.stats.failures = G.stats.failures + 1
    G.lastError = where .. ": " .. tostring(err)
    NR.log.say(2, "eat guard: " .. G.lastError)
end

-- Marked before anything that can raise, so complete and serverStop hold it whatever follows.
function G.start(action)
    G.stats.checks = G.stats.checks + 1
    local ok, refuse = pcall(G.refuses, action)
    if not ok then
        fail("check", refuse)
        return false
    end
    if not refuse then return false end
    action.nrRefused = true
    G.stats.refused = G.stats.refused + 1
    local okR, err = pcall(G.refuse, action)
    if not okR then fail("refuse", err) end
    NR.log.say(3, "eat guard: an eat refused at Overfull 4")
    return true
end

local function makeStart(S)
    return function(self, ...)
        local nr = NutritionRevamp
        local g = nil
        if nr ~= nil and nr.server ~= nil then g = nr.server.eatGuard end
        if g ~= nil and nr.isServer ~= nil and nr.isServer() then
            if g.start(self) then return end               -- refused: the stated exception, the original never runs
        elseif g ~= nil then
            g.stats.passthrough = g.stats.passthrough + 1  -- the client
        end
        if S.orig ~= nil then return S.orig(self, ...) end
    end
end

-- complete answers false, the Reject; any other action runs the original with the same arguments.
local function makeHold(S, kind)
    return function(self, ...)
        if type(self) == "table" and self.nrRefused == true then
            local nr = NutritionRevamp
            local g = nil
            if nr ~= nil and nr.server ~= nil then g = nr.server.eatGuard end
            if kind == "complete" then
                if g ~= nil then g.stats.held = g.stats.held + 1 end
                return false
            end
            if g ~= nil then g.stats.stopped = g.stats.stopped + 1 end
            return nil
        end
        return S.orig(self, ...)
    end
end

-- Never touches new.
function G.install()
    local cls = ISEatFoodAction
    if cls ~= nil then
        NR.installWrap(NR_EatGuardStart_Installed, cls, "serverStart", makeStart, nil,
            "eat guard: ISEatFoodAction.serverStart", true)
        NR.installWrap(NR_EatGuardComplete_Installed, cls, "complete", makeHold, "complete",
            "eat guard: ISEatFoodAction.complete")
        NR.installWrap(NR_EatGuardStop_Installed, cls, "serverStop", makeHold, "stop",
            "eat guard: ISEatFoodAction.serverStop")
    end
    local A, C, T = NR_EatGuardStart_Installed, NR_EatGuardComplete_Installed, NR_EatGuardStop_Installed
    G.wrappedStart = cls ~= nil and A.wrapper ~= nil and A.class == cls
    G.wrappedComplete = cls ~= nil and C.wrapper ~= nil and C.class == cls
    G.wrappedStop = cls ~= nil and T.wrapper ~= nil and T.class == cls
    local IC, IT = NR_IntakeComplete_Installed, NR_IntakeServerStop_Installed
    G.outer = G.wrappedComplete and G.wrappedStop and IC ~= nil and IT ~= nil and IC.wrapper ~= nil
        and C.orig == IC.wrapper and T.orig == IT.wrapper
    return G.wrappedStart and G.wrappedComplete and G.wrappedStop
end

-- At load, after the intake's own wraps (the file order above), and again at OnServerStarted, logged once.
G.install()

if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        local all = G.install()
        if G.wired then return end
        G.wired = true
        local level = 1
        if ISEatFoodAction == nil then level = 3 end
        NR.log.say(level, "eat guard: wraps " .. tostring(all) .. " outside the intake " .. tostring(G.outer))
    end)
end
