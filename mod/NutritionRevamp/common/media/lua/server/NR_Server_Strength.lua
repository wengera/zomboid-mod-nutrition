-- NR_Server_Strength.lua: the Strength adapter. Once per player per game minute, after metabolism, nutrients and
-- effects, it writes the native Strength level when one is due (Metabolism's day close stamps body.levelDue) and
-- re-asserts the carry delta. A native level that left the written one (an admin's set, a grant that crossed a total)
-- is written back the same minute or, through the AddXP listener, at once.
-- The carry delta, the written level's band factor (#2144) times (1 + eAcute), is written with setMaxWeightDelta when
-- it differs from the live delta, so any other writer is re-asserted against (#2143); the carry base is never written
-- (#2704). STR.remap re-asserts the muscle band after the creation handler's write (#2867).
-- The minute runs under one pcall per player; Java globals are named only inside functions. Slow-clock code.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.strength = {
    stats = { minutes = 0, pushes = 0, pushMissing = 0, carryWrites = 0, failures = 0,
              badReads = 0, ladderFallbacks = 0, levelWrites = 0, levelSteps = 0, stepFailures = 0,
              xpPins = 0, xpGrants = 0, pinFailures = 0, masteryWrites = 0, guarded = 0,
              sleepDeferrals = 0 },
    lastError = nil,
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

-- The fallback when the perk's own getter is absent.
STR.FALLBACK_TOTALS = { 1500, 4500, 10500, 19500, 37500, 67500, 127500, 217500, 337500, 487500 } -- VANILLA #2102
-- The carry delta re-assertion tolerance.
STR.CARRY_EPS = 0.001

local finite = NR.finite

-- An unread age skips the step, never stamped 0.

local num = NR.num

-- true only when the member is present and answers true.
local flag = NR.flag

local obj = NR.obj

-- Read once per server; a nil or non-finite answer anywhere reads the #2102 ladder instead, logged once.
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

-- One sendSyncPlayerFields(player, 2) (#2099) when the set changed. Returns whether it changed.
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

-- The nutrients step runs before this one, so these are the CURRENT minute's stamps; an absent or non-finite field
-- reads neutral. w is the body mass, kg.
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

-- Written when it differs from the live delta by more than CARRY_EPS (#2143).
local function carry(player, record, body, level)
    local hourOfDay = K.circadian.hour(record, NR.sleepOn())   -- the body clock's hour; nil (no halving) with sleep off
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
    carry(player, record, body, body.wroteL)                     -- the written level's band
end

-- One pcall around the body: a failure is kept and logged, never raised into the players walk.
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

-- ------------------------------------------------------------ the AddXP capture
-- AddXP(chr, perk, amount) (#2125) fires last in XP.AddXP, after the level loops, every multiplier and the level-10
-- clamp, so amount is the landed XP and getPerkLevel already reads the grant's level. The landed amount carries the
-- protein factor (#2112), the book multiplier (#2113) and the sandbox multiplier, which every vanilla Strength route
-- applies (GameServer.addXp passes AddXP's second boolean true); K.strength.capture divides all three out. The XP never
-- moves the mod's level: a grant that left the native level off body.wroteL, or landed on a level-10 Strength, re-pins
-- at once (STR.repin). Event-driven (Rule 6): any other perk returns before a Java read.

-- nil when unknown (the kernel reads a bad one as 1).
local function sandboxMult()
    local sv = SandboxVars
    if type(sv) ~= "table" then return nil end
    local cfg = sv.MultiplierConfig
    if type(cfg) ~= "table" then return nil end
    if cfg.GlobalToggle ~= false then return cfg.Global end
    return cfg.Strength
end

local function username(player)
    local ok, name = NR.call(player, "getUsername")
    if ok and type(name) == "string" then return name end
    return nil
end

-- Never creates a record.
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

-- NR_Server_Fitness's record; one Lua table lookup.
local function inSet(name)
    local fit = NR.server.fitness
    return fit ~= nil and fit.typeOf ~= nil and fit.typeOf(name) ~= nil
end

-- ------------------------------------------------------------ the level write
-- K.strength.heldLevel against body.wroteL, written in three parts: the native level stepped (STR.stepLevel), the XP
-- pinned (STR.pin), and with BeyondTen its stored mastery XP, never native XP while native is 10. A write due while the
-- character sleeps waits until it wakes (the engine drops a sleeper's grant). Once per day close per player (Rule 6),
-- and when the native level left the written one.

-- The global BeyondTen at API_VERSION 1, else nil.
function STR.beyondTen()
    local bt = BeyondTen
    if type(bt) == "table" and bt.API_VERSION == 1 then return bt end
    return nil
end

-- The level route: one LevelPerk or LoseLevel per level between from and to, vanilla's creation route, so its
-- listener (XpUpdate.lua:389) swaps the band traits at each step on the server; neither pushes from a server (L4854).
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

-- setXPToLevel writes base's starting total (L14519,
-- the only absolute per-perk setter); then one addXp grant of the fraction's XP divided by the engine's chain
-- (K.strength.rawXp). A pin that raises the XP grants even with no fraction: GameServer.addXp re-seeds the anti-cheat's
-- XP snapshot (#2132), setXPToLevel never does. Made under STR.pinning, so the capture ignores it.
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

-- BeyondTen.SetStoredXP clamps to its level-15 cost; 0 below 10 (the write on leaving native 10); then its own client
-- sync, BeyondTenServer.SendPerkSync, when present.
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

-- STR.pinning is held for the write's length and cleared whatever it raised; the raise goes to the caller's pcall.
function STR.write(player, body, perk, native, ctx)
    STR.pinning = true
    local ok, err = pcall(writeBody, player, body, perk, native, ctx)
    STR.pinning = false
    if not ok then error(err, 0) end
end

-- Nothing when the perk or the level is unreadable.
function STR.writeLevel(player, body, ctx)
    local perk = Perks ~= nil and Perks.Strength or nil
    if perk == nil then return end
    local native = num(player, "getPerkLevel", nil, perk)
    if native == nil then return end
    STR.write(player, body, perk, native, ctx)
end

function STR.repin(player, body, native)
    STR.write(player, body, Perks.Strength, native)
end

-- ------------------------------------------------------------ the level-10 guard
-- Vanilla's rust pass (xpUpdate.checkForLosingLevel, XpUpdate.lua:283) drops a level whose XP sits below its starting
-- total, which a parked level 10 always does. The guard (sentinel NR_StrengthGuardInstalled) holds a Strength the mod
-- wrote at 10; every other call goes to the saved original, BeyondTen's wrapper when that was first.
NR_StrengthGuardInstalled = NR_StrengthGuardInstalled or {}

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
        STR.repin(player, body, level)
    end
end

-- One pcall: a failure is counted and kept, never raised into the engine's event dispatch.
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

-- The listener and the guard are installed once, on the server only (installWrap never wraps twice).
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
