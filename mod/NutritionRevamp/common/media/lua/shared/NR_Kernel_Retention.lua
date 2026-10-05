-- NR_Kernel_Retention.lua -- the state multipliers (spec § 4.2, data-pipeline report § B). The four
-- cook/storage states (cooked, burnt, rotten, frozen) scale the MOD nutrients per nutrient class; the
-- four vanilla macros pass through unscaled, because the engine applies no state modifier to the macros
-- except Eat's burnt divisor of 5 (#0036, #0019), which the eat wrapper owns, not this kernel. Burnt
-- replaces cooked on the cook axis (vanilla clears cooked when burnt); frozen and rotten are
-- independent multipliers (#0204). Canned is not a flag: a canned seed baseline already carries the
-- canned composition, so apply with no cook flag is identity. Every factor is a design-phase-v1
-- judgement or a USDA R6 basis, not a settled science row, so none carries a -- Sxxxx tag. Pure: tables
-- in, a fresh table out, no Java. This file sorts before NR_Kernel_Vector.lua, so it never touches
-- K.vector at module load -- every K.vector reference is at call time (macroSet is built lazily).
local K = NutritionRevamp.kernel
K.retention = {}

-- Each mod-nutrient key's retention class. The four macros are absent (apply skips them anyway); a key
-- absent here is left unscaled, so a future nutrient is robust until its class is declared.
K.retention.CLASSES = {}
K.retention.CLASSES.vitC = "watersol"
K.retention.CLASSES.fibre = "stable"
K.retention.CLASSES.water = "stable"
K.retention.CLASSES.iron = "mineral"
K.retention.CLASSES.phytate = "heatlabile"

-- FACTORS[class][state], every value in (0, 1]: the retained fraction of the class under the state.
K.retention.FACTORS = {}
-- watersol: cooked is the USDA R6 water-soluble loss band; burnt is the 0.6^2 judgement; rotten is the vitC/folate/thiamin decay judgement; frozen is the Rickman 2007 long-storage term.
K.retention.FACTORS.watersol = {cooked = 0.60, burnt = 0.36, rotten = 0.50, frozen = 0.95}
-- mineral: minerals are heat-stable with slight leaching; the burnt squaring is a judgement.
K.retention.FACTORS.mineral = {cooked = 0.95, burnt = 0.90, rotten = 1.0, frozen = 1.0}
-- stable: fibre and the water term are heat-stable across every state.
K.retention.FACTORS.stable = {cooked = 1.0, burnt = 1.0, rotten = 1.0, frozen = 1.0}
-- heatlabile (phytate): cooking and soaking REDUCE phytate, which is beneficial for absorption; judgement.
K.retention.FACTORS.heatlabile = {cooked = 0.70, burnt = 0.49, rotten = 1.0, frozen = 1.0}

-- The macro lookup set, built once from the vector's MACROS list and cached. Lazy because K.vector
-- loads after this file; apply calls it at eat time, when the vector table is present.
local IS_MACRO = nil

-- Return the cached macro set, building it on first use from K.vector.MACROS (a Lua table, so # is a
-- Lua length, never a Java list).
function K.retention.macroSet()
    if IS_MACRO == nil then
        IS_MACRO = {}
        local macros = K.vector.MACROS
        for i = 1, #macros do
            IS_MACRO[macros[i]] = true
        end
    end
    return IS_MACRO
end

-- The combined multiplier for one class under the state flags. The cook axis is burnt OR cooked (burnt
-- replaces cooked), then frozen and rotten multiply in independently; the product is clamped to <= 1 as
-- a structural guard (every factor is already <= 1, so retention never exceeds 100 %).
function K.retention.factor(class, flags)
    local f = K.retention.FACTORS[class]
    local combined = 1
    if flags.burnt then
        combined = combined * f.burnt
    end
    if flags.cooked and not flags.burnt then
        combined = combined * f.cooked
    end
    if flags.frozen then
        combined = combined * f.frozen
    end
    if flags.rotten then
        combined = combined * f.rotten
    end
    combined = K.min(combined, 1)
    return combined
end

-- Apply the state flags to a vector: a fresh vector with the input copied in, then every classified,
-- non-macro key scaled by its class factor. The macros and any unclassified key pass through unscaled;
-- an out-of-schema key is dropped by the fixed-schema copy (K.vector.add over the declared keys).
function K.retention.apply(vector, flags)
    local out = K.vector.new()
    K.vector.add(out, vector, 1)
    local macros = K.retention.macroSet()
    local keys = K.vector.keys()
    for i = 1, #keys do
        local key = keys[i]
        local class = K.retention.CLASSES[key]
        if not macros[key] and class ~= nil then
            out[key] = out[key] * K.retention.factor(class, flags)
        end
    end
    return out
end
