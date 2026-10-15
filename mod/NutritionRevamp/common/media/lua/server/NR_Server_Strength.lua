-- NR_Server_Strength.lua -- the body model's Strength adapter (spec § 4.3): once per player per
-- game minute, after the metabolism step (the pipeline's ORDER, NR_Server_Minute, runs the strength
-- step after metabolism, nutrients and effects), it writes the native Strength level when one is due and re-asserts
-- the carry delta. The lean-mass body moves at the day close (NR_Server_Metabolism), which stamps body.levelDue; the
-- minute then writes the shown level (STR.writeLevel, spec section 7): the native level stepped to it, the XP pinned
-- to the level's starting total plus the bar's fraction, parked at the level-9 total at 10, or BeyondTen's stored
-- mastery XP above 10. A native level that left the written one (an admin's set, a grant that crossed a total) is
-- written back the same minute or, through the AddXP listener, at once.
--
-- The carry delta is the trait factor of the written level's muscle band (K.strength.traitCarry of body.wroteL,
-- #2144; ruling 13-7) times (1 + eAcute), written with setMaxWeightDelta when it differs from the live delta, so any
-- other writer is re-asserted against (#2143, #2565). This file never writes the carry base (#2704).
--
-- STR.ladder is the XP ladder the pin reads; STR.remap (vanilla's band remap, the measured route of #2867-#2874)
-- re-asserts the muscle band after the creation handler's write (NR_Server_Creation, Task 17b); ruling 13-8's fallback
-- route was not taken (Task 0 check 6). STR.onXp, the AddXP
-- listener, captures each Strength grant as training signal into body.sigDay (spec section 4).
--
-- Every Java read goes through NR.call (index-first) with a default; every Java global is named only
-- inside a function behind a nil check, so the file loads with no engine
-- (testing/tests/kernel/test_strength_shape.py). The whole minute runs under one pcall per player and
-- never raises into the players walk. Slow-clock code: no @fastpath region in this file.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.strength = {
    stats = { minutes = 0, pushes = 0, pushMissing = 0, carryWrites = 0, failures = 0,
              badReads = 0, ladderFallbacks = 0, levelWrites = 0, levelSteps = 0, stepFailures = 0,
              xpPins = 0, xpGrants = 0, pinFailures = 0, masteryWrites = 0, guarded = 0,
              sleepDeferrals = 0 },
    lastError = nil,
    -- The AddXP capture's counters, beside the minute's (the golden trace walks stats).
    xpStats = { captures = 0, ignored = 0, failures = 0 },
    xpError = nil,
    -- True while the mod's own level write runs, so its XP grants are not captured as training.
    pinning = false,
    wired = false,
    totals = nil,
    limitations = {
        "the carry delta's acute inputs (dehydration, sweat, hours awake, caffeine, clinical vitamin D) read the current minute's fluids, acute and nutrients sub-tables",
        "an unreadable native level writes no level that minute; the carry then reads the last written level's band, and nothing before the first write",
        "the engine's XP grant does not reach a sleeping character, and the bar's fraction lands through it, so a level write due while the character sleeps waits until it wakes",
        "the training signal is the Strength XP the engine's XP event reports; a grant the engine makes without the event (to a sleeping character, or to one whose Strength XP sits at the level-10 total) trains nothing; a Strength grant made without vanilla's multipliers (the admin /addxp without -true, a mod's addXpNoMultiplier) is divided by a sandbox multiplier it never received; a grant that ends a skill book's range counts at the book's factor, because the engine drops the book before the event (AddXP @876-@962 L14323-L14328)",
    },
}
local STR = NR.server.strength

-- The #2102 ladder (cumulative XP for levels 1-10), the fallback when the perk's own getter is absent.
STR.FALLBACK_TOTALS = { 1500, 4500, 10500, 19500, 37500, 67500, 127500, 217500, 337500, 487500 } -- #2102
-- The carry delta re-assertion tolerance.
STR.CARRY_EPS = 0.001

local finite = NR.finite

-- The world age and the minute's other engine reads are NR.read's (an unread age skips the step, never stamped 0).

-- A number read off obj:name(...), or dflt when the member is absent or the answer is not finite.
local num = NR.num

-- A boolean read off obj:name(...): true only when the member is present and answers true.
local flag = NR.flag

-- An object read off obj:name(...), or nil.
local obj = NR.obj

-- The cumulative XP ladder, totals[0] = 0 and totals[L] = Perks.Strength:getTotalXpForLevel(L) for
-- L = 1..10, read once per server; a nil or non-finite answer anywhere reads the #2102 ladder instead,
-- logged once.
function STR.ladder()
    if STR.totals ~= nil then return STR.totals end
    local perk = Perks ~= nil and Perks.Strength or nil
    local totals = { [0] = 0 }
    local whole = true
    for L = 1, K.strength.L_MAX do
        local v = num(perk, "getTotalXpForLevel", nil, L)
        if v == nil then whole = false end
        totals[L] = v
    end
    if not whole then
        totals = { [0] = 0 }
        for L = 1, K.strength.L_MAX do
            totals[L] = STR.FALLBACK_TOTALS[L]
        end
        STR.stats.ladderFallbacks = STR.stats.ladderFallbacks + 1
        NR.log.say(2, "strength: getTotalXpForLevel unreadable; the #2102 ladder is used")
    end
    STR.totals = totals
    return totals
end

-- Vanilla's band remap for a written level: every band trait but the level's own is removed if present,
-- the level's own added if absent; one sendSyncPlayerFields(player, 2) (#2099) when the set changed.
-- Returns whether it changed. ctx (optional) is the pipeline's, whose trait collection read (NR.read) it shares.
function STR.remap(player, level, ctx)
    if CharacterTrait == nil then return false end
    local coll = NR.read.traits(ctx, player)
    if coll == nil then return false end
    local want = K.strength.bandOf(level)
    local changed = false
    local names = K.strength.MUSCLE_TRAITS                -- the band traits vanilla's remap removes first (#2157)
    for i = 1, #names do
        local name = names[i]
        local t = CharacterTrait[name]
        if t ~= nil then
            local present = flag(coll, "get", t)
            if name == want then
                if not present and NR.call(coll, "add", t) then
                    changed = true                       -- a failing add repairs nothing
                end
            elseif present and NR.call(coll, "remove", t) then
                changed = true
            end
        end
    end
    if changed then NR.pushTraits(player, STR.stats) end
    return changed
end

-- The carry delta's acute inputs off the record's Plan 4 sub-tables. The pipeline's ORDER runs the
-- nutrients step before this one, so these are the CURRENT minute's stamps. An
-- absent sub-table (one the nutrients step has not laid) or an absent or non-finite field reads the neutral the
-- Plan 3 stub passed. Read: fluids.dehydPct, fluids.sweatActive (true), acute.awakeH, acute.caf (through
-- K.acute.caffeineActive) and nutrients.vitDClinical (true). w is the body mass, kg.
local function acuteInputs(record, w)
    local nut, fl, ac = record.nutrients, record.fluids, record.acute
    local dehydPct, sweatActive = 0, false
    if type(fl) == "table" then
        if finite(fl.dehydPct) then dehydPct = K.max(0, fl.dehydPct) end
        sweatActive = fl.sweatActive == true
    end
    local awakeH, caffeineActive = 0, false
    if type(ac) == "table" then
        if finite(ac.awakeH) then awakeH = K.max(0, ac.awakeH) end
        if finite(ac.caf) and w > 0 then caffeineActive = K.acute.caffeineActive(ac, w) end
    end
    local vitDClinical = type(nut) == "table" and nut.vitDClinical == true
    return dehydPct, sweatActive, awakeH, caffeineActive, vitDClinical
end

-- The carry delta: the trait factor of level's band (K.strength.traitCarry) x (1 + eAcute), the dehydration, sweat,
-- hours-awake, caffeine and vitamin D inputs read off the record (acuteInputs) at the body mass fm + lm + lx; written
-- when it differs from the live delta by more than CARRY_EPS, so any other writer is re-asserted against (#2143,
-- #2565).
local function carry(player, record, body, ageH, ctx, level)
    local hourOfDay = NR.read.hour(ctx, ageH)
    local w = body.fm + body.lm + body.lx
    local bf = 0
    if w > 0 then bf = body.fm / w end
    local dehydPct, sweatActive, awakeH, caffeineActive, vitDClinical = acuteInputs(record, w)
    local eAcute = K.strength.eAcute(dehydPct, sweatActive, awakeH, hourOfDay, caffeineActive, vitDClinical, bf)
    local delta = K.strength.carryDelta(K.strength.traitCarry(level), eAcute)
    if not finite(delta) then return end
    local live = num(player, "getMaxWeightDelta", nil)
    if live == nil or math.abs(delta - live) > STR.CARRY_EPS then
        local ok = NR.call(player, "setMaxWeightDelta", delta)
        if ok then STR.stats.carryWrites = STR.stats.carryWrites + 1 end
    end
    body.delta = delta
end

local function step(username, player, record, ctx)
    local body = record.body
    if body == nil then return end
    local ageH = NR.read.ageH(ctx)
    if ageH == nil then
        STR.stats.badReads = STR.stats.badReads + 1
        return
    end
    local perk = Perks ~= nil and Perks.Strength or nil
    local level = nil
    if perk ~= nil then level = num(player, "getPerkLevel", nil, perk) end
    if level == nil then
        STR.stats.badReads = STR.stats.badReads + 1
    elseif body.levelDue or level ~= body.wroteL then
        STR.write(player, body, perk, level, ctx)
    end
    if body.wroteL == nil then return end
    carry(player, record, body, ageH, ctx, body.wroteL)          -- the written level's band (ruling 13-7)
end

-- One player's minute: the pipeline's strength step (NR_Server_Minute.run, called from P.work).
-- One pcall around the body: a failure is kept and logged on the slow clock, never raised into the
-- players walk.
function STR.minute(username, player, record, ctx)
    if record == nil then return end
    STR.stats.minutes = STR.stats.minutes + 1
    local ok, err = pcall(step, username, player, record, ctx)
    if not ok then
        STR.stats.failures = STR.stats.failures + 1
        STR.lastError = err
        NR.log.say(2, "strength: " .. tostring(username) .. " failed: " .. tostring(err))
    end
end

-- ------------------------------------------------------------ the AddXP capture (spec section 4, ruling 13-11)
-- AddXP(chr, perk, amount) (#2125) fires last in IsoGameCharacter$XP.AddXP, after the level loops (LevelPerk
-- @997-@1002 L14334, LoseLevel @1151-@1157 L14350) and after every multiplier and the level-10 clamp
-- (@1346-@1364 L14375-L14376), so amount is the landed XP and getPerkLevel already reads the grant's level.
-- GameServer.addXp re-seeds NetworkCharacterAI.updateXpChecker after AddXP returns (@55-@59 L1920).
-- The landed amount carries the protein factor (AddXP @107-@190, #2112), the book multiplier (@738-@756, #2113) and
-- the sandbox multiplier (@757-@823 L14305-L14308: MultiplierConfig.Global when GlobalToggle, else the per-perk
-- MultiplierConfig.Strength; SandboxOptions$MultiplierConfig.<init> @19 L356, @37 L357, @69 L359), the last two behind
-- AddXP's second boolean (@225 L14258), which the server's Lua addXp route passes true, as does every vanilla Java
-- Strength route (Fitness.incStats @194-@201 L351, IsoGameCharacter.hitConsequences @116-@131 L6320,
-- IsoPlayer.hitConsequences @200-@214 L4466, all through GameServer.addXp(p, perk, f) @0-@5 L1903). K.strength.capture
-- divides all three out and weights a grant outside a recorded Fitness set by P.incidental; the signal lands in
-- body.sigDay (ruling 13-12). The XP never moves the mod's level: a grant that left the native level off body.wroteL,
-- or one that landed on a level-10 Strength, re-pins at once (STR.repin, ruling 13-29): back to the written level, the
-- park restored, BeyondTen's stored XP re-set from the body.
-- Cadence (Rule 6): event-driven, no clock work. Any other perk returns before a Java read; a Strength grant reads
-- the username, the protein store, the book multiplier and the level (six calls); the sandbox and the set are Lua.

-- The sandbox multiplier the engine applied to a Strength grant, or nil (the kernel reads a bad one as 1).
local function sandboxMult()
    local sv = SandboxVars
    if type(sv) ~= "table" then return nil end
    local cfg = sv.MultiplierConfig
    if type(cfg) ~= "table" then return nil end
    if cfg.GlobalToggle ~= false then return cfg.Global end
    return cfg.Strength
end

-- The username of a player, or nil.
local function username(player)
    local ok, name = NR.call(player, "getUsername")
    if ok and type(name) == "string" then return name end
    return nil
end

-- The body of an existing record, or nil; never creates a record.
local function bodyOf(name)
    local S = NR.server.store
    if S == nil or name == nil then return nil end
    local records = S.records
    if records == nil and S.attach ~= nil then records = S.attach() end
    if records == nil then return nil end
    local record = records[name]
    if record == nil then return nil end
    return record.body
end

-- Whether username's recorded Fitness set is running (NR_Server_Fitness's record; one Lua table lookup).
local function inSet(name)
    local fit = NR.server.fitness
    return fit ~= nil and fit.typeOf ~= nil and fit.typeOf(name) ~= nil
end

-- ------------------------------------------------------------ the level write (spec section 7, Plan 13 Task 14)
-- The shown level L = K.strength.level(lm, N0, T, P) (ruling 13-45), read by K.strength.heldLevel against the level
-- last written (body.wroteL: a rise at the whole number, a drop only DROP_MARGIN below it; Plan 13 Task 10c) into the
-- native perk level n and the bar's fraction, is written in three parts: the native level stepped to n
-- (STR.stepLevel, the one function a fallback route swaps, ruling 13-8); the XP (STR.pin: n's starting total plus the
-- fraction for n <= 9, ruling 13-9; parked at the level-9 total at 10, spec section 7); and with BeyondTen loaded, its
-- stored mastery XP (ruling 13-42), never native XP while the native level is 10. Then body.wroteL = n and
-- body.levelDue = false.
-- A write due while the character sleeps waits, levelDue kept, until it wakes (the engine drops a sleeper's grant).
-- Cadence (Rule 6): once per day close per player (Metabolism stamps levelDue), and when the native level left the
-- written one; a minute with no write due reads the level only, as before.

-- BeyondTen's API at the version this file was written against (ruling 13-24: the global BeyondTen, API_VERSION 1),
-- else nil.
function STR.beyondTen()
    local bt = BeyondTen
    if type(bt) == "table" and bt.API_VERSION == 1 then return bt end
    return nil
end

-- The level route, ruling 13-8's primary branch: one LevelPerk or LoseLevel per level between from and to, vanilla's
-- creation route, so its LevelPerk listener (XpUpdate.lua:389, :200-217) swaps the band traits at each step on the
-- server; neither method pushes anything from a server (IsoGameCharacter.LevelPerk @183-@194 L4854-L4855, LoseLevel
-- @51-@75 L4823-L4824). Returns the level reached (a missing member stops the walk there).
function STR.stepLevel(player, perk, from, to)
    local level = from
    for _ = from + 1, to do
        if not NR.call(player, "LevelPerk", perk) then return level end
        level = level + 1
    end
    for _ = to + 1, from do
        if not NR.call(player, "LoseLevel", perk) then return level end
        level = level - 1
    end
    return level
end

-- The XP pin (ruling 13-9): getXp():setXPToLevel(perk, base), base = n or 9 at the park, writes base's starting total
-- (IsoGameCharacter$XP.setXPToLevel @54-@67 L14519, the only absolute per-perk setter); then one addXp grant of the
-- fraction's XP divided by the chain the engine multiplies it by (K.strength.rawXp), so it lands as the fraction. A pin
-- that raises the XP grants even with no fraction (an amount of 0): GameServer.addXp re-seeds the anti-cheat's XP
-- snapshot after every call (@55-@59 L1920, #2132, #2862), setXPToLevel never does; a pure lowering calls
-- setXPToLevel only. The grant is made under STR.pinning, so the capture ignores it. Returns whether it landed.
function STR.pin(player, perk, n, frac)
    local totals = STR.ladder()
    local xpObj = obj(player, "getXp")
    local base = K.min(n, K.strength.L_MAX - 1)
    local target = K.strength.pinXp(n, frac, totals)
    local before = num(xpObj, "getXP", nil, perk)
    if not NR.call(xpObj, "setXPToLevel", perk, base) then return false end
    local add = target - totals[base]
    if add > 0 or before == nil or before < target then
        local grant = addXp
        if grant == nil then return false end
        local amount = 0
        if add > 0 then
            local store = num(obj(player, "getNutrition"), "getProteins", 0)
            local book = num(xpObj, "getMultiplier", 1, perk)
            amount = K.strength.rawXp(add, store, sandboxMult(), book)
        end
        grant(player, perk, amount)
        STR.stats.xpGrants = STR.stats.xpGrants + 1
    end
    STR.stats.xpPins = STR.stats.xpPins + 1
    return true
end

-- BeyondTen's stored Strength XP for shown level L (ruling 13-42): K.strength.masteryXp over its own cumulative cost
-- (BeyondTen.GetTotalMasteryCost(perk, level), Shared.lua:222), set through BeyondTen.SetStoredXP(player, perk,
-- value) (Shared.lua:272), which clamps to its level-15 cost; 0 below 10 (the write on leaving native 10); then
-- BeyondTenServer.SendPerkSync(player, perk, old, new), its own client sync, when present.
local function mastery(bt, player, perk, L)
    local v = 0
    if L >= K.strength.L_MAX then
        v = K.strength.masteryXp(L, function(level) return bt.GetTotalMasteryCost(perk, level) end)
    end
    local _, old, new = bt.SetStoredXP(player, perk, v)
    STR.stats.masteryWrites = STR.stats.masteryWrites + 1
    local srv = BeyondTenServer                         -- its client mirror (Server.lua:277 Server.SendPerkSync)
    if type(srv) == "table" and type(srv.SendPerkSync) == "function" then
        pcall(srv.SendPerkSync, player, perk, old, new)
    end
end

local function writeBody(player, body, perk, native, ctx)
    if NR.read.asleep(ctx, player) then
        STR.stats.sleepDeferrals = STR.stats.sleepDeferrals + 1
        return                                          -- AddXP drops a sleeper's grant (L14222-L14223): levelDue stays
    end
    local L = K.strength.level(body.lm, body.N0, body.T, NR.strengthP())
    if not finite(L) then
        STR.stats.badReads = STR.stats.badReads + 1
        return
    end
    local n, frac = K.strength.heldLevel(L, body.wroteL)
    local reached = STR.stepLevel(player, perk, native, n)
    STR.stats.levelSteps = STR.stats.levelSteps + math.abs(reached - native)
    if reached ~= native and K.strength.bandOf(reached) ~= K.strength.bandOf(native) then
        NR.pushTraits(player, STR.stats)                -- vanilla's listener swapped the band on the server only
    end
    if reached ~= n then
        STR.stats.stepFailures = STR.stats.stepFailures + 1
        return                                          -- levelDue stays: the next minute retries
    end
    local bt = STR.beyondTen()
    if n >= K.strength.L_MAX and bt ~= nil then
        mastery(bt, player, perk, L)                    -- never native XP at native 10 under BeyondTen
    else
        if bt ~= nil and (native >= K.strength.L_MAX or body.wroteL == K.strength.L_MAX) then
            mastery(bt, player, perk, L)                -- leaving 10: BeyondTen's stored XP to 0
        end
        if not STR.pin(player, perk, n, frac) then STR.stats.pinFailures = STR.stats.pinFailures + 1 end
    end
    body.wroteL = n
    body.levelDue = false
    STR.stats.levelWrites = STR.stats.levelWrites + 1
end

-- One level write for a body whose native level reads native (the minute's or the listener's read, so the write
-- reads it no second time); ctx (optional) is the pipeline's, whose asleep read the write shares. STR.pinning is held
-- for its length and cleared whatever it raised, and the raise goes on to the caller's pcall.
function STR.write(player, body, perk, native, ctx)
    STR.pinning = true
    local ok, err = pcall(writeBody, player, body, perk, native, ctx)
    STR.pinning = false
    if not ok then error(err, 0) end
end

-- STR.writeLevel(player, body, ctx): the write with its own level read; ctx (optional) is the pipeline's, whose asleep
-- read the write shares; nothing when the perk or the level is unreadable.
function STR.writeLevel(player, body, ctx)
    local perk = Perks ~= nil and Perks.Strength or nil
    if perk == nil then return end
    local native = num(player, "getPerkLevel", nil, perk)
    if native == nil then return end
    STR.write(player, body, perk, native, ctx)
end

-- The AddXP listener's re-pin (ruling 13-29): the write at the level the grant left, reading no clock.
function STR.repin(player, body, native)
    STR.write(player, body, Perks.Strength, native)
end

-- ------------------------------------------------------------ the level-10 guard (ruling 13-10)
-- Vanilla's rust pass calls xpUpdate.checkForLosingLevel(playerObj, perk) (XpUpdate.lua:283, :308, :321), which drops a
-- level whose XP sits below its starting total; a parked level 10 always does. The guard wraps it once (the sentinel
-- NR_StrengthGuardInstalled, the global a live check reads) and returns for a Strength whose native level is 10 and
-- whose record wrote 10; every other call goes to the saved original, BeyondTen's wrapper when that one was in place
-- first (Server.lua:441-468).
NR_StrengthGuardInstalled = NR_StrengthGuardInstalled or {}

-- Whether the guard holds playerObj's perk: Strength, native 10, and the record's written level 10.
function STR.parked(playerObj, perk)
    if Perks == nil or perk ~= Perks.Strength then return false end
    if num(playerObj, "getPerkLevel", nil, perk) ~= K.strength.L_MAX then return false end
    local body = bodyOf(username(playerObj))
    return body ~= nil and body.wroteL == K.strength.L_MAX
end

local function makeGuard(S)
    return function(playerObj, perk, ...)
        local nr = NutritionRevamp
        local str = nil
        if nr ~= nil and nr.server ~= nil then str = nr.server.strength end
        if str ~= nil then
            local ok, held = pcall(str.parked, playerObj, perk)
            if ok and held then
                str.stats.guarded = str.stats.guarded + 1
                return
            end
        end
        return S.orig(playerObj, perk, ...)
    end
end

-- Installs the guard when xpUpdate's function exists; returns whether it is in place.
function STR.installLevelGuard()
    local xu = xpUpdate
    if type(xu) ~= "table" then return false end
    NR.installWrap(NR_StrengthGuardInstalled, xu, "checkForLosingLevel", makeGuard, nil,
        "strength: xpUpdate.checkForLosingLevel")
    return NR_StrengthGuardInstalled.wrapper ~= nil and NR_StrengthGuardInstalled.class == xu
end

local function xpStep(player, perk, amount)
    local name = username(player)
    local body = bodyOf(name)
    if body == nil then
        STR.xpStats.ignored = STR.xpStats.ignored + 1
        return
    end
    if finite(amount) and amount > 0 then
        local store = num(obj(player, "getNutrition"), "getProteins", 0)
        local book = num(obj(player, "getXp"), "getMultiplier", 1, perk)
        local sig = K.strength.capture(amount, store, sandboxMult(), book, inSet(name), NR.strengthP())
        body.sigDay = body.sigDay + sig
        STR.xpStats.captures = STR.xpStats.captures + 1
    else
        STR.xpStats.ignored = STR.xpStats.ignored + 1     -- rust or nothing landed: no signal
    end
    local level = num(player, "getPerkLevel", nil, perk)
    if level ~= nil and (level ~= body.wroteL or level >= K.strength.L_MAX) then
        STR.repin(player, body, level)                    -- ruling 13-29
    end
end

-- The AddXP listener: Strength only, and nothing while the mod writes the level itself (STR.pinning). One pcall; a
-- failure is counted and kept, never raised into the engine's event dispatch.
function STR.onXp(player, perk, amount)
    if STR.pinning then return end
    if Perks == nil or perk ~= Perks.Strength then return end
    local ok, err = pcall(xpStep, player, perk, amount)
    if not ok then
        STR.xpStats.failures = STR.xpStats.failures + 1
        STR.xpError = err
        NR.log.say(2, "strength: XP capture failed: " .. tostring(err))
    end
end

-- Wiring: registered as the pipeline's strength step at OnServerStarted (ORDER runs it after the metabolism step, so
-- the body exists and its day has closed before this step reads it), and STR.onXp as the AddXP listener, once, on the
-- server only; the level-10 guard is installed there too (installWrap keeps a second start from wrapping twice).
if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        STR.installLevelGuard()
        if STR.wired then return end
        STR.wired = true
        local MIN = NR.server.minute
        MIN.register("strength", STR.minute)
        if Events.AddXP ~= nil then Events.AddXP.Add(STR.onXp) end
    end)
end
