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
