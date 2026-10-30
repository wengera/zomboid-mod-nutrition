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
-- PZA/1.5.3 (Task 9 fix 5, ruling P24-R): keepMoving (a boolean, absent: false; else bad args) asks for the bandage to
-- ride beside the moving leg (the ride, at the file's end). ISApplyBandage:new sets stopOnWalk to bodyPart:getIndex() >
-- BodyPartType.ToIndex(BodyPartType.Groin) (lua:shared/TimedActions/ISApplyBandage.lua:181), Groin's ordinal 10
-- (jar-reads-2 section 8), so a part from UpperLeg_L (11) to Foot_R (16) stops on a walk: with keepMoving such a part
-- is refused leg part, and the worst (-1) is sought among the parts above the legs only (leg part when only a leg part
-- qualifies); both apply whenever keepMoving is true, whether or not a leg runs (PZA/1.5.5). A part's index is its getIndex(), else its index in getBodyParts(). Without keepMoving, as before.
K.BANDAGE_MS = 20000
K.LEG_FIRST = 11          -- BodyPartType.UpperLeg_L's ordinal: the first part whose bandage stops on a walk

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

-- whether the part at list index i is a leg part (its bandage stops on a walk): getIndex(), else i, from LEG_FIRST
local function isLegPart(part, i)
    local ok, idx = PZA.call(part, "getIndex")
    if not ok or type(idx) ~= "number" then idx = i end
    return idx >= K.LEG_FIRST
end

-- the worst part and its index: the highest rank, then the longest bleeding time, then the lowest index; nil when no
-- part ranks above 0; aboveLegs (PZA/1.5.3) skips the leg parts
local function worstPart(p, aboveLegs)
    local list, n = bodyParts(p)
    local best, bi, br, bt = nil, nil, 0, 0
    for i = 0, n - 1 do
        local _, part = PZA.call(list, "get", i)
        if part ~= nil and not (aboveLegs and isLegPart(part, i)) then
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
        local want, keep = args.part, args.keepMoving
        if want == nil then want = -1 end
        if type(want) ~= "number" then return false, "bad args" end
        if keep ~= nil and type(keep) ~= "boolean" then return false, "bad args" end
        keep = keep == true
        local part, idx
        if want < 0 then
            part, idx = worstPart(p, keep)
            if part == nil then
                if keep and worstPart(p, false) ~= nil then return false, "leg part" end
                return false, "no wound"
            end
        else
            local list, n = bodyParts(p)
            want = math.floor(want)
            if want >= n then return false, "bad args" end
            local _, got = PZA.call(list, "get", want)
            if got == nil then return false, "bad args" end
            if keep and isLegPart(got, want) then return false, "leg part" end
            part, idx = got, want
        end
        return true, "", { id = args.itemId, item = it, bag = bag, part = part, index = idx, queuedAt = nil,
                           dirty = W.fullTypeHas(it, "Dirty", "Dirty"), keep = keep, ride = false, goneAt = nil }
    end,
    tick = function(p, st)
        if isDead(p) then return "failed", "dead" end
        if st.queuedAt == nil then
            if st.ride then K.rideBegin(p) else clearQueue(p) end
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
            local out = withMoved({ part = st.index, dirty = st.dirty, life = num(st.part, "getBandageLife") }, st)
            if st.ride then out.walking = true end
            return "done", out
        end
        if st.ride and K.rideLost(p, st) then return "failed", "stopped" end
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

-- ---- the ride (PZA/1.5.3, Task 9 fix 5, ruling P24-R) ----------------------------------------------------------------
-- A bandage on a part above the legs runs beside a moving leg. The read (jar-reads-2 section 8): ISApplyBandage's
-- stopOnWalk is false above the groin and its stopOnRun always true (lua:shared/TimedActions/ISApplyBandage.lua:181-
-- 182), its stopOnAim ISBaseTimedAction's true (lua:shared/TimedActions/ISBaseTimedAction.lua:180), and it blocks no
-- movement; a moving player stops the queue's front action only when that action's flag is set
-- (IsoPlayer.updateInternal2 @3289-@3362 L2853-L2865, IsoGameCharacter.StopAllActionQueueWalking @0-@104 L5515-L5536:
-- the action stops, the walk goes on), and an aiming one stops it on stopOnAim (@1746-@1754 L2586-L2587). The vanilla
-- queue runs one action at a time (lua:client/TimedActions/ISTimedActionQueue.lua:9-19), so a bandage queued behind
-- walkTo's ISWalkToTimedAction would wait for the walk's end.
-- The design: a second slot, K.side, beside the runner's K.cur, because the runner's one slot is the leg and the act
-- protocol already keys every line by aid (the slot is a record of K.cur's shape, ticked by the K.tick wrapper below,
-- its lines emitted through the runner's own K.emitAct). The frame's act group stays the leg's (K.status): the
-- bandage's accepted, progress, done and failed lines carry its aid, which the planner tracks, so me gains nothing.
--   K.start, wrapped: a bandage with keepMoving true while K.cur is a walkTo or a steer is checked as the runner checks
--     a command (dead, the check's own refusals, a raise bad args) and rides: it becomes K.side (a side already riding
--     ends failed superseded first) and K.cur keeps driving. While K.cur is an aim it is rejected aiming (the stance
--     stops the bandage). With no leg running it starts as before, standing (the leg-part refusal still applies). Any other command that replaces the leg
--     ends the side failed superseded (the runner's finish leaves the queue to it while a side rides:
--     PZAgent_Skills.lua); a new walkTo or steer takes the side along.
--   K.tick, wrapped: the side ticks first (its first tick: K.rideBegin clears a queued ISWalkToTimedAction, then the
--     bandage's own first tick queues it), then the leg; while a side rides the leg's gait is held at a walk (MO.want
--     and both latches written false: stopOnRun), and the leg's own gait is wanted back at once when the bandage leaves the vanilla queue (stopped, or performed and
--     awaiting the server's reading), else at the side's end. A leg that
--     ends done hands the side over to K.cur, where it finishes standing (its aid, its lines); a leg that fails ends
--     the side failed with the leg's dead, else interrupted.
--   walkTo, wrapped: while a side rides, the leg walks straight at its target on the auto-walk (setAutoWalk,
--     setAutoWalkDirection, the direction re-aimed every RIDE_AIM_MS) instead of the queued path walk, with no stuck
--     count; done within DONE_R without clearing the queue; after the ride it re-queues its path walk. steer's first
--     tick leaves the queue alone while a side rides (PZAgent_Skills.lua).
--   The bandage ends done with walking true; failed stopped when neither its ISApplyBandage nor its transfer has been
--     in the vanilla queue for RIDE_SETTLE_MS without the done reading (the engine stopped it: a run, an aim), the
--     settle covering the server's sync after vanilla's perform; interrupted after BANDAGE_MS.
-- rip, wash and fill never ride: the handcraft stops on a walk unless its recipe reads CanWalk (lua:shared/Entity/
-- TimedActions/ISHandcraftAction.lua:405; RipClothing names no CanWalk key), ISWashClothing and ISTakeWaterAction keep
-- ISBaseTimedAction's stopOnWalk true, and both need the source adjacent.
K.side = nil
K.RIDES = { walkTo = true, steer = true }
K.RIDE_SETTLE_MS = 3000
K.RIDE_AIM_MS = 250

-- whether a vanilla action of type t is in the player's queue (nil when the queue cannot say)
local function queued(p, t)
    local Q = ISTimedActionQueue
    if Q == nil or Q.hasActionType == nil then return nil end
    local ok, has = pcall(Q.hasActionType, p, t)
    if not ok then return nil end
    return has == true
end

-- the leg's gait held at a walk while a side rides (stopOnRun): the wants dropped, both latches written false once
local function holdWalk(p)
    local MO = PZA.motor
    if not MO.wantRun and not MO.wantSprint then return end
    MO.want("walk")
    PZA.call(p, "setForceRun", false)
    PZA.call(p, "setForceSprint", false)
end

-- the side's first tick: a walkTo's queued path walk cleared (the bandage would queue behind it), the gait held
function K.rideBegin(p)
    local cur = K.cur
    if cur ~= nil and cur.type == "walkTo" and queued(p, "ISWalkToTimedAction") then clearQueue(p) end
    holdWalk(p)
end

-- whether the riding bandage has been out of the vanilla queue for RIDE_SETTLE_MS (the engine stopped it); false when
-- the queue cannot say
function K.rideLost(p, st)
    local inQ = queued(p, "ISApplyBandage")
    if inQ == nil then return false end
    if inQ or (st.moved and queued(p, "ISInventoryTransferAction")) then
        st.goneAt = nil
        return false
    end
    local now = PZA.now()
    if st.goneAt == nil then st.goneAt = now end
    return now - st.goneAt >= K.RIDE_SETTLE_MS
end

-- the side's end: the slot cleared, a failure clearing the vanilla queue (as the runner's does), the leg's own gait
-- wanted back, then the act line
local function sideEnd(p, state, reason, result)
    local side = K.side
    K.side = nil
    if state == "failed" then
        clearQueue(p)
        if reason == nil or reason == "" then reason = "interrupted" end
    end
    local cur = K.cur
    if cur ~= nil and K.RIDES[cur.type] and cur.st.gait ~= nil then PZA.motor.want(cur.st.gait) end
    K.emitAct(p, side.aid, side.type, state, reason, result)
end

-- one tick of the side, as the runner ticks K.cur: a raise caught (failed interrupted), done, failed, else a progress
-- line at most every PROGRESS_MS
local function sideTick(p, side)
    local ran, state, out = pcall(side.def.tick, p, side.st)
    if not ran then
        K.caught(state)
        sideEnd(p, "failed", "interrupted")
        return
    end
    if state == "done" then
        sideEnd(p, "done", "", out or {})
        return
    end
    if state == "failed" then
        sideEnd(p, "failed", out)
        return
    end
    local now = PZA.now()
    if now - side.lastProgress >= K.PROGRESS_MS then
        side.lastProgress = now
        side.state = "progress"
        K.emitAct(p, side.aid, side.type, "progress")
    end
end

-- a rejected ride: the act line, a caught raise counted
local function rideReject(p, aid, reason, err)
    if err ~= nil then K.caught(err) end
    K.emitAct(p, aid, "bandage", "rejected", reason)
end

-- a bandage with keepMoving while K.cur is a leg (or an aim): checked as the runner checks a command, then K.side
local function startRide(cmd, p, leg)
    local aid = cmd.aid
    local readable, dead = pcall(isDead, p)
    if not readable then return rideReject(p, aid, "interrupted", dead) end
    if dead then return rideReject(p, aid, "dead") end
    local def = K.types.bandage
    local ran, ok, reason, st = pcall(def.check, cmd.args, p)
    if not ran then return rideReject(p, aid, "bad args", ok) end
    if not ok then return rideReject(p, aid, reason or "bad args") end
    if leg.type == "aim" then return rideReject(p, aid, "aiming") end
    if K.side ~= nil then sideEnd(p, "failed", "superseded") end
    st.ride = true
    K.side = { aid = aid, type = "bandage", def = def, st = st, state = "accepted", lastProgress = PZA.now() }
    K.emitAct(p, aid, "bandage", "accepted")
end

-- a well-formed bandage command asking keepMoving true (an empty aid or a bad keepMoving goes to the runner)
local function rideAsked(cmd)
    return type(cmd) == "table" and cmd.type == "bandage" and type(cmd.aid) == "string" and cmd.aid ~= ""
        and type(cmd.args) == "table" and cmd.args.keepMoving == true
end

local startTend = K.start
function K.start(cmd, p)
    local leg = K.cur
    if rideAsked(cmd) and leg ~= nil and (K.RIDES[leg.type] or leg.type == "aim") then
        startRide(cmd, p, leg)
        return
    end
    startTend(cmd, p)
    local cur = K.cur
    if K.side == nil or cur == leg then return end
    if cur ~= nil and K.RIDES[cur.type] then return end
    sideEnd(p, "failed", "superseded")
end

local tickTend = K.tick
function K.tick(p)
    if K.side ~= nil then sideTick(p, K.side) end
    local leg = K.cur
    tickTend(p)
    local side = K.side
    if side == nil then return end
    if K.cur ~= nil and K.cur == leg then
        -- the bandage out of the vanilla queue (the engine stopped it, or it performed and awaits the server's reading,
        -- st.goneAt set by K.rideLost): the leg's gait back at once, the settle only delays the act line (PZA/1.5.5)
        if side.st.goneAt ~= nil then
            if leg.st.gait ~= nil then PZA.motor.want(leg.st.gait) end
        else
            holdWalk(p)
        end
        return
    end
    if leg ~= nil and leg.st.ended == "done" and K.cur == nil then
        K.side = nil
        K.cur = side
        return
    end
    local why = "interrupted"
    if leg ~= nil and leg.st.endReason == "dead" then why = "dead" end
    sideEnd(p, "failed", why)
end

-- the leg's end recorded on its state (st.ended, st.endReason), which the K.tick wrapper reads once the runner has
-- finished it
local function recordEnd(st, state, out)
    if state == "done" or state == "failed" then st.ended, st.endReason = state, out end
    return state, out
end

-- walkTo while a side rides: straight at the target on the auto-walk, no stuck count, done without a queue clear
local function rideWalk(p, st)
    if isDead(p) then return "failed", "dead" end
    st.rode, st.still, st.lastX, st.lastY = true, 0, nil, nil
    local d = K.dist(p, st.x, st.y)
    if d ~= nil and d <= K.DONE_R then return "done", { d = d } end
    local px, py = W.posOf(p)
    if d == nil or d <= 0 or px == nil or py == nil then return nil end
    local now = PZA.now()
    if st.aimedAt ~= nil and now - st.aimedAt < K.RIDE_AIM_MS then return nil end
    if Vector2 == nil or Vector2.new == nil then return "failed", "not loaded" end
    st.aimedAt = now
    local ix, iy = K.inputVector((st.x - px) / d, (st.y - py) / d)
    PZA.call(p, "setAutoWalk", true)
    PZA.call(p, "setAutoWalkDirection", Vector2.new(ix, iy))
    return nil
end

local walkTick = K.types.walkTo.tick
K.types.walkTo.tick = function(p, st)
    local cur = K.cur
    if K.side ~= nil and cur ~= nil and cur.st == st then return recordEnd(st, rideWalk(p, st)) end
    if st.rode then
        st.rode, st.sq, st.aimedAt = nil, nil, nil       -- the ride over: the path walk re-queued by walkTo's own tick
        PZA.call(p, "setAutoWalk", false)
    end
    return recordEnd(st, walkTick(p, st))
end

local steerTick = K.types.steer.tick
K.types.steer.tick = function(p, st)
    return recordEnd(st, steerTick(p, st))
end

-- ---- wear {itemId} (PZA/1.6, Task 9 fix 9, review-t18 ruling 5; jar-reads-2 section 10) ------------------------------
-- A held garment put on as vanilla's context menu does it (ISInventoryPaneContextMenu.wearItem: transferIfNeeded, then
-- ISTimedActionQueue.add(ISWearClothing:new(playerObj, item, 50)), lua:client/ISUI/ISInventoryPaneContextMenu.lua:
-- 2888-2895); ISWearClothing (lua:shared/TimedActions/ISWearClothing.lua) runs 50 ticks, stops on a run, and its
-- complete (the server's) calls setWornItem(item:getBodyLocation(), item) for a Clothing item with a body location
-- (:101-:131), which replaces the item worn at that location (WornItems.setItem @0-@33 L54-L57) and drops any
-- exclusive one (@48-@93 L62-L65). check: the item held (mainItem: bad args, none held; in a bag, moved out first, in
-- bag when the move cannot be queued), its class Clothing with a body location (W.locOf; else not valid), not worn
-- already (worn), and the player neither in a hit reaction nor in a swing (K.attackBusy: busy, a garment put on under
-- attack is time lost). The first tick: moveOut, the item worn at that location now (getWornItem(getBodyLocation()),
-- its id the result's replaced) read, then ISWearClothing:new(p, item, 50) queued through K.queueAction (not loaded,
-- not valid). Done {itemId, loc, replaced, moved} once the item reads isWorn() true; WEAR_MS after the queue,
-- interrupted. At every end the garment and the one it replaced are marked for Sense's re-read (S.recheck: an
-- item_changed with the new worn and clothing record) and me.worn is read on the next frame (S.wornDirty).
K.WEAR_MS = 15000         -- a garment not worn within this wall time of its queue (a bag move and 50 ticks) is interrupted

local function wornId(p, it)
    local _, loc = PZA.call(it, "getBodyLocation")
    if loc == nil then return nil end
    local _, w = PZA.call(p, "getWornItem", loc)
    local _, id = PZA.call(w, "getID")
    return id
end

local function markWear(st)
    local S = PZA.sense
    if S == nil or type(st) ~= "table" then return end
    if S.recheck ~= nil then
        S.recheck(st.id, nil)
        if st.replaced ~= nil then S.recheck(st.replaced, nil) end
    end
    S.wornDirty = true
end

K.types.wear = {
    check = function(args, p)
        local it, why, bag = mainItem(args, p)
        if it == nil then return false, why end
        if not W.isA(it, "Clothing") then return false, "not valid" end
        local loc = W.locOf(it)
        if loc == nil then return false, "not valid" end
        if W.wornOf(it) then return false, "worn" end
        if K.attackBusy ~= nil and K.attackBusy(p) then return false, "busy" end
        return true, "", { id = args.itemId, item = it, bag = bag, loc = loc, queuedAt = nil }
    end,
    tick = function(p, st)
        if isDead(p) then return "failed", "dead" end
        if st.queuedAt == nil then
            local moved = moveOut(p, st)
            if moved ~= nil then return "failed", moved end
            st.replaced = wornId(p, st.item)
            local ok, why = K.queueAction(ISWearClothing, "not valid", nil, p, st.item, 50)
            if not ok then return "failed", why end
            st.queuedAt = PZA.now()
            return nil
        end
        if W.wornOf(st.item) then
            markWear(st)
            return "done", withMoved({ itemId = st.id, loc = st.loc, replaced = st.replaced }, st)
        end
        if PZA.now() - st.queuedAt > K.WEAR_MS then return "failed", "interrupted" end
        return nil
    end,
    stop = function(p, st, reason)
        markWear(st)
    end,
}

-- ---- unwear {itemId} (PZA/1.7, Task 9 fix 11; jar-reads-2 section 14, rows #4376 and #4377) -------------------------------
-- A worn garment taken off as vanilla's Unequip does it (ISInventoryPaneContextMenu.lua:2847 queues ISUnequipAction:new(
-- player, item, 50)): 50 ticks, stopped by a run, and by a walk unless the garment's body location is in
-- ISWearClothing.WalkBodyLocations (the accessory locations, lua:shared/TimedActions/ISWearClothing.lua:176-202). Its server
-- complete empties the location (removeWornItem) and leaves the garment in the main inventory unless the inventory has no
-- room for it (setWornItem places it on the floor then), where the RipClothing recipe accepts it (IsNotWorn refuses a worn or
-- held item). check: itemId a number (bad args), the item held (none held), worn (W.wornOf, isWorn(): else not worn), not in a
-- hand (isEquipped(): else held), and the player not moving unless the garment's location is in WalkBodyLocations (isPlayerMoving:
-- else moving; an absent list counts every location as stopping on a walk, fail-closed). The first tick queues the action through
-- K.queueAction (not loaded, not valid). Done {itemId, loc} once getWornItems():contains(item) reads false with the item in
-- the main inventory (ItemContainer.contains); failed dropped once it reads false with the item gone from it; failed stopped
-- when the action left the vanilla queue UNWEAR_SETTLE_MS ago with it still worn (a run or a walk stopped it); UNWEAR_MS
-- after the queue, interrupted. At every end the garment is marked for Sense's re-read (markWear: S.recheck, S.wornDirty).
K.UNWEAR_MS = 10000         -- a garment still worn this long after its queue is interrupted
K.UNWEAR_SETTLE_MS = 2000   -- the server's complete reaches the client late; past this after the action left the queue, stopped

