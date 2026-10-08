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
-- A swallowed write never costs the newest copy (Task 11 fix 1): the text last written (or read) per file pair is
-- kept (F.last[username], F.lastIndex), and before the writer opens the other file of a pair it reads the file it
-- believes holds the newest copy back and compares it as a string, with no decode. A mismatch means that write was
-- swallowed: the same file is rewritten instead (the other one still holds the last complete copy), counted in
-- store.file.stats.repaired and logged once per player. The cost is one file read per save (a player's slot at most
-- once a real minute) and per index write.
-- A transient read failure never resets a record whose files the index names: a record S.get created fresh this
-- sight (S.fresh) whose files the save's preload then finds is filled from the file in place and that save skipped,
-- and one whose preload reads nothing while the index names the player is deferred (nothing opened, counted in
-- store.file.stats.deferred, logged once, the flag kept so the next save tries again), so the fresh record never
-- overwrites the real one (logged at level 2); the flag clears at the first save and at a reset. A player first seen
-- after the last index write has no such protection: the index does not name them, so two failed reads save them new.
--
-- The load (Plan 8 ruling 5, ruling T4-1): the first S.get of a username in a sight -- the players' queue calls it
-- at first sight, before the first-sight hooks; a mirror request or an eat that comes first takes it -- reads the
-- newest slot when the record is not in memory, then runs K.store.fillInPlace on the record: the inputs are kept,
-- every derived field dropped for the slow minute to rebuild, and the version set to K.store.VERSION, all in the
-- record's OWN table, so every handle held on it reads the loaded record with no re-point. The load is idempotent
-- and runs at every first sight (derived on read); a record whose version moved logs
-- "store: migrated <username> v<old> -> v<new>" once (a record with no version is v1). A departure forgets the sight,
-- so a return loads again, and queues the record's flush as one task. A load that raises leaves the record as it
-- was, logged.
--
-- The writes ride the players' queue (Decision 6 (b)): a player's slot is written at most once a real minute from
-- its own minute (the pipeline's "store" step), the first after a sight at the player's own phase over that minute
-- (K.store.savePhase), so the players seen at a boot do not all save in one drain; a departure's flush, the index
-- write and the hourly prune are one-shot tasks. The index is debounced (Task 11 fix 1): a departure flush writes
-- only the player's slot and a first save of a username the index lacks marks the index dirty, and the one task
-- "store.index" writes it at most once every S.INDEX_GAP_MS while dirty; the hourly prune writes it too. A task
-- name carries a "." ("store.flush.<hex>", "store.index", "store.prune"), which no username can:
-- ServerWorldDatabase.isValidUserName refuses a name holding "." (42.21 @75-@81 L776) and authClient refuses an
-- invalid name (@61-@84 L1041-L1044), and a task named like an online user would be merged into that user's queue
-- entry and never run.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.store = { name = "NutritionRevamp.players", records = nil, loaded = {}, loadedFor = nil, wired = false,
                    fresh = {}, stats = { loads = 0, migrations = 0, created = 0, failures = 0 },
                    file = { root = nil, index = {}, indexGen = 0, indexAt = nil, gen = {}, at = {}, lastWrite = {},
                             last = {}, lastIndex = nil, indexDirty = false, lastIndexWrite = nil, repairWarned = {},
                             lastPrune = nil, fmt = tostring, warned = false,
                             stats = { writes = 0, reads = 0, readFailures = 0, writeFailures = 0, pruned = 0,
                                       migrated = 0, kept = 0, bytes = 0, repaired = 0, recovered = 0, deferred = 0 }, deferWarned = {} } }
local S = NR.server.store
local F = S.file

S.SAVE_GAP_MS = 60000      -- game choice (ruling 8): a player's slot is written at most once a real minute
S.PRUNE_GAP_MS = 3600000   -- game choice (ruling 8): the prune walks the index once a real hour
S.INDEX_GAP_MS = 300000    -- game choice (Task 11 fix 1): a dirty index is written at most once every 5 real minutes

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

-- One file of a pair decoded: the object and its text, or nil. A missing or empty file is nil and uncounted; one
-- that does not decode (torn, or nested past the decoder's stack: the decode runs under pcall) or lacks done, gen
-- or its body table is a read failure, logged.
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
    return t, text
end

-- Whether the file at path still holds last, the text last written to it or read from it (nil: nothing known, so
-- nothing to compare). A string compare, no decode: one read.
function F.intact(path, last)
    if last == nil then return true end
    return F.read(path) == last
end

-- The file of a pair a write opens: the other file than at, the one holding the newest copy -- unless at's file no
-- longer reads back as last (a swallowed write), when at's own file is rewritten and the other one, the last
-- complete copy, is left alone.
local function target(at, atPath, last, who)
    if at == nil or F.intact(atPath, last) then return other(at) end
    F.stats.repaired = F.stats.repaired + 1
    if not F.repairWarned[who] then
        F.repairWarned[who] = true
        NR.log.say(1, "store: " .. tostring(atPath) .. " did not read back as written (a swallowed write); it is "
            .. "rewritten and the other file, the last complete copy, kept (counted in store.file.stats.repaired; "
            .. "logged once for " .. tostring(who) .. ")")
    end
    return at
end

-- The newest complete slot's raw record, or nil; it remembers which slot holds it, so the next save opens the other.
function F.load(username)
    local a, ta = readDoc(F.slot(username, "a"), "rec")
    local b, tb = readDoc(F.slot(username, "b"), "rec")
    local docs = { a = a, b = b }
    local texts = { a = ta, b = tb }
    local which = K.store.newest(docs.a, docs.b)
    if which == nil then return nil end
    F.gen[username] = docs[which].gen
    F.last[username] = texts[which]
    F.at[username] = which
    return docs[which].rec
end

-- A record S.get created fresh this sight whose files the save's preload found after all (a transient read
-- failure at first sight): the file's record is laid into the in-memory one in place. Returns nothing.
function S.recover(username, record, raw)
    S.fresh[username] = nil
    local records = NR.data and NR.data.records
    local ok, err = pcall(K.store.fillInPlace, record, raw, records and records.ORDER, records)
    if not ok then
        S.stats.failures = S.stats.failures + 1
        NR.log.say(2, "store: recovery failed for " .. tostring(username) .. ": " .. tostring(err))
        return
    end
    F.stats.recovered = F.stats.recovered + 1
    NR.log.say(2, "store: " .. tostring(username) .. " recovered from file after a failed first read")
end

-- One player's record into the slot that does NOT hold the newest complete copy (target: unless a swallowed write
-- left the newest slot unreadable): { gen, rec = the inputs, done = true } on one line. A failed write leaves the
-- newest where it was, so the next save opens the same slot. A record created fresh this sight whose files the
-- preload finds is recovered from them instead of written over them (false: nothing written).
function F.save(username, record)
    if record == nil then return false end
    if F.gen[username] == nil then
        local raw = F.load(username)
        if raw ~= nil and S.fresh[username] == true then
            S.recover(username, record, raw)
            return false
        end
        if raw == nil and S.fresh[username] == true and F.index[username] ~= nil then
            F.stats.deferred = F.stats.deferred + 1
            if not F.deferWarned[username] then
                F.deferWarned[username] = true
                NR.log.say(2, "store: " .. tostring(username) .. " save deferred: files indexed but unreadable")
            end
            return false
        end
    end
    S.fresh[username] = nil
    local gen = (F.gen[username] or 0) + 1
    local which = target(F.at[username], F.slot(username, F.at[username] or "a"), F.last[username], username)
    local text = K.json.encode({ gen = gen, rec = K.store.inputsOnly(record), done = true }, F.fmt)
    if not F.write(F.slot(username, which), text) then return false end
    F.gen[username] = gen
    F.last[username] = text
    F.at[username] = which
    local now = nowMs()
    if now ~= nil then
        F.lastWrite[username] = now
        if F.index[username] == nil then F.indexDirty = true end   -- a first-time player reaches the index file
        F.index[username] = K.store.seconds(now)
    end
    return true
