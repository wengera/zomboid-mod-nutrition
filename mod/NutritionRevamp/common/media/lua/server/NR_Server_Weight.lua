-- NR_Server_Weight.lua -- the body model's weight adapter: once per player per game
-- minute, late in the per-player minute (the pipeline's ORDER, NR_Server_Minute, runs the weight step
-- after the metabolism and strength steps and before the writer and the store, so it reads
-- the fm and lm Metabolism stamped this minute), it writes the model's total mass into the vanilla
-- weight slot, the three direction flags off the 7-day trend, writes the five weight-band traits from the
-- body's axes (WGT.writeTraits) when the day close changed the band or the held set differs, and, under
-- the NR.LegacyMirror sandbox option, overwrites the four vanilla macro stores other mods read.
--
-- The weight slot is re-asserted, not trusted (#2643): setWeight every minute even when unchanged, the
-- three flags every minute (#2644). The band traits are the axes': the day close
-- (NR_Server_Metabolism) sets body.fatT, body.thinT and body.band from K.traits.axes and stamps body.traitsDirty on a
-- band change; this file adds and removes the five traits K.traits.WANT names through the trait collection and
-- pushes the trait block once, sendSyncPlayerFields(player, 2) (it reaches that player's own connection only,
-- #2603). Vanilla's applyTraitFromWeight (its 65/75/85/100 kg bands) is never called. A band trait an admin or
-- another mod removes is re-added as a repair (#2740). The band traits are the registry objects off
-- CharacterTrait[name], never an id built from a name (#0550; the id of VERY_UNDERWEIGHT holds a space).
--
-- The legacy mirror: calories = the trailing-24 h energy balance; proteins = the piecewise
-- map of the trailing-24 h protein per kg; carbohydrates and lipids = the trailing-24 h grams less a
-- reference; each is read off the trailing-24 h window (K.body.trail24 over record.body.trail,
-- as K.energy.eb24h reads it), clamped to the stores (#0022). A plain overwrite every
-- minute. The window is NR_Server_Metabolism's (K.body.new lays it, Metabolism moves it and its heal keeps it
-- finite) before this file reads it. When all four setters answer, the four values written become the record's
-- reconciliation baseline (record.reconcile.baseline): NR_Server_Reconcile, earlier in the
-- same minute, compares the stores against the mod's own last write. A band change's trait write also marks the bus
-- (B.markBand), so the mirror's body_band goes out with the next effects flush.
--
-- Every Java read goes through NR.call (index-first); every Java global is named only inside a function
-- behind a nil check, so the file loads with no engine. The
-- whole minute runs under one pcall per player and never raises into the players walk. Slow-clock code:
-- no @fastpath region in this file.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.weight = {
    stats = { minutes = 0, weightWrites = 0, flagWrites = 0, bandChanges = 0, bandRepairs = 0, pushes = 0,
              pushMissing = 0, mirrorWrites = 0, failures = 0, badReads = 0, rebases = 0 },
    lastError = nil,
    wired = false,
    limitations = {
        "the mirror is a plain overwrite; its four written values are the reconciliation's baseline (NR_Server_Reconcile)",
        "the weight-direction thresholds are a game choice",
        "a stray band trait beside the wanted one is removed at the first minute of the next record day (a once-a-day audit; the minute's held check reads the wanted trait alone, Rule 6)",
    },
}
local WGT = NR.server.weight

local finite = NR.finite

-- K.traits.WANT per rung pair, built once: the rungs are healed whole numbers (fatT 0..2, thinT 0..3, K.heal.RUNGS),
-- so the minute allocates nothing. Read-only.
local wantCache = {}
local function wantOf(fatT, thinT)
    if type(fatT) ~= "number" or type(thinT) ~= "number" then return K.traits.WANT(fatT, thinT) end
    local key = fatT * 4 + thinT
    local want = wantCache[key]
    if want == nil then
        want = K.traits.WANT(fatT, thinT)
        wantCache[key] = want
    end
    return want
end

-- Whether the held set differs from want, read with the fewest gets (Rule 6): a wanted trait absent, or,
-- with none wanted, any of the five present. An unreadable get compares nothing.
local function differs(coll, want)
    local wanted = false
    local names = K.traits.WEIGHT_TRAITS
    for i = 1, #names do
        local name = names[i]
        if want[name] == true then
            wanted = true
            local t = CharacterTrait[name]
            if t ~= nil then
                local okG, present = NR.call(coll, "get", t)
                if okG and present ~= true then return true end
            end
        end
    end
    if wanted then return false end
    for i = 1, #names do
        local t = CharacterTrait[names[i]]
        if t ~= nil then
            local okG, present = NR.call(coll, "get", t)
            if okG and present == true then return true end
        end
    end
    return false
end

-- Whether the write in progress has landed an edit: kept outside write's return, so a raise after a landed edit
-- still pushes it.
local edit = { changed = false }

-- The write: each of the five added when wanted and absent, removed when held and unwanted. Returns whether the
-- collection changed and whether every read and edit landed.
local function write(coll, want)
    local changed, complete = false, true
    local names = K.traits.WEIGHT_TRAITS
    for i = 1, #names do
        local name = names[i]
        local t = CharacterTrait[name]
        if t ~= nil then
            local okG, present = NR.call(coll, "get", t)
            if not okG then
                complete = false
            elseif want[name] == true and present ~= true then
                if NR.call(coll, "add", t) then
                    changed = true
                    edit.changed = true
                else
                    complete = false
                end
            elseif want[name] ~= true and present == true then
                if NR.call(coll, "remove", t) then
                    changed = true
                    edit.changed = true
                else
                    complete = false
                end
            end
        end
    end
    return changed, complete
end

-- The five weight-band traits from the body's axes: when body.traitsDirty (the day close changed the
-- band), at the first minute of a record day (the audit: body.traitsDay, not stored, so a restart audits once) or when
-- the held set differs from K.traits.WANT(fatT, body.thinT), each is added or removed through the trait collection
-- and the trait block is pushed once if the collection changed (also when a later edit raised). A thinness rung
-- excludes the fat traits here too (precedence). A dirty write that landed clears body.traitsDirty and returns true
-- (the band changed: the caller marks the bus); an unreadable registry or collection, or an edit that failed, keeps
-- it for the next minute. ctx (optional) is the pipeline's, whose trait collection read (NR.read) it shares.
function WGT.writeTraits(player, body, ctx)
    if CharacterTrait == nil then return false end
    local coll = NR.read.traits(ctx, player)
    if coll == nil then return false end
    local fatT = body.fatT
    if type(body.thinT) == "number" and body.thinT > 0 then
        fatT = 0
    end
    local want = wantOf(fatT, body.thinT)
    local dirty = body.traitsDirty == true
    local audit = body.traitsDay ~= body.dayIndex
    if not dirty and not audit and not differs(coll, want) then return false end
    edit.changed = false
    local okW, changed, complete = pcall(write, coll, want)
    if not okW then
        if edit.changed then
            NR.pushTraits(player, WGT.stats)
        end
        error(changed, 0)
    end
    if complete then body.traitsDay = body.dayIndex end
    if changed then NR.pushTraits(player, WGT.stats) end
    if not dirty then
        if changed then WGT.stats.bandRepairs = WGT.stats.bandRepairs + 1 end
        return false
    end
    if not complete then return false end
    body.traitsDirty = nil
    WGT.stats.bandChanges = WGT.stats.bandChanges + 1
    return true
end

-- The legacy macro mirror: the four stores off the trailing-24 h window.
local function mirror(nut, body, w)
    local t = body.trail
    local p24h = K.body.trail24(t, "p") / w
    local carb24h = K.body.trail24(t, "carb")
    local lip24h = K.body.trail24(t, "lip")
    local cal = K.body.mapCalories(K.energy.eb24h(body))
    local prot = K.body.mapProteins(p24h)
    local carb = K.body.mapCarbs(carb24h)
    local lip = K.body.mapLipids(lip24h)
    local okC = NR.call(nut, "setCalories", cal)
    local okP = NR.call(nut, "setProteins", prot)
    local okH = NR.call(nut, "setCarbohydrates", carb)
    local okL = NR.call(nut, "setLipids", lip)
    WGT.stats.mirrorWrites = WGT.stats.mirrorWrites + 1
    if okC and okP and okH and okL then
        return { calories = cal, carbs = carb, lipids = lip, proteins = prot }
    end
    return nil
end

-- The reconciliation baseline after the legacy write: the four values written. A record
-- with no reconcile table yet is left for the reconciliation's own seed.
local function rebase(record, wrote)
    local rc = record.reconcile
    if wrote == nil or type(rc) ~= "table" then return end
    rc.baseline = K.reconcile.baselineAfter(wrote)
    WGT.stats.rebases = WGT.stats.rebases + 1
end

-- The band mark on the bus: the effects mark, one gap and one flush.
local function markBand(username)
    local B = NR.server.bus
    if B ~= nil and B.markBand ~= nil then B.markBand(username) end
end

local function step(username, player, record, ctx)
    local body = record.body
    if body == nil then return end
    local w = body.fm + body.lm + body.lx                -- the body mass: the weight slot
    if not finite(w) or w <= 0 then
        WGT.stats.failures = WGT.stats.failures + 1
        WGT.lastError = "weight: non-finite or non-positive mass for " .. tostring(username) .. "; nothing written"
        NR.log.say(2, WGT.lastError)
        return
    end
    local nut = NR.read.nutrition(ctx, player)
    if nut == nil then
        WGT.stats.badReads = WGT.stats.badReads + 1
        return
    end
    if NR.call(nut, "setWeight", w) then WGT.stats.weightWrites = WGT.stats.weightWrites + 1 end
    local inc, lot, dec = K.body.flags(K.body.trend(body.mass7, w))
    local okI = NR.call(nut, "setIncWeight", inc)
    local okL = NR.call(nut, "setIncWeightLot", lot)
    local okD = NR.call(nut, "setDecWeight", dec)
    if okI and okL and okD then WGT.stats.flagWrites = WGT.stats.flagWrites + 1 end
    if WGT.writeTraits(player, body, ctx) then markBand(username) end
    local opts = NR.server.options
    if opts == nil or opts.legacyMirror ~= false then
        rebase(record, mirror(nut, body, w))
    end
end

-- One player's minute: the pipeline's weight step (NR_Server_Minute.run, called from P.work).
-- One pcall around the body: a failure is kept and logged on the slow clock, never raised into the
-- players walk.
function WGT.minute(username, player, record, ctx)
    if record == nil then return end
    WGT.stats.minutes = WGT.stats.minutes + 1
    local ok, err = pcall(step, username, player, record, ctx)
    if not ok then
        WGT.stats.failures = WGT.stats.failures + 1
        WGT.lastError = err
        NR.log.say(2, "weight: " .. tostring(username) .. " failed: " .. tostring(err))
    end
end

-- Wiring: registered as the pipeline's weight step at OnServerStarted. ORDER runs it after the
-- metabolism and strength steps, so it reads this minute's masses.
if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        if WGT.wired then return end
        WGT.wired = true
        local MIN = NR.server.minute
        MIN.register("weight", WGT.minute)
    end)
end
