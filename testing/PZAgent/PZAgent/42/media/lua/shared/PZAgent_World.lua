-- PZAgent_World.lua — the world readers (PZA.world), one table that Map, Sense and both Skills files read squares,
-- objects and positions through (Plan 22 fix wave M2: these were four files' private copies). Loads after
-- PZAgent_Core.lua and PZAgent_Schema.lua (shared/, by name) and before every client file. Every Java member is reached
-- through PZA.call (index-first: a member an object lacks is skipped, never nil-called), and a Java list is walked by
-- size/get, never #. Nothing here raises on an absent member; a raising member inside a present one propagates to the
-- caller's own guard (Main's map pcall, Sense's group pcalls, the runner's pcall round a skill).
PZA.world = PZA.world or {}
local W = PZA.world

function W.isA(o, cls)
    return instanceof ~= nil and instanceof(o, cls) == true
end

-- obj:member(...) into out[key] when the member is present, else the member's name added to miss; answers ok and v
function W.getm(miss, out, key, obj, member, ...)
    local ok, v = PZA.call(obj, member, ...)
    if ok then out[key] = v else PZA.missing(miss, member) end
    return ok, v
end

-- a number read, or nil when the member is absent or answers no number
local function num(ok, v)
    if ok and type(v) == "number" then return v end
    return nil
end

-- the object's (a player's, a zombie's) world x and y, and z when withZ, each nil when absent or not a number
function W.posOf(o, withZ)
    local x = num(PZA.call(o, "getX"))
    local y = num(PZA.call(o, "getY"))
    if not withZ then return x, y end
    return x, y, num(PZA.call(o, "getZ"))
end

