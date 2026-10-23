-- NR_Server_Store.lua: the durable per-player store: an in-memory table of the records seen this uptime,
-- persisted per player to two alternating JSON slot files under the Lua cache folder through getFileWriter, with a
-- real-time last-seen index; nothing per-player is
-- kept under a global modData name (#3417: any client could request it). A record is kept for good (no prune).
-- The folder is keyed by the server name, so a world wiped under the
-- same name finds the old files, and every returning player's record, resets included, carries over; an operator
-- who wants a fresh start deletes the folder by hand. Inputs only (K.store.inputsOnly), never transmitted (#2416).
-- Player modData is never the authoritative copy (#1042): NR_Server_Backup's copy is read only by the load rule.
-- Every write is behind NutritionRevamp.isServer().
--
-- The files: getFileWriter TRUNCATES the file at the call, not at close,
-- so the writer never opens the file of a pair that holds the newest complete copy: a host killed mid-write loses
-- only that file. The
-- index (real-time last-seen stamps) is a pair too, index_a.json and index_b.json, for the same reason.
-- One JSON object a line, written with ONE write, read with getFileReader(path, false) (true creates an empty file).
-- LuaFileWriter is a PrintWriter, which swallows I/O errors, so a torn write is caught on read, where
-- a file that does not decode to an object
-- carrying done = true and its gen is a read failure and the other file of the pair wins. A swallowed write is also
-- caught before the next open: the file believed newest is read back as a string and rewritten on a mismatch.
-- A transient read failure never resets a record the index names: its save is deferred for S.DEFER_MAX_MS of real
-- time (a step count would be seconds at a short day), then gives up and saves the session record as a new generation.
--
-- The load: the first S.get of a sight reads the newest slot and runs K.store.fillInPlace in the record's OWN table, so
-- every held handle reads it with no re-point; then the resume moves every stamp past the absence, so nothing changes
-- offline, and the return minute runs nothing (S.takeResumed). A sight is keyed on the player object.
--
-- The load rule (S.pick): a missing or unreadable store file, or a store record past the world clock (a hard kill
-- rolled the world back under it, #3280), loads the backup, which the engine's player save keeps in step with the
-- character, so food landed after that snapshot is not eaten twice; otherwise the store wins.
--
-- The writes ride the players' queue: a player's slot is written at most once a real minute from its own minute, at
-- the player's phase (K.store.savePhase); the index is debounced (S.INDEX_GAP_MS). A task name carries a ".", which no
-- username can (isValidUserName, 42.21 L776), so a task is never merged into a user's queue entry.
--
-- No Lua event fires around a world save or a stop. A landed eat or drink (IN.land
-- calls S.mark) and a respawn's reset (S.reset) mark the player's slot dirty, written at the next store step whatever
-- the gap. A clean stop then loses at most the last S.SAVE_GAP_MS of digestion drift; a hard kill is the load rule's.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.store = { records = nil, loaded = {}, loadedFor = nil, wired = false,
                    fresh = {}, filled = {}, resumed = {}, stats = { loads = 0, created = 0, failures = 0, resumes = 0, resumedH = 0 },
                    file = { root = nil, index = {}, indexGen = 0, indexAt = nil, gen = {}, at = {}, lastWrite = {},
                             last = {}, lastIndex = nil, indexDirty = false, lastIndexWrite = nil, repairWarned = {},
                             lastReread = nil, fmt = tostring, warned = false,
                             stats = { writes = 0, reads = 0, readFailures = 0, writeFailures = 0,
                                       bytes = 0, repaired = 0, recovered = 0, deferred = 0, deferGiveUps = 0 }, deferWarned = {}, deferSince = {},
                             dirty = {} } }
local S = NR.server.store
local F = S.file

S.SAVE_GAP_MS = K.dials.get("store.SAVE_GAP_MS")
S.REREAD_GAP_MS = K.dials.get("store.REREAD_GAP_MS")
S.INDEX_GAP_MS = K.dials.get("store.INDEX_GAP_MS")
S.DEFER_MAX_MS = K.dials.get("store.DEFER_MAX_MS")

local nowMs = NR.nowMs

local function other(which)
    if which == "a" then return "b" end
    return "a"
end

-- Also appended to the live queue (P.task alone would wait for the next minute's merge), or inline without one.
local function indexSoon(fn)
    local P = NR.server.players
    if P == nil or P.task == nil or type(P.queue) ~= "table" then
        fn()
        return
    end
    P.task("store.index", fn)
    for i = P.queueHead or 1, #P.queue do
        if P.queue[i] == "store.index" then return end
    end
    P.queue[#P.queue + 1] = "store.index"
end

-- The in-memory records: never ModData.getOrCreate (that would recreate the requestable table).
function S.attach()
    if S.records == nil then S.records = {} end
    return S.records
end

function S.new(username, worldAgeHours)
    return K.store.new(username, worldAgeHours)
end

-- A different table than the one the set was kept for starts empty.
local function sights(t)
    if S.loadedFor ~= t then
        S.loaded = {}
        S.loadedFor = t
    end
    return S.loaded
end

-- A load that raises (a corrupt or hand-edited file) lays a fresh record in target's OWN table, so held handles stay
-- valid; the username and first sight are kept. lastSeen is stamped at ageH, so the minute never reads the gap as a stall.
local function freshInPlace(username, target, firstSeen, ageH)
    local age = firstSeen
    if type(age) ~= "number" or age ~= age then age = NR.worldAge() end   -- nil when unread: P.work stamps lastSeen
    local rec = K.store.new(username, age)
    for k in pairs(target) do target[k] = nil end
    for k, v in pairs(rec) do target[k] = v end
    if NR.finite(ageH) then target.lastSeen = ageH end
    return target
end

-- The header's load, then the resume. Returns r.
function S.load(username, r, worldAgeHours)
    local records = NR.data and NR.data.records
    local ok, err = pcall(K.store.fillInPlace, r, r, records and records.ORDER, records, NR.sexSpecific(), NR.strengthP())
    if not ok then
        S.stats.failures = S.stats.failures + 1
        NR.log.say(1, "store: load failed for " .. tostring(username) .. ": " .. tostring(err) .. "; a fresh record laid")
        S.filled[username] = r
        return freshInPlace(username, r, r.firstSeen, worldAgeHours)
    end
    S.stats.loads = S.stats.loads + 1
    S.filled[username] = r
    S.resume(username, r, worldAgeHours)
    return r
end

-- An unread age moves nothing and leaves the sight unmarked, so the next touch with a clock resumes it.
function S.resume(username, r, ageH)
    local gapH = K.resume.resume(r, ageH)
    if gapH > 0 then
        S.resumed[username] = true
        S.stats.resumes = S.stats.resumes + 1
        S.stats.resumedH = S.stats.resumedH + gapH
        NR.log.say(3, "store: " .. tostring(username) .. " resumed after " .. tostring(gapH) .. " game hours away")
    elseif gapH < 0 then
        S.resumed[username] = true
        S.stats.rewound = (S.stats.rewound or 0) + 1
        NR.log.say(2, "store: " .. tostring(username) .. "'s record moved back " .. tostring(-gapH)
            .. " game hours onto a world clock behind it (a hard-kill rollback)")
    end
end

-- The file root: NutritionRevamp/<server name>/ under the Lua cache folder (the folder is per host).
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

-- False when the writer came back nil or raised; a write the PrintWriter swallowed reads true and is caught on read.
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

-- A missing or empty file is nil and uncounted; a torn one, or one lacking done, gen or body, answers true third.
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
        return nil, nil, true
    end
    return t, text
end

-- A string compare, no decode: one read. nil last knows nothing to compare.
function F.intact(path, last)
    if last == nil then return true end
    return F.read(path) == last
end

-- The other file than at, unless at's file no longer reads back as last (a swallowed write): then at is rewritten.
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

-- Second: whether either slot file is present but unreadable (a missing file is not), which F.save's deferral reads.
local function loadSlots(username)
    local a, ta, badA = readDoc(F.slot(username, "a"), "rec")
    local b, tb, badB = readDoc(F.slot(username, "b"), "rec")
    local docs = { a = a, b = b }
    local texts = { a = ta, b = tb }
    local bad = badA == true or badB == true
    local which = K.store.newest(docs.a, docs.b)
    if which == nil then return nil, bad end
    F.gen[username] = docs[which].gen
    F.last[username] = texts[which]
    F.at[username] = which
    return docs[which].rec, bad
end

function F.load(username)
    return (loadSlots(username))
end

-- A record created fresh this sight whose files the save's preload found after all: filled from the file in place.
function S.recover(username, record, raw)
    S.fresh[username] = nil
    F.deferSince[username] = nil
    local records = NR.data and NR.data.records
    local ok, err = pcall(K.store.fillInPlace, record, raw, records and records.ORDER, records, NR.sexSpecific(), NR.strengthP())
    if not ok then
        S.stats.failures = S.stats.failures + 1
        NR.log.say(1, "store: load failed for " .. tostring(username) .. " (recovery): " .. tostring(err) .. "; a fresh record laid")
        freshInPlace(username, record, record.firstSeen, NR.worldAge())
        return
    end
    S.filled[username] = record
    F.stats.recovered = F.stats.recovered + 1
    NR.log.say(2, "store: " .. tostring(username) .. " recovered from file after a failed first read")
    S.resume(username, record, NR.worldAge())               -- the file's stamps are the departure's
end

-- Into the slot that does NOT hold the newest complete copy; a fresh-this-sight record whose files the preload finds
-- is recovered instead (false). The same text is the player's backup (BK.write), written whether or not the file held.
function F.save(username, record, player, ageH)
    if record == nil then return false end
    if F.gen[username] == nil then
        local raw, bad = loadSlots(username)
        if raw ~= nil and S.fresh[username] == true then
            S.recover(username, record, raw)
            return false
        end
        -- deferred on the slot files themselves (present but unreadable) or on the index, which a locked index
        -- cannot answer; a missing slot never defers, so a new player writes
        if raw == nil and S.fresh[username] == true and (bad or F.index[username] ~= nil) then
            local now = nowMs()
            if F.deferSince[username] == nil then F.deferSince[username] = now end
            local since = F.deferSince[username]
            if since == nil or now == nil or now - since < S.DEFER_MAX_MS then  -- an unread clock never gives up
                F.stats.deferred = F.stats.deferred + 1
                if not F.deferWarned[username] then
                    F.deferWarned[username] = true
                    NR.log.say(2, "store: " .. tostring(username) .. " save deferred: files indexed but unreadable")
                end
                return false
            end
            F.stats.deferGiveUps = F.stats.deferGiveUps + 1
            NR.log.say(1, "store: " .. tostring(username) .. " files indexed but unreadable for "
                .. tostring(math.floor((now - since) / 60000)) .. " real minutes; saving the session record")
        end
    end
    S.fresh[username] = nil
    F.deferSince[username] = nil
    local gen = (F.gen[username] or 0) + 1
    local which = target(F.at[username], F.slot(username, F.at[username] or "a"), F.last[username], username)
    local text = K.json.encode({ gen = gen, rec = K.store.inputsOnly(record), done = true }, F.fmt)
    if player ~= nil and NR.server.backup ~= nil then NR.server.backup.write(player, text, ageH) end
    if not F.write(F.slot(username, which), text) then return false end
    F.gen[username] = gen
    F.last[username] = text
    F.at[username] = which
    local now = nowMs()
    if now ~= nil then
        F.lastWrite[username] = now
        local new = F.index[username] == nil
        F.index[username] = K.store.seconds(now)
        if new then                                        -- a first-time player reaches the index file promptly
            F.indexDirty = true
            indexSoon(S.indexNow)
        end
    end
    return true
end

-- A locked index (F.readIndex) is never written: the call cleans the flag and answers false.
function F.writeIndex()
    if F.indexLocked then
        F.indexDirty = false
        return false
    end
    local gen = F.indexGen + 1
    local which = F.indexPin or target(F.indexAt, F.indexPath(F.indexAt or "a"), F.lastIndex, "the index")
    local text = K.json.encode({ gen = gen, players = F.index, done = true }, F.fmt)
    if not F.write(F.indexPath(which), text) then return false end
    F.indexGen = gen
    F.indexAt = which
    F.lastIndex = text
    F.indexDirty = false
    F.lastIndexWrite = nowMs()
    return true
end

-- When no index file reads and one is unreadable: with the other missing, every write goes to the missing one
-- (F.indexPin); with both unreadable the index is locked for this boot, since alternating writes would overwrite the
-- real index. Logged once each.
function F.readIndex()
    local a, ta, badA = readDoc(F.indexPath("a"), "players")
    local b, tb, badB = readDoc(F.indexPath("b"), "players")
    local docs = { a = a, b = b }
    local texts = { a = ta, b = tb }
    local which = K.store.newest(docs.a, docs.b)
    if which == nil then
        F.indexLocked = badA == true and badB == true
        F.indexPin = nil
        if F.indexLocked then
            if not F.lockWarned then
                F.lockWarned = true
                NR.log.say(1, "store: the index files are present but unreadable; the index is not written this boot "
                    .. "until a restart or an hourly re-read reads it")
            end
        elseif badA or badB then
            F.indexPin = badA and "b" or "a"
            if not F.pinWarned then
                F.pinWarned = true
                NR.log.say(1, "store: " .. F.indexPath(badA and "a" or "b") .. " is unreadable and the other index "
                    .. "file is missing; the index is pinned to " .. F.indexPath(F.indexPin) .. " this boot and the "
                    .. "unreadable file is never opened")
            end
        end
        return
    end
    F.indexLocked = false
    F.indexPin = nil
    local players = docs[which].players
    for u, t in pairs(F.index) do                          -- stamps laid while locked outrank the file's
        if type(t) == "number" and (type(players[u]) ~= "number" or players[u] < t) then players[u] = t end
    end
    F.index = players
    F.lastIndex = texts[which]
    F.indexGen = docs[which].gen
    F.indexAt = which
end

-- That minute is the return, which integrates nothing, so it runs nothing (P.work).
function S.takeResumed(username)
    if S.resumed[username] ~= true then return false end
    S.resumed[username] = nil
    return true
end

-- The generation set one past both the store's and the backup's, so an unread store file never outranks the restore.
function S.restore(username, raw, gen, why)
    F.gen[username] = K.max(F.gen[username] or 0, gen) + 1
    S.mark(username)
    local B = NR.server.backup
    B.stats.restored = B.stats.restored + 1
    NR.log.say(1, "store: " .. tostring(username) .. "'s record restored from the backup on the character: " .. why)
    return raw
end

-- With no player or no clock, the store is read alone.
function S.pick(username, ageH, player)
    local raw = F.load(username)
    local B = NR.server.backup
    if player == nil or B == nil or not NR.finite(ageH) then return raw end
    local bk, gen, why = B.read(player, username)
    if raw == nil then
        if bk == nil then return nil end
        return S.restore(username, bk, gen, "the store file is missing or unreadable")
    end
    local latest = K.resume.latest(raw)
    if latest ~= nil and latest > ageH then
        if bk ~= nil then
            return S.restore(username, bk, gen, "the store record is past the world clock (a hard-kill rollback)")
        end
        B.stats.aheadKept = B.stats.aheadKept + 1
        NR.log.say(1, "store: " .. tostring(username) .. "'s record is past the world clock (a hard-kill rollback) and "
            .. "the character holds no valid backup; the store's record is kept")
    end
    if bk == nil and why ~= "unavailable" then S.mark(username) end  -- a rejected backup: rewritten at the next store step
    return raw
end

-- A touch with a player object other than the sight's starts a new sight.
function S.get(username, worldAgeHours, player)
    local t = S.attach()
    local seen = sights(t)
    local r = t[username]
    if r == nil then
        r = S.pick(username, worldAgeHours, player)
        if r ~= nil then t[username] = r end
    end
    local mark = player
    if mark == nil then mark = true end
    if r == nil then
        -- A failed clock read never creates a record stamped 0
        if worldAgeHours == nil then return nil end
        r = S.new(username, worldAgeHours)
        t[username] = r
        seen[username] = mark
        S.filled[username] = r
        S.fresh[username] = true
        S.stats.created = S.stats.created + 1
        NR.log.say(3, "store: new record for " .. tostring(username))
        return r
    end
    local cur = seen[username]
    if cur == nil or (player ~= nil and cur ~= true and cur ~= player) then
        if S.filled[username] == r then
            S.resume(username, r, worldAgeHours)            -- held in memory since its fill: its derived fields stand
        else
            S.load(username, r, worldAgeHours)
        end
        if NR.finite(worldAgeHours) then seen[username] = mark end   -- no clock: not resumed, the sight left open
    elseif cur == true and player ~= nil then
        seen[username] = player                            -- the sight's first object: adopted, no new sight
    end
    return r
end

-- Marks the index dirty for the debounced task. A save that writes nothing keeps the dirty mark and stamps the attempt,
-- so the retry comes once per save gap; only a flush that writes marks the index.
local function flush(username)
    local r = S.records and S.records[username]
    F.dirty[username] = nil                                -- the flush is the dirty slot's save
    if r == nil then return end
    if F.save(username, r) then
        F.indexDirty = true                                -- the departure's stamp reaches the file at the next store.index task
        return
    end
    F.dirty[username] = true
    F.lastWrite[username] = nowMs() or F.lastWrite[username]
end

-- The flush as a one-shot task on the players' queue (it rides the budget), when the record is held.
local function queueFlush(username)
    local P = NR.server.players
    if P ~= nil and P.task ~= nil and S.records ~= nil and S.records[username] ~= nil then
        P.task("store.flush." .. K.store.hexName(username), function() flush(username) end)
    end
end

-- A dirty slot whose record is gone is dropped.
function S.retryAway(now)
    local P = NR.server.players
    if P == nil or P.online == nil then return end
    for username in pairs(F.dirty) do
        if S.records == nil or S.records[username] == nil then
            F.dirty[username] = nil                        -- a record no longer held ends the retries
        elseif P.online[username] == nil and K.store.due(F.lastWrite[username], now, S.SAVE_GAP_MS) then
            queueFlush(username)
        end
    end
end

-- The sight forgotten, so the next first sight loads the record again.
function S.forget(username)
    if username == nil then return end
    if S.loaded ~= nil then S.loaded[username] = nil end
    queueFlush(username)
end

-- S.reset REPLACES the table (the one place a held handle goes stale); the reset count carries over.
function S.reset(username, worldAgeHours, player)
    local t = S.attach()
    local old = t[username]
    if old == nil then old = F.load(username) end
    local r = S.new(username, worldAgeHours)
    S.fresh[username] = nil
    F.deferSince[username] = nil                           -- a reset record is meant to replace the file's
    if old ~= nil then
        r.resets = (old.resets or 0) + 1                   -- every OnNewGame over an existing record
    else
        r.resets = 0                                       -- a first character
    end
    t[username] = r
    S.filled[username] = r
    S.resumed[username] = nil
    sights(t)[username] = player or true                   -- the respawn's object (OnNewGame's) holds the new sight
    local IN = NR.server.intake
    if IN ~= nil and IN.forget ~= nil then IN.forget(username) end  -- nothing the dead character ate carries over
    -- a reset reaches the file at the next store step
    S.mark(username)
    NR.log.say(2, "store: reset record for " .. tostring(username) .. " (reset " .. tostring(r.resets) .. ")")
    return r
end

-- Written at the next store step past the save gap. A skipped name is never marked.
function S.mark(username)
    if username == nil then return end
    if S.skip ~= nil and S.skip(username) == true then return end
    F.dirty[username] = true
end

-- A real minute since the last write, or at once when dirty; the first after a boot at the player's phase.
function S.step(username, player, record, ctx)
    -- The skip seam: S.skip is nil in production; only the test harness sets it, to a
    -- function of a username answering true for its ghost names, whose store step then does nothing at all (no
    -- phase seed, no preload read, no deferral, no save, no index entry or dirty mark).
    if S.skip ~= nil and S.skip(username) == true then return end
    local now = nowMs()
    if now == nil or record == nil then return end
    if F.lastWrite[username] == nil then F.lastWrite[username] = K.store.firstLast(username, now, S.SAVE_GAP_MS) end
    local dirty = F.dirty[username] == true
    if not dirty and not K.store.due(F.lastWrite[username], now, S.SAVE_GAP_MS) then return end
    F.dirty[username] = nil
    local ageH = record.lastSeen
    if ctx ~= nil and ctx.eAge ~= nil then ageH = ctx.eAge end      -- the age the minute ran at: no clock read
    if not F.save(username, record, player, ageH) and dirty then F.dirty[username] = true end  -- retried at the next step
end

-- The hourly task: a locked index is read again (a file that reads now lifts the lock).
local function reread()
    if F.indexLocked then F.readIndex() end
end

-- The debounced index write: a clean index is left alone.
function S.indexNow()
    if F.indexDirty then F.writeIndex() end
end
local indexNow = S.indexNow

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
-- departure hook and the pipeline's "store" step.
if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        if S.wired then return end
        S.wired = true
        S.attach()
        F.readIndex()
        local P = NR.server.players
        if P ~= nil then P.onDeparture[#P.onDeparture + 1] = S.forget end
        NR.server.minute.register("store", S.step)
    end)
end

-- Each a one-shot task, so it runs in a queue slot under the budget, not in the minute event.
if Events ~= nil and Events.EveryOneMinute ~= nil then
    Events.EveryOneMinute.Add(function()
        if not NR.isServer() then return end
        local now = nowMs()
        if now == nil then return end
        if F.indexDirty and K.store.due(F.lastIndexWrite, now, S.INDEX_GAP_MS) then queue("store.index", indexNow) end
        S.retryAway(now)
        if not F.indexLocked or not K.store.due(F.lastReread, now, S.REREAD_GAP_MS) then return end
        F.lastReread = now
        queue("store.reread", reread)
    end)
end
