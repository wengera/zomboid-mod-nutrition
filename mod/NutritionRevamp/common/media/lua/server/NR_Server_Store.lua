-- NR_Server_Store.lua -- the durable per-player store (Plan 11 Task 11, Decision 3): an in-memory table of the
-- records seen this uptime, persisted per player to two alternating JSON slot files under the server's Lua cache
-- folder through getFileWriter, with a real-time last-seen index pruned at NR.RecordKeepDays; nothing per-player is
-- kept under a global modData name (#3417: any client could request it). A pruned player's slots are emptied, not
-- deleted: Lua has no file delete or rename (J2). The folder is keyed by the server name, so a world wiped under the
-- same name finds the old files, and every returning player's record, resets included, carries over; an operator
-- who wants a fresh start deletes the folder by hand. The load at first sight (fillInPlace) is kept as before.
-- Inputs only (K.store.inputsOnly), never transmitted (#2416) and never player modData (#1042). Runs in both Lua
-- states; every write below is behind NutritionRevamp.isServer().
--
-- The files (42.21 jar, Task 2's J2: T1102.3, T1102.4, T1102.6). getFileWriter TRUNCATES the file at the call, not
-- at close, so the writer never opens the file of a pair that holds the newest complete copy: a host killed
-- between open and close loses only the file being written, and the other still holds the last complete one. The
-- index (real-time last-seen stamps) is a pair too, index_a.json and index_b.json, for the same reason: one index
-- file emptied by a crash mid-write would lose every stamp, and a player who never came back would never be pruned.
-- Each file is one JSON object on one line, written with ONE write (writeln appends the host's separator, CRLF on
-- Windows) and read with getFileReader(path, false) (true would create an empty file; a missing file reads nil).
-- The guard: LuaFileWriter is a PrintWriter, which swallows I/O errors, so writeFailures counts only a writer that
-- came back nil or raised; a torn or failed write is caught on read, where a file that does not decode to an object
-- carrying done = true and its gen is a read failure and the other file of the pair wins. The server name is passed
-- through K.store.safeName (it is not sanitised, and a name holding .. would make every write nil); a nil writer is
-- counted every time and logged once.
--
-- The load (Plan 8 ruling 5, ruling T4-1): the first S.get of a username in a sight -- the players' queue calls it
-- at first sight, before the first-sight hooks; a mirror request or an eat that comes first takes it -- reads the
-- newest slot when the record is not in memory, then runs K.store.fillInPlace on the record: the inputs are kept,
-- every derived field dropped for the slow minute to rebuild, and the version set to K.store.VERSION, all in the
-- record's OWN table, so every handle held on it reads the loaded record with no re-point. The load is idempotent
-- and runs at every first sight (derived on read); a record whose version moved logs
-- "store: migrated <username> v<old> -> v<new>" once (a record with no version is v1). A departure forgets the sight,
-- so a return loads again, and queues the record's flush and an index write as one task. A load that raises leaves
-- the record as it was, logged.
--
-- The writes ride the players' queue (Decision 6 (b)): a player's slot is written at most once a real minute from
-- its own minute (the pipeline's "store" step); a departure's flush and the hourly prune are one-shot tasks. A task
-- name carries a "." ("store.flush.<hex>", "store.prune"), which no username can: ServerWorldDatabase.isValidUserName
-- refuses a name holding "." (42.21 @75-@81 L776) and authClient refuses an invalid name (@61-@84 L1041-L1044), and a
-- task named like an online user would be merged into that user's queue entry and never run.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.store = { name = "NutritionRevamp.players", records = nil, loaded = {}, loadedFor = nil, wired = false,
                    stats = { loads = 0, migrations = 0, created = 0, failures = 0 },
                    file = { root = nil, index = {}, indexGen = 0, indexAt = nil, gen = {}, at = {}, lastWrite = {},
                             lastPrune = nil, fmt = tostring, warned = false,
                             stats = { writes = 0, reads = 0, readFailures = 0, writeFailures = 0, pruned = 0,
                                       migrated = 0, kept = 0, bytes = 0 } } }
local S = NR.server.store
local F = S.file

S.SAVE_GAP_MS = 60000      -- game choice (ruling 8): a player's slot is written at most once a real minute
S.PRUNE_GAP_MS = 3600000   -- game choice (ruling 8): the prune walks the index once a real hour

local function nowMs()
    if getTimestampMs == nil then return nil end
    local ok, v = pcall(getTimestampMs)
    if ok and type(v) == "number" then return v end
    return nil
end

local function other(which)
    if which == "a" then return "b" end
    return "a"
end

-- The in-memory records: never ModData.getOrCreate (that would recreate the requestable table).
function S.attach()
    if S.records == nil then S.records = {} end
    return S.records
end

-- A fresh record at the current version (K.store.new: the identity fields and the satiety seed).
function S.new(username, worldAgeHours)
    return K.store.new(username, worldAgeHours)
end

-- The sight set of the records table t: a different table than the one the set was kept for starts empty.
local function sights(t)
    if S.loadedFor ~= t then
        S.loaded = {}
        S.loadedFor = t
    end
    return S.loaded
end

-- The load of a stored record r, in place (the header). Returns r.
function S.load(username, r)
    local old = r.v
    if old == nil then old = 1 end
    local records = NR.data and NR.data.records
    local ok, err = pcall(K.store.fillInPlace, r, r, records and records.ORDER, records)
    if not ok then
        S.stats.failures = S.stats.failures + 1
        NR.log.say(2, "store: load failed for " .. tostring(username) .. ": " .. tostring(err))
        return r
    end
    S.stats.loads = S.stats.loads + 1
    if r.v ~= old then
        S.stats.migrations = S.stats.migrations + 1
        NR.log.say(2, "store: migrated " .. tostring(username) .. " v" .. tostring(old) .. " -> v" .. tostring(r.v))
    end
    return r
end

-- The file root: NutritionRevamp/<server name>/ under the Lua cache folder (the folder is per host, J2).
function F.dir()
    if F.root == nil then
        local name = ""
        if getServerName ~= nil then
            local ok, v = pcall(getServerName)
            if ok and type(v) == "string" then name = v end
        end
        F.root = "NutritionRevamp/" .. K.store.safeName(name) .. "/"
    end
    return F.root
end

function F.slot(username, which)
    return F.dir() .. "p_" .. K.store.hexName(username) .. "_" .. which .. ".json"
end

function F.indexPath(which)
    return F.dir() .. "index_" .. which .. ".json"
end

-- One file written whole: open (which truncates), one write, close. False when the writer came back nil or raised,
-- or a member raised (counted); a write the PrintWriter swallowed reads true here and is caught on read.
function F.write(path, text)
    if getFileWriter == nil then return false end
    local ok, w = pcall(getFileWriter, path, true, false)
    if not ok or w == nil then
        F.stats.writeFailures = F.stats.writeFailures + 1
        if not F.warned then
            F.warned = true
            NR.log.say(1, "store: getFileWriter answered nil for " .. tostring(path)
                .. "; the store is not persisted (counted in store.file.stats.writeFailures; logged once)")
        end
        return false
    end
    local okW = pcall(NR.call, w, "write", text)
    local okC = pcall(NR.call, w, "close")
    if not okW or not okC then
        F.stats.writeFailures = F.stats.writeFailures + 1
        return false
    end
    F.stats.writes = F.stats.writes + 1
    F.stats.bytes = F.stats.bytes + string.len(text)
    return true
end

function F.read(path)
    if getFileReader == nil then return nil end
    local ok, r = pcall(getFileReader, path, false)
    if not ok or r == nil then return nil end
    local parts = {}
    while true do
        local okL, present, line = pcall(NR.call, r, "readLine")
        if not okL or not present or line == nil then break end
        parts[#parts + 1] = line
    end
    pcall(NR.call, r, "close")
    F.stats.reads = F.stats.reads + 1
    return table.concat(parts, "\n")
end

-- One file of a pair decoded: the object, or nil. A missing or empty file is nil and uncounted; one that does not
-- decode (torn, or nested past the decoder's stack: the decode runs under pcall) or lacks done, gen or its body
-- table is a read failure, logged.
local function readDoc(path, body)
    local text = F.read(path)
    if text == nil or text == "" then return nil end
    local okD, t, err = pcall(K.json.decode, text)
    if not okD then
        err = t
        t = nil
    end
    if type(t) ~= "table" or t.done ~= true or type(t.gen) ~= "number" or type(t[body]) ~= "table" then
        F.stats.readFailures = F.stats.readFailures + 1
        NR.log.say(2, "store: " .. tostring(path) .. " unreadable: " .. tostring(err))
        return nil
    end
    return t
end

-- The newest complete slot's raw record, or nil; it remembers which slot holds it, so the next save opens the other.
function F.load(username)
    local docs = { a = readDoc(F.slot(username, "a"), "rec"), b = readDoc(F.slot(username, "b"), "rec") }
    local which = K.store.newest(docs.a, docs.b)
    if which == nil then return nil end
    F.gen[username] = docs[which].gen
    F.at[username] = which
    return docs[which].rec
end

-- One player's record into the slot that does NOT hold the newest complete copy: { gen, rec = the inputs,
-- done = true } on one line. A failed write leaves the newest where it was, so the next save opens the same slot.
function F.save(username, record)
    if record == nil then return false end
    if F.gen[username] == nil then F.load(username) end
    local gen = (F.gen[username] or 0) + 1
    local which = other(F.at[username])
    local text = K.json.encode({ gen = gen, rec = K.store.inputsOnly(record), done = true }, F.fmt)
    if not F.write(F.slot(username, which), text) then return false end
    F.gen[username] = gen
    F.at[username] = which
    local now = nowMs()
    if now ~= nil then
        F.lastWrite[username] = now
        F.index[username] = K.store.seconds(now)
    end
    return true
end

-- The index into the file of its pair that does not hold the newest complete copy.
function F.writeIndex()
    local gen = F.indexGen + 1
    local which = other(F.indexAt)
    local text = K.json.encode({ v = 1, gen = gen, players = F.index, done = true }, F.fmt)
    if not F.write(F.indexPath(which), text) then return false end
    F.indexGen = gen
    F.indexAt = which
    return true
end

function F.readIndex()
    local docs = { a = readDoc(F.indexPath("a"), "players"), b = readDoc(F.indexPath("b"), "players") }
    local which = K.store.newest(docs.a, docs.b)
    if which == nil then return end
    F.index = docs[which].players
    F.indexGen = docs[which].gen
    F.indexAt = which
end

function S.get(username, worldAgeHours)
    local t = S.attach()
    local seen = sights(t)
    local r = t[username]
    if r == nil then
        r = F.load(username)
        if r ~= nil then t[username] = r end
    end
    if r == nil then
        -- Plan 11 Task 3: a failed clock read never creates a record stamped 0
        if worldAgeHours == nil then return nil end
        r = S.new(username, worldAgeHours)
        t[username] = r
        seen[username] = true
        S.stats.created = S.stats.created + 1
        NR.log.say(3, "store: new record for " .. tostring(username))
        return r
    end
    if seen[username] ~= true then
        seen[username] = true
        S.load(username, r)
    end
    return r
end

-- A departure flush: the record held now (a pruned one is gone and only the index is written), then the index.
local function flush(username)
    local r = S.records and S.records[username]
    if r ~= nil then F.save(username, r) end
    F.writeIndex()
end

-- A departure: the sight forgotten, so the next first sight loads the record again, and the record's flush and an
-- index write queued as one task (it rides the budget), so the index never trails the slot files by more than one
-- departure.
function S.forget(username)
    if username == nil then return end
    if S.loaded ~= nil then S.loaded[username] = nil end
    local P = NR.server.players
    if P ~= nil and P.task ~= nil and S.records ~= nil and S.records[username] ~= nil then
        P.task("store.flush." .. K.store.hexName(username), function() flush(username) end)
    end
end

-- A respawn: the character is new, the record starts fresh, the reset count carries over so a later reading can
-- tell a returning player from a new one. S.reset REPLACES the table (the one place a handle held on the record goes
-- stale until it is read again).
function S.reset(username, worldAgeHours)
    local t = S.attach()
    local old = t[username]
    if old == nil then old = F.load(username) end
    local r = S.new(username, worldAgeHours)
    if old ~= nil then
        r.resets = (old.resets or 0) + 1                   -- ruling 4: every OnNewGame over an existing record
    else
        r.resets = 0                                       -- a first character
    end
    t[username] = r
    sights(t)[username] = true
    NR.log.say(2, "store: reset record for " .. tostring(username) .. " (reset " .. tostring(r.resets) .. ")")
    return r
end

-- The pipeline's store step: the player's slot written when a real minute has passed since its last write.
function S.step(username, player, record, ctx)
    local now = nowMs()
    if now == nil or record == nil then return end
    if not K.store.due(F.lastWrite[username], now, S.SAVE_GAP_MS) then return end
    F.save(username, record)
end

-- The prune: offline players unseen for more than keepDays real days lose their record. Both slots are EMPTIED, not
-- deleted -- Lua has no delete or rename (J2) -- so an emptied pair reads as no record; the index entry and the
-- in-memory record are dropped, and the index is written (keepDays 0 keeps everything and still writes it, so the
-- online players' stamps reach the file once an hour). Returns the count.
function S.prune(now, keepDays)
    if now == nil or keepDays == nil then return 0 end
    local P = NR.server.players
    local online = (P and P.online) or {}
    local doomed = K.store.expired(F.index, K.store.seconds(now), K.store.keepSeconds(keepDays), online)
    for i = 1, #doomed do
        local u = doomed[i]
        F.write(F.slot(u, "a"), "")
        F.write(F.slot(u, "b"), "")
        F.index[u] = nil
        F.gen[u] = nil
        F.at[u] = nil
        F.lastWrite[u] = nil
        if S.records ~= nil then S.records[u] = nil end
        if S.loaded ~= nil then S.loaded[u] = nil end
    end
    F.stats.pruned = F.stats.pruned + #doomed
    F.lastPrune = now
    F.writeIndex()
    if #doomed > 0 then
        NR.log.say(1, "store: pruned " .. tostring(#doomed) .. " record(s) unseen for " .. tostring(keepDays) .. " real days")
    end
    return #doomed
end

-- The migration (at OnServerStarted, every boot while the old table exists): a username whose slot files already
-- hold a record is never written (F.load answered: the files are newer than any global copy, which a crash before
-- the world save can bring back; ruling 16); every other record is written to its slot and read back. Only when no
-- record failed is the global table removed, so the leak closes (#3417). A second run changes nothing.
function F.migrate()
    if ModData == nil or ModData.exists == nil then return 0 end
    local okE, has = pcall(ModData.exists, S.name)
    if not okE or has ~= true then return 0 end
    local okG, old = pcall(ModData.get, S.name)
    if not okG or type(old) ~= "table" then return 0 end
    local n, kept, bad = 0, 0, 0
    for username, rec in pairs(old) do
        if type(username) == "string" and type(rec) == "table" then
            if F.load(username) ~= nil then
                kept = kept + 1
            elseif F.save(username, rec) and F.load(username) ~= nil then
                n = n + 1
            else
                bad = bad + 1
            end
        end
    end
    F.stats.migrated = F.stats.migrated + n
    F.stats.kept = F.stats.kept + kept
    if bad > 0 then
        NR.log.say(1, "store: " .. tostring(bad) .. " record(s) did not read back; the global table is kept until the next boot")
        return n
    end
    pcall(ModData.remove, S.name)
    F.writeIndex()
    NR.log.say(1, "store: migrated " .. tostring(n) .. " record(s) from global modData to " .. F.dir() .. " ("
        .. tostring(kept) .. " already on file, left as they were); the global table removed")
    return n
end

local function keepDays()
    local o = NR.server.options
    if o ~= nil and type(o.recordKeepDays) == "number" then return o.recordKeepDays end
    return 30
end

local function pruneNow()
    S.prune(nowMs(), keepDays())
end

-- Wiring at OnServerStarted (this file sorts after NR_Server_Options and NR_Server_Players): the index read, the
-- migration and a first prune (no player is online yet), the departure hook and the pipeline's "store" step.
if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        if S.wired then return end
        S.wired = true
        S.attach()
        F.readIndex()
        F.migrate()
        pruneNow()
        local P = NR.server.players
        if P ~= nil then P.onDeparture[#P.onDeparture + 1] = S.forget end
        NR.server.minute.register("store", S.step)
    end)
end

-- The hourly prune, queued as a one-shot task so it runs in a queue slot under the budget, not in the minute event.
if Events ~= nil and Events.EveryOneMinute ~= nil then
    Events.EveryOneMinute.Add(function()
        if not NR.isServer() then return end
        local now = nowMs()
        if now == nil or not K.store.due(F.lastPrune, now, S.PRUNE_GAP_MS) then return end
        F.lastPrune = now
        local P = NR.server.players
        if P ~= nil and P.task ~= nil then
            P.task("store.prune", pruneNow)
        else
            pruneNow()
        end
    end)
end
