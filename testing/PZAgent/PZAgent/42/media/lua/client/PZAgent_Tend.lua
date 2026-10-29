-- PZAgent_Tend.lua — the care skills (PZA/1.5, ruling P24-G; Plan 24 spec section 6): bandage, rip, wash and fill, registered
-- into PZA.skills.types like PZAgent_SkillsWorld.lua's, whose runner (K.start, K.tick) owns every act line, the S-12 and
-- S-15 guards and MO.off at every end (PZAgent_Stance.lua's K.start releases a held stance before each of them: every
-- vanilla action here stops on aiming). Loads after PZAgent_Stance.lua (client files load by name, "St" before "T") and
-- reaches PZAgent_SkillsWorld.lua's helpers through K (K.itemById, K.squareAt, K.floorOf, K.approach, K.queueAction,
-- K.numOf).
-- Every Java member through PZA.call (index-first), every vanilla class and member index-checked before a call under
-- pcall. The jar and install reads are docs/superpowers/specs/2026-10-29-plan-24-jar-reads-2.md sections 3-5 and 7
-- (Task 6b, rows T6b.5-T6b.8, T6b.10, T6b.11).
local K = PZA.skills
local W = PZA.world
local isDead, clearQueue = K.isDead, K.clearQueue

-- a boolean member read: true only when it answers true
local function flag(o, member, ...)
    local _, v = PZA.call(o, member, ...)
    return v == true
end

-- a number member read: the number, else 0 (PZAgent_SkillsWorld.lua's numOf, nil read as 0)
local function num(o, member)
    return K.numOf(o, member) or 0
end

-- the held item a check names by itemId: the item, else nil and the reason (bad args, none held)
local function heldItem(args, p)
    local id = args.itemId
    if type(id) ~= "number" then return nil, "bad args" end
    local it = K.itemById(p, id)
    if it == nil then return nil, "none held" end
    return it, nil
end

-- heldItem, and where it sits: K.itemById finds an item in a bag (ItemContainer.getItemById recurses), but the
-- server's ISApplyBandage:isValid tests getInventory():contains(item), which does not (ItemContainer.contains @0-@8
-- L658), and ISWashClothing:isValid requires item:getContainer() == character:getInventory() (lua:shared/
-- TimedActions/ISWashClothing.lua:10). Vanilla moves the item to the main inventory first (PZA/1.5.2, Task 9 fix 4,
-- review-t10 minor 8): ISInventoryPaneContextMenu.applyBandage (lua:client/ISUI/ISInventoryPaneContextMenu.lua:2781-
-- 2786) calls transferIfNeeded (:1910-1913), which, when luautils.haveToBeTransfered reads the item's getContainer()
-- not the player's getInventory() (lua:shared/luautils.lua:444-445), queues ISInventoryTransferAction:new(player,
-- item, item:getContainer(), player:getInventory()) before the bandage. Answers the item and its bag (nil when in the
-- main inventory: the bag the transfer moves it from), else nil and the reason: in bag (PZA/1.5.1, Task 9 review
-- minor 3) when the move cannot be queued, the container or the inventory unreadable (an absent member: fails closed)
-- or ISInventoryTransferAction absent.
local function mainItem(args, p)
    local it, why = heldItem(args, p)
    if it == nil then return nil, why end
    local _, inv = PZA.call(p, "getInventory")
    local _, c = PZA.call(it, "getContainer")
    if inv == nil or c == nil then return nil, "in bag" end
    if c == inv then return it, nil end
    local T = ISInventoryTransferAction
    if T == nil or T.new == nil then return nil, "in bag" end
    return it, nil, c
end

-- the first tick's move of a bag item (st.bag, mainItem's) to the main inventory, queued before the skill's own
-- action: nil when queued (st.moved true) or not needed, else the reason (in bag: the class or a raise refused it)
local function moveOut(p, st)
    if st.bag == nil then return nil end
    local _, inv = PZA.call(p, "getInventory")
    local ok = K.queueAction(ISInventoryTransferAction, "in bag", nil, p, st.item, st.bag, inv)
    if not ok then return "in bag" end
    st.moved = true
    return nil
