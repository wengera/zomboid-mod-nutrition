-- PZAgent_Tend.lua — the care skills (PZA/1.5, ruling P24-G; Plan 24 spec section 6): bandage, rip and wash, registered
-- into PZA.skills.types like PZAgent_SkillsWorld.lua's, whose runner (K.start, K.tick) owns every act line, the S-12 and
-- S-15 guards and MO.off at every end (PZAgent_Stance.lua's K.start releases a held stance before each of them: every
-- vanilla action here stops on aiming). Loads after PZAgent_Stance.lua (client files load by name, "St" before "T") and
-- reaches PZAgent_SkillsWorld.lua's helpers through K (K.itemById, K.squareAt, K.floorOf, K.approach, K.queueAction).
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

-- a number member read: the number, else 0
local function num(o, member)
    local ok, v = PZA.call(o, member)
    if ok and type(v) == "number" then return v end
    return 0
end

-- the held item a check names by itemId: the item, else nil and the reason (bad args, none held)
local function heldItem(args, p)
    local id = args.itemId
    if type(id) ~= "number" then return nil, "bad args" end
    local it = K.itemById(p, id)
    if it == nil then return nil, "none held" end
    return it, nil
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
-- held) and isCanBandage() true (a bandage, a ripped sheet, a rag, dirty or clean: else not valid); part a number
-- (absent: -1), -1 the worst part (worstPart: a bleeding unbandaged part, a deep wound first, then the longest
-- getBleedingTime; else a wound under a dirty bandage; else an unbandaged wound; none: no wound), else the index into
-- getBodyParts() (out of range: bad args). The first tick: the vanilla queue cleared; on a part already bandaged, the
-- bandage taken off first (doIt false), then the item applied (doIt true): not loaded, not valid. Done once the item is
-- gone from the inventory by id and the part reads bandaged(), {part (its index), dirty (the item's full type names
-- Dirty), life (getBandageLife())}; interrupted after BANDAGE_MS.
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
        local it, why = heldItem(args, p)
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
        return true, "", { id = args.itemId, item = it, part = part, index = idx, queuedAt = nil,
                           dirty = W.fullTypeHas(it, "Dirty", "Dirty") }
    end,
    tick = function(p, st)
        if isDead(p) then return "failed", "dead" end
        if st.queuedAt == nil then
            clearQueue(p)
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
            return "done", { part = st.index, dirty = st.dirty, life = num(st.part, "getBandageLife") }
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
-- the logic refused) is not valid. Done once the item is gone by id, {rags (the new items whose full type names
-- RippedSheets), dirty (those naming Dirty)}; interrupted after RIP_MS.
K.RIP_MS = 20000

-- whether item it carries ItemTag[name] (false when the constant or the member is absent)
local function tagged(it, name)
    local t = ItemTag ~= nil and ItemTag[name] or nil
    if t == nil then return false end
    return flag(it, "hasTag", t)
end

-- the reason the item cannot be ripped without a tool, or nil
local function ripRefusal(it)
    if ItemTag == nil then return "not loaded" end
    if flag(it, "isWorn") then return "worn" end
    if tagged(it, "RIP_CLOTHING_COTTON") then return nil end
    if tagged(it, "RIP_CLOTHING_DENIM") or tagged(it, "RIP_CLOTHING_LEATHER") then return "needs tool" end
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
    if Q.hasActionType ~= nil then
        local okQ, has = pcall(Q.hasActionType, p, "ISHandcraftAction")
        if not okQ or has ~= true then return "not valid" end
    end
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
-- args), getItemAfterCleaning() a non-empty string (else not dirty), x and y numbers (bad args); on square (x, y) of the
-- player's floor the first object whose hasWater() holds (W.waterOn: else no source), its getFluidAmount() at least the
-- need (else no water). The tick walks next to the source as interact does (K.approach: not adjacent), then queues
-- ISWashClothing:new(p, source, item, blood, 0, noSoap), noSoap unless the inventory's getSoapList(nil, true) reads not
-- empty (not loaded, not valid). Done once the item is gone by id, {water (the units the wash needs)}; interrupted after
-- WASH_MS from the queue.
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
        local it, why = heldItem(args, p)
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
        return true, "", { id = args.itemId, item = it, x = x, y = y, src = src, need = need, blood = blood,
                           sub = nil, queuedAt = nil }
    end,
    tick = function(p, st)
        if isDead(p) then return "failed", "dead" end
        if st.queuedAt == nil then
            local at = K.approach(p, st)
            if at == "fail" then return "failed", "not adjacent" end
            if at == "walk" then return nil end
            local ok, why = K.queueAction(ISWashClothing, "not valid", nil, p, st.src, st.item, st.blood, 0, noSoap(p))
            if not ok then return "failed", why end
            st.queuedAt = PZA.now()
            return nil
        end
        if K.itemById(p, st.id) == nil then return "done", { water = st.need } end
        if PZA.now() - st.queuedAt > K.WASH_MS then return "failed", "interrupted" end
        return nil
    end,
}
