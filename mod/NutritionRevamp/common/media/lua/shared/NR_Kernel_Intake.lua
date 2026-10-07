-- NR_Kernel_Intake.lua -- the eat's arithmetic (Plan 10 Task R3, moved out of NR_Server_Intake.lua): the share
-- and fraction of an eat, what Eat delivered to the four vanilla macros, the vector's source, the source chain
-- for one type and the assembly of the eaten vector. Pure: numbers and Lua tables in, numbers and Lua tables out,
-- no Java and no global data -- the lookup, the inference templates and the dish or craft input lookup are
-- arguments (the adapter passes NR.data.nutrients.get, NR.data.infer and its chained-lookup closure). The
-- adapter keeps every public name as a thin wrapper (IN.fractionOf = K.intake.fractionOf, ...). Slow-path code
-- (once per eat): no fast region. This file sorts before NR_Kernel_Retention.lua and NR_Kernel_Vector.lua, so
-- every K.vector / K.retention / K.clamp reference is at call time.
local K = NutritionRevamp.kernel
K.intake = {}

-- The share of the WHOLE item eaten: the drop in raw hunger over the instance base hunger, clamped to
-- 0..1 (#0002, #0001). Raw hunger is negative (an apple is -0.16); the sign cancels in the ratio. A base
-- hunger of 0 answers 0. With instBase replaced by rawBefore it is the share of what was LEFT, which is
-- Eat's own rescaled fraction (Eat rescales the requested fraction by baseHunger/hungChange, #0006).
function K.intake.shareEaten(rawBefore, rawAfter, instBase)
    if instBase == 0 then
        return 0
    end
    return K.clamp((rawBefore - rawAfter) / instBase, 0, 1)
end

-- The two fractions (see assemble): frac = Eat's own fraction of what was LEFT, share = the share of
-- the WHOLE instance. From the raw hunger when the instance base hunger is non-zero. A thirst-only
-- Food (base hunger 0) still goes through Eat (#0083), which then skips the baseHunger rescale and
-- applies the menu fraction directly (#0014); the leftover multiplyFoodValues(1 - f) scales its stored
-- thirstChange too (#0057), so the drop in RAW thirst (getThirstChangeUnmodified, #0005) over the raw
-- thirst before IS that fraction -- of what was LEFT (frac). It is the share of the whole only for a
-- never-eaten item: after a partial eat the stored thirst has shrunk, so the whole-instance share
-- takes the drop over the TYPE's unscaled thirst instead (scriptThirst, readBefore), the same shape as
-- hunger's instBase. A thirst-only Food has no base-thirst field; scriptThirst is the denominator.
-- Raw thirst is negative like hunger; the sign cancels. Nothing readable -> 0, 0 (nothing landed).
-- limitations:
--  * A split or butchered thirst-only item (its instance thirst scaled off the script value) mis-shares
--    by that scale -- vanishingly rare for a thirst-only Food.
--  * scriptThirst 0 or unreadable: the whole is unknown and share falls back to frac, which over-counts
--    the whole-instance vector on any eat after the first partial one.
function K.intake.fractionOf(rawBefore, rawAfter, instBase, thirstBefore, thirstAfter, scriptThirst)
    if instBase == nil or instBase == 0 then
        if type(thirstBefore) == "number" and type(thirstAfter) == "number" and thirstBefore ~= 0 then
            local drop = thirstBefore - thirstAfter
            local f = K.clamp(drop / thirstBefore, 0, 1)
            if type(scriptThirst) == "number" and scriptThirst ~= 0 then
                return f, K.clamp(drop / scriptThirst, 0, 1)
            end
            return f, f
        end
        return 0, 0
    end
    return K.intake.shareEaten(rawBefore, rawAfter, rawBefore), K.intake.shareEaten(rawBefore, rawAfter, instBase)
end

-- What Eat delivered to the four vanilla macros: each live macro times the fraction Eat applied,
-- divided by 5 when the item is burnt (#0019, #0036 -- the one vanilla nutrition modifier).
function K.intake.macrosEaten(cal, carb, lip, pro, share, burnt)
    local d = 1
    if burnt then
        d = 5
    end
    return { calories = cal * share / d, carbs = carb * share / d, lipids = lip * share / d, proteins = pro * share / d }
end

-- The vector's source: a dish's ingredient list is authoritative, so it wins over a craft map; then the
-- eaten item's own chain step (chainOne): `declared` and `inferred` name themselves, a table hit and
-- a miss are both `baseline` (a miss names the type in `missing`, as before Plan 6).
function K.intake.sourceOf(hasExtra, hasCraftMap, step)
    if hasExtra then
        return "dish"
    end
    if hasCraftMap then
        return "craft"
    end
    if step == "declared" or step == "inferred" then
        return step
    end
    return "baseline"
end

-- One type through the chain declared -> table -> inferred -> missing (rulings 13-14). info is
-- { declared = <NR_Nutrients string or nil>, macros = { calories, carbs, lipids, proteins }, foodType }
-- or nil; lookup(fullType) -> table seed or nil; templates is NR.data.infer or nil. Returns vec, step,
-- note: step is "declared", "table", "inferred" or "missing" (vec nil); note is the declared string's
-- unknown-key list, or its malformed reason (a string) when the chain fell through it, else nil. A
-- declared vector's four macros are info.macros, the item's own: the script block owns them.
-- Plan 7 (Task 3, ruling 8): the chain itself is K.vector.resolve (shared with the food tooltip); this
-- hands it the lookup and the templates in NR.data's shape.
function K.intake.chainOne(fullType, lookup, templates, info)
    local i = info or {}
    return K.vector.resolve(i.declared, i.macros, i.foodType, fullType, { nutrients = { get = lookup }, infer = templates })
end

-- A fresh per-eat trace of the chain: the types that took a declared or an inferred vector, and the
-- malformed declared strings ("<fullType>: <reason>") and unknown declared keys ("<fullType>: <key>").
function K.intake.newTrace()
    return { declared = {}, inferred = {}, malformed = {}, unknown = {} }
end

-- Record one chain step in the trace (Lua tables, so `#` is a Lua length).
function K.intake.traceStep(trace, fullType, step, note)
    if step == "declared" then
        trace.declared[#trace.declared + 1] = fullType
    end
    if step == "inferred" then
        trace.inferred[#trace.inferred + 1] = fullType
    end
    if type(note) == "string" then
        trace.malformed[#trace.malformed + 1] = tostring(fullType) .. ": " .. note
    elseif type(note) == "table" then
        for i = 1, #note do
            trace.unknown[#trace.unknown + 1] = tostring(fullType) .. ": " .. tostring(note[i])
        end
    end
end

-- Assemble the eaten vector from the before-snapshot b and the raw hunger after the original ran.
-- Returns vec, source, missing, share, frac, trace (nil vec when nothing was eaten). Two fractions:
--  share = the drop over instBase, the share of the WHOLE instance -- the factor on a whole-instance
--          vector (the baseline at the instance scale, the craft map);
--  frac  = the drop over rawBefore, the share of what was LEFT, which is Eat's own fraction -- the
--          factor on anything read off the live item, whose values a prior partial eat already shrank
--          (multiplyFoodValues): the four macros and the dish scaled to the live macro total.
-- For an item never eaten before rawBefore == instBase and the two agree. A thirst-only Food takes
-- frac from its raw thirst and share from that drop over the type's script thirst (fractionOf);
-- thirstAfter is the raw thirst after the original ran.
-- lookup(fullType) -> seed vector or nil (the server passes NR.data.nutrients.get); templates is
-- NR.data.infer (nil: no inference); inputs(fullType) -> vector or nil is a dish or craft input's lookup
-- (the adapter's chained lookup, which writes its steps into trace); trace is the per-eat trace (newTrace).
-- The eaten item's own chain reads b.declared, b.foodType and its live macros (b.macros, else
-- b.cal/carb/lip/pro). A declared or table vector is a whole-type vector: the instance scale and share,
-- as the baseline always took. An inferred vector is read off the live macros, which a prior partial eat
-- already shrank and which carry the instance scale already: it takes frac and no instance scale.
function K.intake.assemble(b, rawAfter, lookup, thirstAfter, templates, inputs, trace)
    local frac, share = K.intake.fractionOf(b.rawBefore, rawAfter, b.instBase, b.thirstBefore, thirstAfter, b.scriptThirst)
    if not K.vector.finite(share) or share <= 0 or not K.vector.finite(frac) or frac <= 0 then
        return nil, nil, {}, share, frac, trace
    end
    local extra = b.extraTypes or {}
    local source = K.intake.sourceOf(#extra > 0, b.craftMap ~= nil)
    local vec, missing, factor
    if source == "dish" then
        local note
        vec, note = K.vector.dish(inputs, extra, b.cal + b.carb + b.lip + b.pro)
        missing = note.missing
        factor = frac
    elseif source == "craft" then
        vec, missing = K.vector.craft(inputs, b.craftMap, 1)
        factor = share
    else
        local macros = b.macros or { calories = b.cal, carbs = b.carb, lipids = b.lip, proteins = b.pro }
        local own = { declared = b.declared, foodType = b.foodType, macros = macros }
        local step, note
        vec, step, note = K.intake.chainOne(b.fullType, lookup, templates, own)
        K.intake.traceStep(trace, b.fullType, step, note)
        source = K.intake.sourceOf(false, false, step)
        missing = {}
        if step == "inferred" then
            factor = frac
        else
            if vec == nil then
                vec = K.vector.new()
                missing[1] = b.fullType
            end
            -- the instance scale instBase/scriptHunger: 1 for an unscaled item, the butcher ratio x
            -- jitter for a butchered meat (#2669-#2672), 1/amount for a split output (#2660); meat guards 0
            vec = K.vector.meat(vec, b.instBase, b.scriptHunger)
            factor = share
        end
    end
    vec = K.vector.add(K.vector.new(), vec, factor)
    -- the macros track vanilla exactly: what Eat delivered, not what the seed says
    local m = K.intake.macrosEaten(b.cal, b.carb, b.lip, b.pro, frac, b.burnt)
    vec.calories, vec.carbs, vec.lipids, vec.proteins = m.calories, m.carbs, m.lipids, m.proteins
    -- retention skips the macros by design
    vec = K.retention.apply(vec, { cooked = b.cooked, burnt = b.burnt, rotten = b.rotten, frozen = b.frozen })
    return vec, source, missing or {}, share, frac, trace
end
