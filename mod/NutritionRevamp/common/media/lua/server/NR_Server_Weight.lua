-- NR_Server_Weight.lua: the weight adapter. Once per player per game minute, after metabolism and strength and before
-- the writer and the store, it writes the model's total mass into the vanilla weight slot and the three trend flags,
-- the five weight-band traits from the body's axes, and, under NR.LegacyMirror, the four vanilla macro stores.
-- The weight slot is re-asserted every minute, not trusted (#2643), and the flags too (#2644).
-- Vanilla's applyTraitFromWeight (its 65/75/85/100 kg bands) is never called. A band trait an admin or
-- another mod removes is re-added as a repair (#2740). Traits are the registry objects off CharacterTrait[name], never
-- an id built from a name (#0550: VERY_UNDERWEIGHT's id holds a space). sendSyncPlayerFields(player, 2) reaches that
-- player's own connection only (#2603).
-- The legacy mirror is a plain overwrite every minute off the trailing-24 h window, clamped to the stores (#0022);
-- the values written become the reconciliation baseline. The minute runs under one pcall per player.
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

-- Built once, so the minute allocates nothing. Read-only.
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

-- With the fewest gets (Rule 6); an unreadable get compares nothing.
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

-- Kept outside write's return, so a raise after a landed edit still pushes it.
local edit = { changed = false }

-- Returns whether the collection changed and whether every read and edit landed.
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

-- Written when body.traitsDirty, at a record day's first minute (body.traitsDay is not stored, so a restart audits once)
-- or when the held set differs; one push when the collection changed. A thinness rung excludes the fat traits here too.
-- A failed write keeps traitsDirty for the next minute.
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

-- A record with no reconcile table yet is left for the reconciliation's own seed.
local function rebase(record, wrote)
    local rc = record.reconcile
    if wrote == nil or type(rc) ~= "table" then return end
    rc.baseline = K.reconcile.baselineAfter(wrote)
    WGT.stats.rebases = WGT.stats.rebases + 1
end

-- One gap and one flush.
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

-- One pcall around the body: a failure is kept and logged, never raised into the players walk.
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

if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        if WGT.wired then return end
        WGT.wired = true
        local MIN = NR.server.minute
        MIN.register("weight", WGT.minute)
    end)
end
