-- TKX_Nutrient server side -- the three candidate routes a nutrient field can take, one per
-- tick of EveryOneMinute. At the fixture's DayLength = 4 with `settimespeed 1` that event
-- fires every 3.75 real seconds, so no time acceleration and no [sandbox] block is needed.
--
--  arm 1  player modData write, NEVER transmitted        -> md.TKX_fibre = <tick count>
--  arm 2  server-driven player:transmitModData()         -> armed by md.TKX_transmit_now,
--         which the driver sets with `moddata.set admin TKX_transmit_now 1`. This is the
--         server->client direction; the library has only ever measured client->server, where
--         the transmit is a whole-table wipe-and-replace (patterns.md FILTER 10).
--  arm 3  per-ITEM modData + syncItemFields()            -> Base.Cheese, once per instance.
--
-- Own six-line guard; the harness's TK is never referenced.
local function tkxCall(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return pcall(m, obj, ...)
end

-- arm 3. Once per instance: the presence of the key IS the "already done" flag, so a restart
-- that reloads the same item does not double-count itemWrites.
local function markCheese(item)
    local okType, full = tkxCall(item, "getFullType")
    if not okType or full ~= "Base.Cheese" then return end
    local okMd, imd = tkxCall(item, "getModData")
    if not okMd or imd == nil then return end
    if imd.TKX_fibre ~= nil then return end
    imd.TKX_fibre = 12.5
    tkxCall(item, "syncItemFields")
    TKX_Nutrient.itemWrites = TKX_Nutrient.itemWrites + 1
end

-- Java lists are walked with size()/get(i) from 0: `#` on an ArrayList is a Kahlua trap.
local function walkItems(container)
    local okItems, items = tkxCall(container, "getItems")
    if not okItems or items == nil then return end
    local okSize, size = tkxCall(items, "size")
    if not okSize or size == nil then return end
    local i = 0
    while i < size do
        local okGet, item = tkxCall(items, "get", i)
        if okGet and item ~= nil then markCheese(item) end
        i = i + 1
    end
end

local function eachPlayer(player)
    local okMd, md = tkxCall(player, "getModData")
    if not okMd or md == nil then return end
    md.TKX_fibre = TKX_Nutrient.ticks                       -- arm 1: write, never transmit
    if md.TKX_transmit_now ~= nil then                      -- arm 2: server -> client push
        md.TKX_transmit_now = nil
        tkxCall(player, "transmitModData")
    end
    local okInv, inv = tkxCall(player, "getInventory")
    if okInv and inv ~= nil then walkItems(inv) end
end

local function tick()
    if TKX_Nutrient == nil then return end          -- shared/ not loaded: nothing to witness
    TKX_Nutrient.side = "server"
    TKX_Nutrient.ticks = TKX_Nutrient.ticks + 1
    if getOnlinePlayers == nil then return end
    local okList, players = pcall(getOnlinePlayers)
    if not okList or players == nil then return end
    local okSize, size = tkxCall(players, "size")
    if not okSize or size == nil then return end
    local i = 0
    while i < size do
        local okGet, player = tkxCall(players, "get", i)
        if okGet and player ~= nil then eachPlayer(player) end
        i = i + 1
    end
end

Events.EveryOneMinute.Add(tick)