-- the square's objects as a Lua array of its non-nil entries (none when the square or its list cannot be read), and
-- their count. A per-frame caller passes its own scratch table as out, filled from 1 and read to the count only (entries
-- past it are a previous square's), so a walk of many squares allocates nothing; out is a new table when absent.
function W.objectsOn(sq, out)
    out = out or {}
    local k = 0
    local _, list = PZA.call(sq, "getObjects")
    local okN, n = PZA.call(list, "size")
    if not okN or type(n) ~= "number" then return out, 0 end
    for i = 0, n - 1 do
        local _, o = PZA.call(list, "get", i)
        if o ~= nil then
            k = k + 1
            out[k] = o
        end
    end
    return out, k
end

-- door, window or nil, by type first: an IsoThumpable answers by isDoor, then isWindow (IsoWindow and IsoThumpable
-- also answer IsOpen/isLocked/isBarricaded, so the members cannot tell a portal's kind)
function W.kindOf(o)
    if W.isA(o, "IsoDoor") then return "door" end
    if W.isA(o, "IsoWindow") then return "window" end
    if W.isA(o, "IsoThumpable") then
        local _, d = PZA.call(o, "isDoor")
        if d == true then return "door" end
        local _, w = PZA.call(o, "isWindow")
        if w == true then return "window" end
    end
    return nil
end

-- the square's door or window that a timed action can open and its kind, door first. A window is an IsoWindow only,
-- since ISOpenCloseWindow:perform calls character:openWindow(object), which the jar takes as IsoWindow alone (a
-- thumpable window would raise)
function W.openableOn(sq)
    local win = nil
    local objs = W.objectsOn(sq)
    for _, o in ipairs(objs) do
        local k = W.kindOf(o)
        if k == "door" then return o, "door" end
        if k == "window" and win == nil and W.isA(o, "IsoWindow") then win = o end
    end
    if win ~= nil then return win, "window" end
    return nil, nil
end

-- the object's containers as a Lua array: getContainerCount/getContainerByIndex, else its one getContainer
function W.containersOf(o)
    local out = {}
    local okN, cn = PZA.call(o, "getContainerCount")
    if okN and type(cn) == "number" then
        for i = 0, cn - 1 do
            local _, c = PZA.call(o, "getContainerByIndex", i)
            if c ~= nil then out[#out + 1] = c end
        end
    else
        local _, c = PZA.call(o, "getContainer")
        if c ~= nil then out[#out + 1] = c end
    end
    return out
end

-- every container of every object on the square, as a Lua array
function W.containersOn(sq)
    local out = {}
    local objs = W.objectsOn(sq)
    for _, o in ipairs(objs) do
        local cs = W.containersOf(o)
        for _, c in ipairs(cs) do out[#out + 1] = c end
    end
    return out
end

-- an item's full type holds a or b as plain text (the loot's bandage rule and consume's bleach and petrol rule)
function W.fullTypeHas(it, a, b)
    local _, ft = PZA.call(it, "getFullType")
    ft = tostring(ft or "")
    return string.find(ft, a, 1, true) ~= nil or string.find(ft, b, 1, true) ~= nil
end

-- The use table (PZA/1.4.1, ruling P24-F; F2 drank a Base.Disinfectant, RubbingAlcohol, 68 times with no thirst fall).
-- Water is what vanilla's drink menu offers to drink that lowers thirst and harms nothing (PZA/1.5, the Task 9
-- amendment: a pop, a juice or a milk is water too). Vanilla offers a drink for a container whose
-- FluidContainer.isWaterSource() holds (the 42.21 jar: isEmpty false and the primary fluid Water, TaintedWater or
-- CarbonatedWater, FluidContainer.isWaterSource @0 L875; InventoryItem.isWaterSource @0 L2889 wraps it) or whose primary
-- fluid isCategory(FluidCategory.Beverage) (ISInventoryPaneContextMenu.lua L436-L443). Read here on the container so a
-- fake answers it: a container vanilla's drink menu refuses (getCapacity over DRINK_CAP_L, its Tooltip_CantDrinkFrom in
-- doDrinkFluidMenu), a tainted one (isTainted) or a poisonous one is never water, nor a full type naming Bleach or
-- Petrol (Act's firstDrink rule); a water source is water; any other is water only when none of its fluids is
-- Hazardous or Alcoholic (FluidContainer.isCategory: any fluid in it; the fluids' categories off scripts/generated/
-- fluids.txt, data/food-items.json's fluids), one is a Beverage, and its mixed properties lower thirst
-- (getProperties():getThirstChange() below 0, SealedFluidProperties). Fails closed: a read absent reads no (an absent
-- FluidCategory leaves only the water sources).
W.DRINK_CAP_L = 3.0       -- litres: ISInventoryPaneContextMenu.doDrinkFluidMenu refuses a drink from a larger container

local function reads(obj, member, want, ...)
    local ok, v = PZA.call(obj, member, ...)
    return ok and v == want
end

-- the container is one a character drinks from: not over DRINK_CAP_L litres, and no Bleach or Petrol by full type
local function drinkVessel(it, fc)
    if W.fullTypeHas(it, "Bleach", "Petrol") then return false end
    local _, cap = PZA.call(fc, "getCapacity")
    return type(cap) == "number" and cap <= W.DRINK_CAP_L
end

-- fc:isCategory(FluidCategory[name]): true or false, nil when the constant or the member is absent
local function category(fc, name)
    local c = FluidCategory ~= nil and FluidCategory[name] or nil
    if c == nil then return nil end
    local ok, v = PZA.call(fc, "isCategory", c)
    if not ok then return nil end
    return v == true
end

-- a beverage that lowers thirst and is neither hazardous nor alcoholic (the water sources aside)
local function quenches(fc)
    if category(fc, "Hazardous") ~= false or category(fc, "Alcoholic") ~= false then return false end
    if category(fc, "Beverage") ~= true then return false end
    local _, props = PZA.call(fc, "getProperties")
    local _, thirst = PZA.call(props, "getThirstChange")
    return type(thirst) == "number" and thirst < 0
end

-- the item holds a fluid a character can drink (fc, its fluid container): the use table's water and consume's drink.
-- A sealed container is never drinkable (PZA/1.5.1, Task 9 review minor 2): vanilla's drink menu disables one whose
-- canPlayerEmpty() is false (ISInventoryPaneContextMenu.lua:2308, Tooltip_item_sealed; FluidContainer.canPlayerEmpty
-- @0-@19 L214: not a multi-tile moveable and the canPlayerEmpty field, which FluidContainer.unseal sets true @44 L1474),
-- as a pop can tagged base:sealedbeveragecan spawns; an absent member reads sealed (fails closed)
function W.drinkable(it, fc)
    if fc == nil or not drinkVessel(it, fc) then return false end
    if not reads(fc, "canPlayerEmpty", true) then return false end
    if not (reads(fc, "isTainted", false) and reads(fc, "isPoisonous", false)) then return false end
    if reads(fc, "isWaterSource", true) then return true end
    return quenches(fc)
end

-- the item is an empty drinking vessel that may hold water, FluidContainer.canAddFluid(Fluid.Water) (@0 L950: not
-- input-locked, canPlayerEmpty, its fluids blend with water and its whitelist and blacklist allow it): the use
-- table's container, which Task 9's fill takes to a sink or a toilet
function W.waterVessel(it, fc)
    if fc == nil or Fluid == nil or not drinkVessel(it, fc) then return false end
    return reads(fc, "isEmpty", true) and reads(fc, "canAddFluid", true, Fluid.Water)
end

-- the item is food a character can eat: isA Food with getHungerChange below 0 (a spice or a hunger-free food is not)
function W.edible(it)
    if not W.isA(it, "Food") then return false end
    local _, h = PZA.call(it, "getHungerChange")
    return type(h) == "number" and h < 0
end

-- the item's use as the engine answers it (item_added.use, item_changed.use, the loot's filters): food (edible), else
-- weapon (before water: a saucepan is both), else water (drinkable), else container (an empty water vessel), else
-- bandage (isCanBandage() true, PZA/1.5.1, Task 9 review minor 5: the script's CanBandage, which Bandage, BandageDirty,
-- Bandaid, RippedSheets, RippedSheetsDirty, the denim and leather strips and the alcohol-soaked ones carry, and a Rag
-- or a BandageBox does not; an absent member reads no), else other. PZA/1.6 (Task 9 fix 9, review-t18 ruling 5): an
-- item whose class is Clothing reads clothing, after weapon (a Clothing is never a Food or a HandWeapon) and before
-- water (a garment carries no drinking vessel)
function W.useOf(it)
    if W.edible(it) then return "food" end
    if W.isA(it, "HandWeapon") then return "weapon" end
    if W.isA(it, "Clothing") then return "clothing" end
    local _, fc = PZA.call(it, "getFluidContainer")
    if W.drinkable(it, fc) then return "water" end
    if W.waterVessel(it, fc) then return "container" end
    if reads(it, "isCanBandage", true) then return "bandage" end
    return "other"
end

-- the square's first object whose hasWater() holds (IsoObject.hasWater @0-@177 L3108-L3145, jar-reads-2 section 7: an
-- infinite source, a fluid container whose contents are all water, an unmoved piped source with reserve water, a sprite
-- flagged taintedWater, a solid floor with puddles over 0.09), or nil: the source of the wash and the fill (PZA/1.5)
function W.waterOn(sq)
    local objs, n = W.objectsOn(sq)
    for i = 1, n do
        local _, w = PZA.call(objs[i], "hasWater")
        if w == true then return objs[i] end
    end
    return nil
end

-- the item's fluid container takes water at a fill (PZA/1.5's fill): a drinking vessel (drinkVessel) whose
-- canAddFluid(Fluid.Water) holds, empty (the use table's container) or part-filled with water (its water, topped up)
function W.fillable(it, fc)
    if fc == nil or Fluid == nil or not drinkVessel(it, fc) then return false end
    return reads(fc, "canAddFluid", true, Fluid.Water)
end

-- the item's inventory record beyond its use (PZA/1.5.2, Task 9 fix 4, review-t10 minor 7: the planner stops guessing
-- a garment's rip class from its name and worn from the first sight):
-- W.wornOf: true when isWorn() answers true, else nil (elided). The jar: InventoryItem.isWorn @0-@19 L4247 answers
-- IsClothing() and the Clothing override, Clothing.isWorn @0-@43 L1296: the item's container's parent is a character
-- whose getWornItems() contains it. An absent member reads not worn.
function W.wornOf(it)
    if reads(it, "isWorn", true) then return true end
    return nil
end

-- the fabric class the rip recipes read, else nil (elided): hasTag(ItemTag.RIP_CLOTHING_COTTON) cotton (the
-- RipClothing recipe's tags[base:ripclothingcotton], scripts/generated/recipes/recipes.txt:226, #4300), else
-- RIP_CLOTHING_DENIM denim, else RIP_CLOTHING_LEATHER leather (the tool recipe's tags[base:ripclothingdenim;
-- base:ripclothingleather], :243). The jar: ItemTag.<clinit> registers RipClothingCotton @3047-@3053 L350,
-- RipClothingDenim @3056-@3062 L351 and RipClothingLeather @3065-@3071 L352; InventoryItem.hasTag(ItemTag) @0-@8
-- L2841 asks the script item. ItemTag or a constant absent reads no class.
W.RIP_TAGS = { { "RIP_CLOTHING_COTTON", "cotton" }, { "RIP_CLOTHING_DENIM", "denim" },
               { "RIP_CLOTHING_LEATHER", "leather" } }

function W.ripOf(it)
    if ItemTag == nil then return nil end
    for _, t in ipairs(W.RIP_TAGS) do
        local tag = ItemTag[t[1]]
        if tag ~= nil and reads(it, "hasTag", true, tag) then return t[2] end
    end
    return nil
end

-- ---- the clothing record (PZA/1.6, Task 9 fix 9, review-t18 ruling 5) ---------------------------------------------
-- W.clothingOf(it): nil for an item whose class is not Clothing, else { loc, bite, scratch, bullet, cond, condMax,
-- holes, worn }, each field nil when its member is absent or answers no number (worn: a boolean). The jar (jar-reads-2
-- section 10): loc is tostring(getBodyLocation()), the ItemBodyLocation's registry name (ItemBodyLocation.toString
-- @0-@10 L134, as base:tshirt), the slot WornItems.setItem replaces (one item a location, but for a multi-item group);
-- bite, scratch and bullet are Clothing.getBiteDefense @0-@13 L890-L893, getScratchDefense @0-@13 L902-L905 and
-- getBulletDefense @0-@13 L504-L507, each 0 while getCondition() is 0 or less; cond and condMax are getCondition and
-- getConditionMax; holes is getHolesNumber @0-@16 L946-L949 (the visual's holes, 0 without a visual); worn is
-- isWorn() (Clothing.isWorn @0-@43 L1296). A zombie's scratch or laceration rolls Rand.Next(100) against the summed
-- scratch defence of the worn items covering the hit part without a hole there, a bite against the bite defence, capped
-- at 100 (IsoGameCharacter.getBodyPartClothingDefense, BodyDamage.AddRandomDamageFromZombie), so a garment's bite and
-- scratch are what it adds to the parts its location covers.
local function numOr(it, member)
    local ok, v = PZA.call(it, member)
    if ok and type(v) == "number" then return v end
    return nil
end

function W.locOf(it)
    local ok, loc = PZA.call(it, "getBodyLocation")
    if not ok or loc == nil then return nil end
    local s = tostring(loc)
    if s == "" then return nil end
    return s
end

function W.clothingOf(it)
    if not W.isA(it, "Clothing") then return nil end
    local c = { loc = W.locOf(it), bite = numOr(it, "getBiteDefense"), scratch = numOr(it, "getScratchDefense"),
                bullet = numOr(it, "getBulletDefense"), cond = numOr(it, "getCondition"),
                condMax = numOr(it, "getConditionMax"), holes = numOr(it, "getHolesNumber") }
    local okW, worn = PZA.call(it, "isWorn")
    if okW then c.worn = worn == true end
    return c
end
