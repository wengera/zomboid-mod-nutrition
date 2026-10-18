-- NR_Server_Backup.lua -- the record's backup on the character (Plan 16 Task 3, spec section 1.4): a copy of the
-- player's stored record kept in the character's own modData, so a lost or corrupt store file, or a store file left
-- ahead of a world a hard kill rolled back, restores from what the world saved with the character (NR_Server_Store's
-- load rule, S.pick). The store's file stays the authoritative copy; this one is read only by that rule.
--
-- The copy: modData key NutritionRevamp.backup = { n, parts, sum, age }. parts holds the store slot's own text (the
-- one K.json document F.save writes: { gen, rec = K.store.inputsOnly, done = true }, so there is no second format and
-- no second encode) cut into n strings of at most BK.PART characters: the engine saves a modData string, and sends a
-- command's, with a 16-bit length (GameWindow$StringUTF.save @20-@27 L1419-L1420 on the 42.21 jar, `i2s` before
-- putShort), so one longer string would be cut. age is the world age the store step ran at; sum is BK.sum of the text
-- and age.
--
-- The write (BK.write): only from F.save, so at the store's save cadence (at most once a real minute a player, and
-- after an eat, a drink or a respawn's reset), never per minute; a departure's flush has no player and writes none.
-- The same table is sent to the owning client (command "backup"), whose NR_Client_Mirror lays it in its own player's
-- modData: a client's transmitModData replaces the server's whole table (#1042, #1151), so the client must hold the
-- copy too or any other mod's transmit would wipe it.
--
-- The read (BK.read): a copy is rejected, counted by reason in BK.stats.rejected and logged at level 2, when it is
-- absent or not a table (a wipe), its parts are not n strings or its text does not decode to the store's document for
-- this username (garbled), its sum does not match (edited), or its age or its record's latest stamp
-- (K.resume.latest) is past the world clock (a copy from a world that has not happened). A player with no readable
-- modData answers "unavailable" and is not counted. The sum catches a wipe, a truncation and a stray edit; it is not
-- a signature, so a client that rebuilds a matching sum can forge a copy, which only the load rule's two cases read.
--
-- Rule 6: a write cuts the text and sums it (one string.byte call per four characters) and makes one modData
-- assignment and one send, once a save; no read happens outside a first sight. Runs in both Lua states; the write
-- and the send run only behind the store's isServer() path. Slow-clock code: no @fastpath region in this file.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.backup = {
    module = "NutritionRevamp",
    KEY = "NutritionRevamp",   -- the modData key; the copy is its field backup
    PART = 8000,               -- not science (no row): characters a part, under the 16-bit string length the engine saves at
    MAX_PARTS = 64,            -- not science (no row): a copy longer than 512 000 characters is garbled
    MOD = 2147483647,          -- not science (no row): the sum's modulus, the prime 2^31 - 1, so every step is exact in a double
    stats = { writes = 0, sends = 0, sendFailures = 0, bytes = 0, reads = 0, restored = 0, aheadKept = 0,
              rejected = { absent = 0, garbled = 0, sum = 0, ahead = 0 } },
}
local BK = NR.server.backup

-- The sum of text and the world age ageH: a base-31 polynomial of the code units modulo BK.MOD, four units a step,
-- then the age in whole game seconds. A whole number in [0, BK.MOD).
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

-- The copy of text at world age ageH: { n, parts, sum, age }.
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

-- The player's modData table, or nil when the member is absent, raises or answers no table.
local function modData(player)
    local ok, present, md = pcall(NR.call, player, "getModData")
    if not ok or not present or type(md) ~= "table" then return nil end
    return md
end

-- The backup of the store text written at world age ageH, on player and on the owning client. False when the player
-- has no modData or the age is not finite (nothing written).
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
    if sendServerCommand ~= nil then
        if pcall(sendServerCommand, player, BK.module, "backup", doc) then
            BK.stats.sends = BK.stats.sends + 1
        else
            BK.stats.sendFailures = BK.stats.sendFailures + 1
        end
    end
    return true
end

-- A rejection: counted by reason and logged at level 2. Answers nil, nil, why.
local function reject(username, why)
    BK.stats.rejected[why] = BK.stats.rejected[why] + 1
    NR.log.say(2, "backup: " .. tostring(username) .. "'s backup rejected (" .. why .. ")")
    return nil, nil, why
end

-- The text of a copy's parts, or nil when n or a part is not what the copy says.
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

-- The validated backup on player for username at world age ageH: the stored record (raw, as a slot file's rec),
-- its generation and the copy's age; or nil, nil and the reason (the header's rules; "unavailable" with no modData).
function BK.read(player, username, ageH)
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
    local latest = K.resume.latest(t.rec)
    if NR.finite(ageH) and (doc.age > ageH or (latest ~= nil and latest > ageH)) then
        return reject(username, "ahead")
    end
    return t.rec, t.gen, doc.age
end
