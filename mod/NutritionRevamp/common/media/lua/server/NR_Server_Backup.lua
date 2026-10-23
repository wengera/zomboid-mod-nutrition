-- NR_Server_Backup.lua: the record's backup in the character's own modData, read only by the store's load rule
-- (S.pick) when the store file is lost or ahead of a world a hard kill rolled back. The engine saves the character
-- to players.db on its own cadence (every 180 real seconds online, at a disconnect, at a world save; ServerPlayerDB),
-- so after a hard kill the copy matches the restored character and usually sits ahead of the rolled-back clock: its
-- normal state, which K.resume.resume moves back.
-- The copy (NutritionRevamp.backup = { n, parts, sum, age }) is the store slot's own text cut into parts of at most
-- BK.PART characters: the engine saves a modData string with a signed 16-bit byte count (StringUTF.save L1419), so a
-- string over 32767 bytes is lost; PART stays at or under 10922 (backup.PART's max) to fit 3 bytes a character.
-- Written only from F.save, at the store's cadence. The copy is never sent to the client: it would multiply the mod's
-- server-to-client traffic 3.5-5.5 times. So a client's transmitModData (another mod's) replaces the whole table
-- (#1042) and wipes the copy until the next save.
-- The read rejects a wiped, garbled or edited copy (by reason, logged). The sum is not a signature: a client that
-- rebuilds a matching sum can forge a copy, which only the load rule's two cases read.
-- Rule 6: a write cuts and sums the text once a save; no read happens outside a first sight.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.backup = {
    KEY = "NutritionRevamp",   -- the modData key; the copy is its field backup
    PART = K.dials.get("backup.PART"),
    MAX_PARTS = K.dials.get("backup.MAX_PARTS"),
    MOD = 2147483647,          -- not science (no row): the sum's modulus, the prime 2^31 - 1, so every step is exact in a double
    stats = { writes = 0, bytes = 0, reads = 0, restored = 0, aheadKept = 0,
              rejected = { absent = 0, garbled = 0, sum = 0 } },
}
local BK = NR.server.backup

-- A base-31 polynomial of the code units modulo BK.MOD, four units a step, then the age in whole game seconds.
function BK.sum(text, ageH)
    local M = BK.MOD
    local n = string.len(text)
    local h = n % M
    local i = 1
    while i <= n do
        local a, b, c, d = string.byte(text, i, i + 3)
        h = (h * 923521 + a * 29791 + (b or 0) * 961 + (c or 0) * 31 + (d or 0)) % M   -- 31^4, 31^3, 31^2, 31
        i = i + 4
    end
    return (h * 31 + math.floor(ageH * 3600)) % M
end

function BK.doc(text, ageH)
    local parts = {}
    local n = string.len(text)
    local i = 1
    while i <= n do
        parts[#parts + 1] = string.sub(text, i, i + BK.PART - 1)
        i = i + BK.PART
    end
    return { n = #parts, parts = parts, sum = BK.sum(text, ageH), age = ageH }
end

-- nil when the member is absent, raises or answers no table.
local function modData(player)
    local ok, present, md = pcall(NR.call, player, "getModData")
    if not ok or not present or type(md) ~= "table" then return nil end
    return md
end

-- False when the player has no modData or the age is not finite (nothing written).
function BK.write(player, text, ageH)
    if type(text) ~= "string" or not NR.finite(ageH) then return false end
    local md = modData(player)
    if md == nil then return false end
    local doc = BK.doc(text, ageH)
    local root = md[BK.KEY]
    if type(root) ~= "table" then
        root = {}
        md[BK.KEY] = root
    end
    root.backup = doc
    BK.stats.writes = BK.stats.writes + 1
    BK.stats.bytes = BK.stats.bytes + string.len(text)
    return true
end

-- Answers nil, nil, why.
local function reject(username, why)
    BK.stats.rejected[why] = BK.stats.rejected[why] + 1
    NR.log.say(2, "backup: " .. tostring(username) .. "'s backup rejected (" .. why .. ")")
    return nil, nil, why
end

-- nil when n or a part is not what the copy says.
local function textOf(doc)
    local n = doc.n
    if type(n) ~= "number" or n < 1 or n > BK.MAX_PARTS or n ~= math.floor(n) or type(doc.parts) ~= "table" then
        return nil
    end
    local out = {}
    for i = 1, n do
        local s = doc.parts[i]
        if type(s) ~= "string" then return nil end
        out[i] = s
    end
    return table.concat(out)
end

-- Or nil, nil and the reason ("unavailable" with no modData, uncounted).
function BK.read(player, username)
    local md = modData(player)
    if md == nil then return nil, nil, "unavailable" end
    BK.stats.reads = BK.stats.reads + 1
    local root = md[BK.KEY]
    local doc = type(root) == "table" and root.backup or nil
    if type(doc) ~= "table" then return reject(username, "absent") end
    local text = textOf(doc)
    if text == nil or not NR.finite(doc.age) then return reject(username, "garbled") end
    if BK.sum(text, doc.age) ~= doc.sum then return reject(username, "sum") end
    local ok, t = pcall(K.json.decode, text)
    if not ok or type(t) ~= "table" or t.done ~= true or type(t.gen) ~= "number" or type(t.rec) ~= "table"
        or t.rec.username ~= username then
        return reject(username, "garbled")
    end
    return t.rec, t.gen, doc.age
end