-- whether action still sits in the player's vanilla queue (ISTimedActionQueue.hasAction), index-checked and under pcall
local function unwearQueued(action)
    local Q = ISTimedActionQueue
    if Q == nil or Q.hasAction == nil then return false end
    local ok, has = pcall(Q.hasAction, action)
    return ok and has == true
end

-- whether the garment's body location lets the unequip run beside a walk: its location is in WalkBodyLocations
local function walkOk(it)
    local list = ISWearClothing ~= nil and ISWearClothing.WalkBodyLocations or nil
    if type(list) ~= "table" then return false end
    local _, loc = PZA.call(it, "getBodyLocation")
    if loc == nil then return false end
    for i = 1, #list do
        if list[i] == loc or tostring(list[i]) == tostring(loc) then return true end
    end
    return false
end

-- the garment's state: worn (getWornItems():contains), held in the main inventory (contains; nil when unreadable, which
-- counts as held), and whether the worn list was readable
local function unwearReads(p, it)
    local _, wi = PZA.call(p, "getWornItems")
    local okW, w = PZA.call(wi, "contains", it)
    local _, inv = PZA.call(p, "getInventory")
    local okI, h = PZA.call(inv, "contains", it)
    local held = nil
    if okI then held = h == true end
    return okW and w == true, held, okW
