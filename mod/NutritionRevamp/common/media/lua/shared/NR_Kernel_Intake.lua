-- NR_Kernel_Intake.lua -- the eat's arithmetic: the share and fraction of an eat, what Eat delivered to the vanilla
-- macros, the vector's source chain and the eaten vector. No global data: the lookup, the inference templates and the
-- input lookup are arguments. K.vector / K.retention / K.clamp are read at call time (this file sorts before them).
local K = NutritionRevamp.kernel
K.intake = {}

-- Raw hunger is negative (#0002); the sign cancels in the ratio. With instBase replaced by rawBefore it is the share of
-- what was LEFT, Eat's own rescaled fraction (#0006).
function K.intake.shareEaten(rawBefore, rawAfter, instBase)
    if instBase == 0 then
        return 0
    end
    return K.clamp((rawBefore - rawAfter) / instBase, 0, 1)
end

-- frac = Eat's fraction of what was LEFT, share = the share of the WHOLE instance. A thirst-only Food goes through Eat
-- (#0083) unrescaled, and its leftover thirst is scaled too (#0057), so raw thirst's drop gives frac; after a partial
-- eat the whole-instance share takes the drop over the TYPE's script thirst instead.
-- Pitfalls: a split thirst-only item mis-shares by its split scale; a scriptThirst of 0 falls back to frac, which
-- over-counts on any eat after the first partial one.
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

-- Divided by 5 when burnt (#0019), the one vanilla nutrition modifier.
function K.intake.macrosEaten(cal, carb, lip, pro, share, burnt)
    local d = 1
    if burnt then
        d = 5
    end
    return { calories = cal * share / d, carbs = carb * share / d, lipids = lip * share / d, proteins = pro * share / d }
end

-- A dish's ingredient list is authoritative, so it wins over a craft map; a table hit and a miss are both `baseline`.
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

-- Returns vec, step ("declared", "table", "inferred" or "missing"), note (the declared string's unknown keys or its
-- malformed reason). A declared vector's macros are the item's own: the script block owns them.
function K.intake.chainOne(fullType, lookup, templates, info)
    local i = info or {}
    return K.vector.resolve(i.declared, i.macros, i.foodType, fullType, { nutrients = { get = lookup }, infer = templates })
end

function K.intake.newTrace()
    return { declared = {}, inferred = {}, malformed = {}, unknown = {} }
end

-- Lua tables, so `#` is a Lua length.
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

-- Returns vec, source, missing, share, frac, trace (nil vec when nothing was eaten). share (over instBase) scales a
-- whole-instance vector; frac (over rawBefore, Eat's own) scales anything read off the live item, which a prior
-- partial eat already shrank. A table or craft vector is scaled to the calories Eat delivered; an inferred vector,
-- read off the live macros, takes frac and no instance scale.
function K.intake.assemble(b, rawAfter, lookup, thirstAfter, templates, inputs, trace)
    local frac, share = K.intake.fractionOf(b.rawBefore, rawAfter, b.instBase, b.thirstBefore, thirstAfter, b.scriptThirst)
    if not K.finite(share) or share <= 0 or not K.finite(frac) or frac <= 0 then
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
        local scale
        scale, factor = K.vector.instanceScale(vec.calories, b.cal, frac, nil, 0, share)
        vec = K.vector.scaled(vec, scale)
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
            -- The micronutrients follow the macros Eat delivered. A declared vector's calories are the item's LIVE
            -- ones, so they anchor nothing: anchored on them, a second bite would land the whole vector again.
            local kcal = vec.calories
            if step == "declared" then
                kcal = nil
            end
            local scale
            scale, factor = K.vector.instanceScale(kcal, b.cal, frac, b.instBase, b.scriptHunger, share)
            vec = K.vector.scaled(vec, scale)
        end
    end
    vec = K.vector.add(K.vector.new(), vec, factor)
    -- what Eat delivered, not what the seed says
    local m = K.intake.macrosEaten(b.cal, b.carb, b.lip, b.pro, frac, b.burnt)
    vec.calories, vec.carbs, vec.lipids, vec.proteins = m.calories, m.carbs, m.lipids, m.proteins
    -- retention skips the macros by design
    vec = K.retention.apply(vec, { cooked = b.cooked, burnt = b.burnt, rotten = b.rotten, frozen = b.frozen })
    return vec, source, missing or {}, share, frac, trace
end