end

-- a done result with moved true when the skill moved its item out of a bag first (elided otherwise)
local function withMoved(out, st)
    if st.moved then out.moved = true end
    return out
end

-- the ids of every item in the player's main inventory, as a set (empty when the list cannot be read)
local function idSet(p)
    local out = {}
    local _, inv = PZA.call(p, "getInventory")
    local _, items = PZA.call(inv, "getItems")
    local okN, n = PZA.call(items, "size")
    if not okN or type(n) ~= "number" then return out end
    for i = 0, n - 1 do
        local _, it = PZA.call(items, "get", i)
        local _, id = PZA.call(it, "getID")
        if id ~= nil then out[id] = it end
    end
    return out
end

-- ---- bandage {itemId, part} -----------------------------------------------------------------------------------------
-- The jar (jar-reads-2 section 3, T6b.5, T6b.6): any bandage stops its part's bleeding, scratch, cut and bite drains
-- (BodyPart.setBandaged clears those flags, their times kept) and ends the bleeding tenfold faster; a clean one halves
-- the infection odds against none, a dirty one (life 0: vanilla's ISApplyBandage sets 0 for a type containing Dirty)
-- doubles them. The action is vanilla's own, ISApplyBandage:new(character, otherPlayer, item, bodyPart, doIt)
-- (lua:shared/TimedActions/ISApplyBandage.lua:173), doIt true to apply, false (with no item) to take a bandage off
-- (ISHealthPanel.lua:1219), as the health panel queues them. check: itemId a number (bad args), the item held (none
-- held; in a bag, moved out first, PZA/1.5.2: in bag when the move cannot be queued) and isCanBandage() true (a bandage, a ripped sheet, dirty or clean: else
-- not valid); part a number (absent: -1), -1 the worst part (worstPart: a bleeding unbandaged part, a deep wound first,
-- then the longest getBleedingTime; else a wound under a dirty bandage; else an unbandaged wound; none: no wound), else
-- the index into getBodyParts() (out of range: bad args). The first tick: the vanilla queue cleared; an item in a bag
-- moved to the main inventory (moveOut: in bag); on a part already bandaged, the bandage taken off first (doIt false),
-- then the item applied (doIt true): not loaded, not valid. Done once the item is gone from the inventory by id and the
-- part reads bandaged(), {part (its index), dirty (the item's full type names Dirty), life (getBandageLife()), moved
-- (true when it was moved out of a bag first, else absent)}; interrupted after BANDAGE_MS.
K.BANDAGE_MS = 20000

-- the player's body parts as the Java list and its size (nil, 0 when unreadable)
local function bodyParts(p)
    local _, bd = PZA.call(p, "getBodyDamage")
    local _, list = PZA.call(bd, "getBodyParts")
    local okN, n = PZA.call(list, "size")
    if not okN or type(n) ~= "number" then return nil, 0 end
    return list, n
end

-- a part's wound under a bandage (whose flags setBandaged cleared): any wound time still running
local function woundTime(part)
    return num(part, "getBleedingTime") > 0 or num(part, "getDeepWoundTime") > 0 or num(part, "getScratchTime") > 0
        or num(part, "getCutTime") > 0 or num(part, "getBiteTime") > 0
end

-- the part's rank for the worst: 4 a bleeding unbandaged deep wound, 3 a bleeding unbandaged part, 2 a wound under a
-- dirty bandage, 1 an unbandaged wound (scratched, cut, bitten, deep-wounded), 0 nothing to bandage
local function rankOf(part)
    if flag(part, "bandaged") then
        if flag(part, "isBandageDirty") and woundTime(part) then return 2 end
        return 0
    end
    if flag(part, "bleeding") then
        if flag(part, "deepWounded") then return 4 end
        return 3
    end
    if flag(part, "scratched") or flag(part, "isCut") or flag(part, "bitten") or flag(part, "deepWounded") then
        return 1
    end
    return 0
end

-- the worst part and its index: the highest rank, then the longest bleeding time, then the lowest index; nil when no
-- part ranks above 0
local function worstPart(p)
    local list, n = bodyParts(p)
    local best, bi, br, bt = nil, nil, 0, 0
    for i = 0, n - 1 do
        local _, part = PZA.call(list, "get", i)
        if part ~= nil then
            local r = rankOf(part)
            if r > 0 then
                local t = num(part, "getBleedingTime")
                if r > br or (r == br and t > bt) then best, bi, br, bt = part, i, r, t end
            end
        end
    end
    return best, bi
end

K.types.bandage = {
    check = function(args, p)
        local it, why, bag = mainItem(args, p)
        if it == nil then return false, why end
        if not flag(it, "isCanBandage") then return false, "not valid" end
        local want = args.part
        if want == nil then want = -1 end
        if type(want) ~= "number" then return false, "bad args" end
        local part, idx
        if want < 0 then
            part, idx = worstPart(p)
            if part == nil then return false, "no wound" end
        else
            local list, n = bodyParts(p)
            want = math.floor(want)
            if want >= n then return false, "bad args" end
            local _, got = PZA.call(list, "get", want)
            if got == nil then return false, "bad args" end
            part, idx = got, want
        end
        return true, "", { id = args.itemId, item = it, bag = bag, part = part, index = idx, queuedAt = nil,
                           dirty = W.fullTypeHas(it, "Dirty", "Dirty") }
    end,
    tick = function(p, st)
        if isDead(p) then return "failed", "dead" end
        if st.queuedAt == nil then
            clearQueue(p)
            local whyMove = moveOut(p, st)
            if whyMove ~= nil then return "failed", whyMove end
            if flag(st.part, "bandaged") then
                local off, whyOff = K.queueAction(ISApplyBandage, "not valid", nil, p, p, nil, st.part, false)
                if not off then return "failed", whyOff end
            end
            local ok, why = K.queueAction(ISApplyBandage, "not valid", nil, p, p, st.item, st.part, true)
            if not ok then return "failed", why end
            st.queuedAt = PZA.now()
            return nil
        end
        if K.itemById(p, st.id) == nil and flag(st.part, "bandaged") then
            return "done", withMoved({ part = st.index, dirty = st.dirty, life = num(st.part, "getBandageLife") }, st)
        end
        if PZA.now() - st.queuedAt > K.BANDAGE_MS then return "failed", "interrupted" end
        return nil
    end,
}

-- ---- rip {itemId} ---------------------------------------------------------------------------------------------------
-- The jar and the scripts (jar-reads-2 section 4, T6b.7): the RipClothing craft recipe takes one unworn item tagged
-- base:ripclothingcotton with no tool and yields between 1 (or 2) and its covered-part count of RippedSheets, each one
-- RippedSheetsDirty with a chance of the item's dirt plus blood in percent; the denim and leather recipes need scissors
-- or a sharp knife. check: the item held (none held, bad args); ItemTag absent: not loaded; isWorn() true: worn (the
-- recipe's IsNotWorn: the skill never strips the character); hasTag(ItemTag.RIP_CLOTHING_COTTON) true passes, else a
-- denim or leather tag is needs tool, else not cotton. The first tick runs vanilla's own context-menu path,
-- ISInventoryPaneContextMenu.OnNewCraft(item, getScriptManager():getCraftRecipe("RipClothing"), playerNum, false)
-- (lua:client/ISUI/ISInventoryPaneContextMenu.lua:3428: a HandcraftLogic, canPerformCurrentRecipe, then
-- ISEntityUI.HandcraftStart queues the handcraft), each piece index-checked (not loaded) and the call under pcall
-- (not valid); a handcraft not in the queue after it (ISTimedActionQueue.hasActionType(p, "ISHandcraftAction") false,
-- the logic refused) is not valid, and hasActionType absent not loaded (PZA/1.5.1: fails closed). Done once the item is gone by id, {rags (the new items whose full type names
-- RippedSheets), dirty (those naming Dirty)}; interrupted after RIP_MS.
K.RIP_MS = 20000

-- the reason the item cannot be ripped without a tool, or nil: its class the inventory record's rip (W.ripOf,
-- PZA/1.5.2), worn its worn (W.wornOf)
local function ripRefusal(it)
    if ItemTag == nil then return "not loaded" end
    if W.wornOf(it) then return "worn" end
    local class = W.ripOf(it)
    if class == "cotton" then return nil end
    if class ~= nil then return "needs tool" end
    return "not cotton"
end

-- the first tick: vanilla's OnNewCraft on the RipClothing recipe; nil when the handcraft is queued, else the reason
local function ripStart(p, st)
    local M = ISInventoryPaneContextMenu
    if M == nil or M.OnNewCraft == nil or getScriptManager == nil or not K.queueLoaded() then return "not loaded" end
    local _, recipe = PZA.call(getScriptManager(), "getCraftRecipe", "RipClothing")
    local okN, num0 = PZA.call(p, "getPlayerNum")
    if recipe == nil or not okN then return "not loaded" end
    clearQueue(p)
    st.before = idSet(p)
    if not pcall(M.OnNewCraft, st.item, recipe, num0, false) then return "not valid" end
    local Q = ISTimedActionQueue
    if Q.hasActionType == nil then return "not loaded" end
    local okQ, has = pcall(Q.hasActionType, p, "ISHandcraftAction")
    if not okQ or has ~= true then return "not valid" end
    st.queuedAt = PZA.now()
    return nil
end

-- the rags the rip made: the items not in st.before whose full type names RippedSheets, and how many name Dirty
local function ripYield(p, st)
    local rags, dirty = 0, 0
    local now = idSet(p)                    -- a Lua table of the inventory by id
    for id, it in pairs(now) do
        if st.before[id] == nil and W.fullTypeHas(it, "RippedSheets", "RippedSheets") then
            rags = rags + 1
            if W.fullTypeHas(it, "Dirty", "Dirty") then dirty = dirty + 1 end
        end
    end
    return rags, dirty
end

K.types.rip = {
    check = function(args, p)
        local it, why = heldItem(args, p)
        if it == nil then return false, why end
        local no = ripRefusal(it)
        if no ~= nil then return false, no end
        return true, "", { id = args.itemId, item = it, queuedAt = nil, before = nil }
    end,
    tick = function(p, st)
        if isDead(p) then return "failed", "dead" end
        if st.queuedAt == nil then
            local why = ripStart(p, st)
            if why ~= nil then return "failed", why end
            return nil
        end
        if K.itemById(p, st.id) == nil then
            local rags, dirty = ripYield(p, st)
            return "done", { rags = rags, dirty = dirty }
        end
        if PZA.now() - st.queuedAt > K.RIP_MS then return "failed", "interrupted" end
        return nil
    end,
}

-- ---- wash {itemId, x, y} --------------------------------------------------------------------------------------------
-- The install and the jar (jar-reads-2 section 5, T6b.8): vanilla's ISWashClothing turns an item with ItemAfterCleaning
-- into that item (RippedSheetsDirty into RippedSheets, BandageDirty into Bandage), needs the source's getFluidAmount()
-- at least ceil(4 + 3 x the blood level) for a non-clothing item (ISWashClothing.GetRequiredWater, lua:shared/
-- TimedActions/ISWashClothing.lua:76-92), uses that much, and tests neither the water's taint nor soap; its new is
-- (character, sink, item, bloodAmount, dirtAmount, noSoap) (:230), vanilla passing the blood level for a non-clothing
-- item after a walk next to the source (ISWorldObjectContextMenu.lua:1777-1815). check: the item held (none held, bad
-- args; in a bag, moved out first, PZA/1.5.2: in bag when the move cannot be queued), getItemAfterCleaning() a non-empty string (else not dirty), x and y
-- numbers (bad args); on square (x, y) of the player's floor the first object whose hasWater() holds (W.waterOn: else
-- no source), its getFluidAmount() at least the need (else no water). The tick walks next to the source as interact
-- does (K.approach: not adjacent), then moves an item in a bag to the main inventory (moveOut: in bag) and queues
-- ISWashClothing:new(p, source, item, blood, 0, noSoap), noSoap unless the inventory's getSoapList(nil, true) reads not
-- empty (not loaded, not valid). Done once the item is gone by id, {water (the units the wash needs), moved (true when
-- it was moved out of a bag first, else absent)}; interrupted after WASH_MS from the queue.
K.WASH_MS = 40000

-- the water a wash of item it needs (ISWashClothing.GetRequiredWater's non-clothing rule) and its blood level
local function washNeed(it)
    local blood = num(it, "getBloodLevel")
    return math.ceil(4 + 3 * blood), blood
end

-- the first object on square (x, y) of the player's floor holding water, or nil and the reason (no source)
local function sourceAt(p, x, y)
    local sq = K.squareAt(x, y, K.floorOf(p))
    if sq == nil then return nil end
    return W.waterOn(sq)
end

-- whether the player carries no soap (vanilla's own read, getSoapList(nil, true), off the main inventory)
local function noSoap(p)
    local _, inv = PZA.call(p, "getInventory")
    local _, soaps = PZA.call(inv, "getSoapList", nil, true)
    local ok, empty = PZA.call(soaps, "isEmpty")
    return not ok or empty ~= false
end

K.types.wash = {
    check = function(args, p)
        local it, why, bag = mainItem(args, p)
        if it == nil then return false, why end
        local x, y = args.x, args.y
        if type(x) ~= "number" or type(y) ~= "number" then return false, "bad args" end
        local _, after = PZA.call(it, "getItemAfterCleaning")
        if type(after) ~= "string" or after == "" then return false, "not dirty" end
        x, y = math.floor(x), math.floor(y)
        local src = sourceAt(p, x, y)
        if src == nil then return false, "no source" end
        local need, blood = washNeed(it)
        if num(src, "getFluidAmount") < need then return false, "no water" end
        return true, "", { id = args.itemId, item = it, bag = bag, x = x, y = y, src = src, need = need,
                           blood = blood, sub = nil, queuedAt = nil }
    end,
    tick = function(p, st)
        if isDead(p) then return "failed", "dead" end
        if st.queuedAt == nil then
            local at = K.approach(p, st)
            if at == "fail" then return "failed", "not adjacent" end
            if at == "walk" then return nil end
            local whyMove = moveOut(p, st)
            if whyMove ~= nil then return "failed", whyMove end
            local ok, why = K.queueAction(ISWashClothing, "not valid", nil, p, st.src, st.item, st.blood, 0, noSoap(p))
            if not ok then return "failed", why end
            st.queuedAt = PZA.now()
            return nil
        end
        if K.itemById(p, st.id) == nil then return "done", withMoved({ water = st.need }, st) end
        if PZA.now() - st.queuedAt > K.WASH_MS then return "failed", "interrupted" end
        return nil
    end,
}

-- ---- fill {itemId, x, y} --------------------------------------------------------------------------------------------
-- The jar and the install (jar-reads-2 section 7, T6b.10, T6b.11): a sink or a toilet in a room gives clean Water
-- (infinite until the water shut-off, then its reserve of 20), a river or a puddle TaintedWater; the fill moves fluid
-- only on the server (IsoObject.transferFluidTo returns unmoved on a client), so the client reads the container's
-- amount rise once the server syncs it. Vanilla's action is ISTakeWaterAction:new(character, item, waterObject,
-- waterTaintedCL) (lua:shared/TimedActions/ISTakeWaterAction.lua:184), valid while the source hasFluid(), queued after
-- a walk next to the source with the source's own isTaintedWater() (ISWorldObjectContextMenu.lua:2064-2070). check:
-- the item held (none held, bad args), x and y numbers (bad args); its fluid container a drinking vessel that may take
-- water (W.fillable: not a container) with free capacity (getFreeCapacity above 0: else full; an empty vessel, the use
-- table's container, or a part-filled water item, topped up); on square (x, y) of the player's floor a water object
-- (W.waterOn: no source) whose getFluidAmount() is above 0 (no water). The tick walks next to the source (K.approach:
-- not adjacent), then queues ISTakeWaterAction:new(p, item, source, source:isTaintedWater() == true) (not loaded,
-- not valid). Done once the amount has risen and the container reads full (getFreeCapacity at most FULL_EPS) or has
-- held still FILL_STILL_MS, {amount, added, fluid (getPrimaryFluid():getFluidTypeString()), tainted (isTainted())};
-- interrupted when nothing has risen FILL_MS after the queue.
K.FILL_MS = 30000
K.FILL_STILL_MS = 1500
K.FULL_EPS = 0.001        -- litres: a free capacity at or under this reads full

local function fillResult(st)
    local _, f = PZA.call(st.fc, "getPrimaryFluid")
    local _, ft = PZA.call(f, "getFluidTypeString")
    local _, tainted = PZA.call(st.fc, "isTainted")
    local now = num(st.fc, "getAmount")
    return { amount = now, added = now - st.amount0, fluid = ft, tainted = tainted == true }
end

K.types.fill = {
    check = function(args, p)
        local it, why = heldItem(args, p)
        if it == nil then return false, why end
        local x, y = args.x, args.y
        if type(x) ~= "number" or type(y) ~= "number" then return false, "bad args" end
        local _, fc = PZA.call(it, "getFluidContainer")
        if not W.fillable(it, fc) then return false, "not a container" end
        if num(fc, "getFreeCapacity") <= K.FULL_EPS then return false, "full" end
        x, y = math.floor(x), math.floor(y)
        local src = sourceAt(p, x, y)
        if src == nil then return false, "no source" end
        if num(src, "getFluidAmount") <= 0 then return false, "no water" end
        return true, "", { id = args.itemId, item = it, fc = fc, x = x, y = y, src = src, sub = nil, queuedAt = nil,
                           amount0 = num(fc, "getAmount"), last = nil, stillAt = nil }
    end,
    tick = function(p, st)
        if isDead(p) then return "failed", "dead" end
        local now = PZA.now()
        if st.queuedAt == nil then
            local at = K.approach(p, st)
            if at == "fail" then return "failed", "not adjacent" end
            if at == "walk" then return nil end
            local tainted = flag(st.src, "isTaintedWater")
            local ok, why = K.queueAction(ISTakeWaterAction, "not valid", nil, p, st.item, st.src, tainted)
            if not ok then return "failed", why end
            st.queuedAt, st.last, st.stillAt = now, st.amount0, now
            return nil
        end
        local a = num(st.fc, "getAmount")
        if a ~= st.last then st.last, st.stillAt = a, now end
        if a > st.amount0 then
            if num(st.fc, "getFreeCapacity") <= K.FULL_EPS or now - st.stillAt >= K.FILL_STILL_MS then
                return "done", fillResult(st)
            end
            return nil
        end
        if now - st.queuedAt > K.FILL_MS then return "failed", "interrupted" end
        return nil
    end,
}

-- ---- the item re-read (PZA/1.5.1, Task 9 fix 1, review major 1) ----------------------------------------------------
-- A fill, a consume, a wash or a rip changes its item's contents, so each one's end marks its item for Sense's re-read
-- (PZAgent_Sense.lua's S.recheck: an item_changed event when the item's use or its settled fluid amount changed), with
-- the fluid amount the skill read when it began (fill's amount0, a drink's amount; nil otherwise). The mark is set at
-- every end: a done through the skill's tick, any other (failed, superseded, a raise) through its stop hook, which the
-- runner calls at every end but done. Each skill's table is edited in place, so a running skill's def (the runner's
-- cur.def) reads the wrapped members. A bandage needs none: it consumes its item, whose item_removed the diff emits.
local function mark(st)
    local S = PZA.sense
    if S == nil or S.recheck == nil or type(st) ~= "table" then return end
    S.recheck(st.id, st.amount0 or st.amount)
end

function K.markOnEnd(name)
    local def = K.types[name]
    local tick, stop = def.tick, def.stop
    def.tick = function(p, st)
        local state, out = tick(p, st)
        if state == "done" then mark(st) end
        return state, out
    end
    def.stop = function(p, st, reason)
        mark(st)
        if stop ~= nil then stop(p, st, reason) end
    end
end

for _, name in ipairs({ "fill", "consume", "wash", "rip" }) do K.markOnEnd(name) end