end

K.types.unwear = {
    check = function(args, p)
        local it, why = heldItem(args, p)
        if it == nil then return false, why end
        if not W.wornOf(it) then return false, "not worn" end
        if flag(it, "isEquipped") then return false, "held" end
        if flag(p, "isPlayerMoving") and not walkOk(it) then return false, "moving" end
        return true, "", { id = args.itemId, item = it, loc = W.locOf(it), queuedAt = nil, action = nil, leftAt = nil }
    end,
    tick = function(p, st)
        if isDead(p) then return "failed", "dead" end
        if st.queuedAt == nil then
            if not PZA.field(p, "getWornItems") then return "failed", "not loaded" end
            local ok, why, action = K.queueAction(ISUnequipAction, "not valid", nil, p, st.item, 50)
            if not ok then return "failed", why end
            st.queuedAt, st.action = PZA.now(), action
            return nil
        end
        local worn, held, readable = unwearReads(p, st.item)
        if readable and not worn then
            markWear(st)
            if held ~= false then return "done", { itemId = st.id, loc = st.loc } end
            return "failed", "dropped"
        end
        local now = PZA.now()
        if st.leftAt == nil and not unwearQueued(st.action) then st.leftAt = now end
        if st.leftAt ~= nil and now - st.leftAt >= K.UNWEAR_SETTLE_MS then return "failed", "stopped" end
        if now - st.queuedAt > K.UNWEAR_MS then return "failed", "interrupted" end
        return nil
    end,
    stop = function(p, st, reason)
        markWear(st)
    end,
}