end

-- The index into the file of its pair that does not hold the newest complete copy (target, as F.save). A written
-- index is clean.
function F.writeIndex()
    local gen = F.indexGen + 1
    local which = target(F.indexAt, F.indexPath(F.indexAt or "a"), F.lastIndex, "the index")
    local text = K.json.encode({ v = 1, gen = gen, players = F.index, done = true }, F.fmt)
    if not F.write(F.indexPath(which), text) then return false end
    F.indexGen = gen
    F.indexAt = which
    F.lastIndex = text
    F.indexDirty = false
    F.lastIndexWrite = nowMs()
    return true
end

function F.readIndex()
    local a, ta = readDoc(F.indexPath("a"), "players")
    local b, tb = readDoc(F.indexPath("b"), "players")
    local docs = { a = a, b = b }
    local texts = { a = ta, b = tb }
    local which = K.store.newest(docs.a, docs.b)
    if which == nil then return end
    F.index = docs[which].players
    F.lastIndex = texts[which]
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
        S.fresh[username] = true
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

-- A departure flush: the record held now (a pruned one is gone and nothing is written), and the index marked dirty
-- for the debounced store.index task (ten departures in a minute write it once, not ten times).
local function flush(username)
    local r = S.records and S.records[username]
    if r ~= nil then F.save(username, r) end
    F.indexDirty = true -- the departure's stamp reaches the file at the next store.index task
end

-- A departure: the sight forgotten, so the next first sight loads the record again, and the record's flush queued
-- as a task (it rides the budget); the index follows within S.INDEX_GAP_MS.
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
    S.fresh[username] = nil                                -- a reset record is meant to replace the file's
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

-- The pipeline's store step: the player's slot written when a real minute has passed since its last write; the
-- first write after a boot falls at the player's phase over that minute (K.store.firstLast).
function S.step(username, player, record, ctx)
    local now = nowMs()
    if now == nil or record == nil then return end
    if F.lastWrite[username] == nil then F.lastWrite[username] = K.store.firstLast(username, now, S.SAVE_GAP_MS) end
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
        F.last[u] = nil
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

-- The debounced index write: a clean index (the prune wrote it since) is left alone.
local function indexNow()
    if F.indexDirty then F.writeIndex() end
end

-- A one-shot task on the players' queue, or inline when the queue is absent.
local function queue(name, fn)
    local P = NR.server.players
    if P ~= nil and P.task ~= nil then
        P.task(name, fn)
    else
        fn()
    end
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

-- The dirty index's write and the hourly prune, each queued as a one-shot task so it runs in a queue slot under
-- the budget, not in the minute event.
if Events ~= nil and Events.EveryOneMinute ~= nil then
    Events.EveryOneMinute.Add(function()
        if not NR.isServer() then return end
        local now = nowMs()
        if now == nil then return end
        if F.indexDirty and K.store.due(F.lastIndexWrite, now, S.INDEX_GAP_MS) then queue("store.index", indexNow) end
        if not K.store.due(F.lastPrune, now, S.PRUNE_GAP_MS) then return end
        F.lastPrune = now
        local P = NR.server.players
        if P ~= nil and P.task ~= nil then
            P.task("store.prune", pruneNow)
        else
            pruneNow()
        end
    end)
end
