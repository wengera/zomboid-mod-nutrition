-- NR_Kernel_Retention.lua -- the cook/storage state multipliers on the MOD nutrients per class. The vanilla macros pass
-- through unscaled: the engine's only macro modifier is Eat's burnt divisor (#0036), which the eat wrapper owns. Burnt
-- replaces cooked (vanilla clears cooked when burnt); frozen and rotten are independent (#0204). A canned seed already
-- carries the canned composition. K.vector is read at call time (macroSet is built lazily).
local K = NutritionRevamp.kernel
K.retention = {}

-- A key absent here is left unscaled, so a future nutrient is robust until its class is declared.
K.retention.CLASSES = {}
K.retention.CLASSES.vitC = "watersol"
K.retention.CLASSES.fibre = "stable"
K.retention.CLASSES.water = "stable"
K.retention.CLASSES.iron = "mineral"
K.retention.CLASSES.phytate = "heatlabile"
-- The B vitamins and choline lose to heat and cooking water (S0252); the class gives the direction only (open S0309).
K.retention.CLASSES.thiamine = "watersol"
K.retention.CLASSES.riboflavin = "watersol"
K.retention.CLASSES.niacin = "watersol"
K.retention.CLASSES.vitB6 = "watersol"
K.retention.CLASSES.folate = "watersol"
K.retention.CLASSES.vitB12 = "watersol"
K.retention.CLASSES.choline = "watersol"
-- Carotene is left unscaled: cooking RAISES its availability, which this loss-only table cannot express.
K.retention.CLASSES.carotene = "stable"
K.retention.CLASSES.zinc = "mineral"
K.retention.CLASSES.calcium = "mineral"
K.retention.CLASSES.magnesium = "mineral"
K.retention.CLASSES.sodium = "mineral"
K.retention.CLASSES.potassium = "mineral"
K.retention.CLASSES.caffeine = "stable"
K.retention.CLASSES.ethanol = "stable"
-- Unclassified, so unscaled: no settled retention row (open S0206).

-- Every value in (0, 1]. No factor is a settled science row: design-phase-v1 game choices on a USDA R6 basis.
K.retention.FACTORS = {}
-- watersol: cooked the USDA R6 water-soluble band, burnt the 0.6^2 judgement, frozen Rickman 2007.
K.retention.FACTORS.watersol = {cooked = 0.60, burnt = 0.36, rotten = 0.50, frozen = 0.95}
-- mineral: heat-stable with slight leaching.
K.retention.FACTORS.mineral = {cooked = 0.95, burnt = 0.90, rotten = 1.0, frozen = 1.0}
-- stable: fibre and the water term, heat-stable in every state.
K.retention.FACTORS.stable = {cooked = 1.0, burnt = 1.0, rotten = 1.0, frozen = 1.0}
-- heatlabile (phytate): cooking REDUCES phytate, which helps absorption.
K.retention.FACTORS.heatlabile = {cooked = 0.70, burnt = 0.49, rotten = 1.0, frozen = 1.0}

-- Lazy because K.vector loads after this file.
local IS_MACRO = nil

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

-- The clamp to <= 1 is a structural guard: every factor is already <= 1.
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

-- An out-of-schema key is dropped by the fixed-schema copy.
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
