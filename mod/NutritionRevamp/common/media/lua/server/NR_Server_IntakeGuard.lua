-- NR_Server_IntakeGuard.lua -- the server's refusal of an eat at Overfull 4.
--
-- Why: vanilla refuses an eat at FOOD_EATEN level 3 in client Lua alone (#3599): the menu greys Eat with
-- Tooltip_CantEatMore, and isValidStart runs only when the client's queue starts its NEXT action, so an eat added to an
-- empty queue (a script, the hotbar, a double queue) reaches the server, which meets no cap (#3936). The food-timer
-- bridge (NR_Server_Writer W.foodTimer) holds FOOD_EATEN at 3 exactly while the record reads Overfull 4, so the menu
-- refusal and this one read the same level.
--
-- The refusal path (read on the 42.21 jar, buildid 25485521):
--  * the server builds the eat through ISEatFoodAction.new and sets action.netAction (NetTimedAction.parse @221-@228
--    L175); ActionManager.start calls Action.start, then add (@19-@24 L43-L44); NetTimedAction.start lays the time
--    data (endTime = start + duration) and only then calls serverStart through a rawget (@0-@38 L102-L105), so a
--    forceComplete inside serverStart holds;
--  * NetTimedAction.forceComplete sets endTime to the server's now (@0-@4 L181), so ActionManager.update performs the
--    action on its next pass: perform calls Lua complete (protectedCallBoolean, @0-@21 L140); true is Done, false is
--    Reject, and either sends the action's packet to its client (ActionManager.update @72-@170 L70-L87, @173-@249
--    L88-L96);
--  * the client's LuaTimedActionNew.update reads ActionManager.isRejected and calls forceStop (@62-@77 L93-L94), so the
--    eat's animation stops, ISBaseTimedAction:stop resets the client's queue and the item is untouched;
--  * a server-side stop (ActionManager.remove: Action.stop, @252-@254 L197) calls Lua serverStop, and vanilla's
--    serverStop eats by netAction:getProgress(), which reads 1 once endTime == startTime (Action.getProgress @0-@12
--    L94-L95): a cancel after the forceComplete would eat the WHOLE item, so serverStop is guarded too.
-- Vanilla's own pattern: serverStart then netAction:forceComplete() (ISInsertMagazine.lua:60-62, ISRestAction.lua:
-- 101-103), and complete returning false as the reject (ISGatherBloodFromAnimal.lua:183-185). The message is vanilla's
-- server-side halo route, as ISReadABook sends it (forceComplete then doHaloText at :398-400; its
-- HaloTextHelper.addBadText of a getText at :86): HaloTextHelper.addText on a server sends a HaloText packet to the player (@60-@86 L158-L159), whose client
-- draws the string it carries, untranslated (HaloTextPacket.processClient @0-@15).
--
-- The wraps, three, on ISEatFoodAction (never `new`: the client sends the action's arguments by the
-- parameter names of the `new` closure on its class, so a varargs wrapper would send none):
--  * serverStart (vanilla defines none on ISEatFoodAction or ISBaseTimedAction, so NR.installWrap's absentOk installs
--    it over nil and any serverStart another mod laid first is chained): at Overfull 4 it marks the action refused
--    (action.nrRefused, a field of the server's action table, as ISReadABook's forceStopped is), forceCompletes it and
--    sends the player Tooltip_CantEatMore; below it the saved original, if any, runs unchanged;
--  * complete: a refused action returns false (the Reject) and nothing BELOW it runs: no Eat, no intake capture, and no
--    corpus wrap laid before this mod; a wrap laid AROUND it (a mod loaded after this one, such as QualityCooking, whose
--    complete wrap applies its buff whatever the result) still runs its own work (a limitation); any other action runs
--    the saved original unchanged;
--  * serverStop: a refused action stops with nothing eaten; any other stop (a real cancel) runs the original.
-- THE STATED EXCEPTION: the intake's wrappers ALWAYS call the saved original (NR_Server_Intake.lua's shape, #1067).
-- These three do not, on a refused action alone, on purpose: refusing the eat is the point. Below Overfull 4, for
-- every other item and on the client, each calls its original with the same arguments and returns its result.
--
-- Wrap order: this file must wrap complete and serverStop OUTSIDE the intake's capture, so a refusal never reaches the
-- capture. Each mod's Lua files run sorted case-insensitively (#0850), and "nr_server_intake.lua" sorts before
-- "nr_server_intakeguard.lua" ('.' before 'g'), so the intake wraps first at load and this file wraps its wrapper; the
-- file's name is load-bearing (testing/tests/kernel/test_intake_guard.py holds the order). G.outer reports it.
--
-- Shape (NR_Server_Fitness.lua's): each sentinel a global of its own, kept across a reload of this file and of NR_Core
-- (#0943); NR.installWrap is idempotent and never wraps a wrapper; the wrapper reads its logic from
-- NutritionRevamp.server.eatGuard per call; the side test is per call (this server/ file also runs in the client's
-- Lua state, #0855, where serverStart passes through); every Java global (ISEatFoodAction, HaloTextHelper, getText,
-- Events) is named only inside a function behind a nil check, so the file loads with no engine.
-- The rim guard: the check runs under one pcall and the refusal's steps under their own; a raising check runs the
-- original (the eat proceeds), and a raise after the mark leaves the action refused at its own end time.
--
-- Cadence (Rule 6): once per eat start, no clock and no per-minute work. The wrapper's side test (NR.isServer, one Java
-- call), then the check: the running mode (Lua), the eater's username (a second Java call), the record already in memory
-- (a table lookup, never a load) and its Overfull level (K.view.overfullOf, Lua): 2 Java calls below Overfull 4; only at
-- it does it read the item's hunger change (a third). A refusal
-- adds forceComplete, getText and the halo send. complete and serverStop read one Lua field. No @fastpath region.
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

-- The sentinels: globals of their own, kept across a reload of this file and of NR_Core.
NR_EatGuardStart_Installed = NR_EatGuardStart_Installed or {}
NR_EatGuardComplete_Installed = NR_EatGuardComplete_Installed or {}
NR_EatGuardStop_Installed = NR_EatGuardStop_Installed or {}

G.TEXT_KEY = "Tooltip_CantEatMore"            -- vanilla's menu refusal (ISInventoryPaneContextMenu.lua:503)
G.TEXT_FALLBACK = "Too full to eat more."     -- vanilla's EN text of the key (shared/Translate/EN/Tooltip.json:264)

-- Whether the server refuses the action: Mode 1, a sating food (getHungChange below 0, the context menu's test,
-- ISInventoryPaneContextMenu.lua:468), and the eater's in-memory record at Overfull K.view.REFUSE_AT. The record is read
-- as held, never loaded: a record not in memory refuses nothing.
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

-- The text the player sees: the key through getText when it resolves, else vanilla's EN text.
function G.text()
    local f = getText
    if f ~= nil then
        local ok, t = pcall(f, G.TEXT_KEY)
        if ok and type(t) == "string" and t ~= "" and t ~= G.TEXT_KEY then return t end
    end
    return G.TEXT_FALLBACK
end

-- The refusal's two steps, each under its own pcall: the forceComplete (the action performs on the server's next
-- update), then the message. A missing netAction is counted: the action then ends at its own time, still refused.
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

-- The start's decision under the rim guard: true when the action is refused (marked before anything that can raise,
-- so complete and serverStop hold it whatever follows), false when the original must run (a raising check included).
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

-- The serverStart wrapper: the check on the server; the original (when the class had one) on every other path.
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

-- The complete and serverStop wrapper: a refused action ends with nothing below it run (complete answers false, the
-- Reject); any other action runs the original with the same arguments and returns its result.
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

-- Installs the three wraps when ISEatFoodAction exists; returns whether all three are in place. Never touches new.
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

-- At load, after the intake's own wraps (the file order above), and again at OnServerStarted behind the side test,
-- where the state is logged once: at level 1 when the class exists (a guard not outside the intake's capture shows
-- there), at level 3 when it is absent (the intake's own line already reports no eat wrappers).
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
