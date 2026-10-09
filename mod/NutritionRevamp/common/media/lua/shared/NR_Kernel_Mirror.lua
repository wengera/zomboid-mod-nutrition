-- NR_Kernel_Mirror.lua -- the flat scalar table the server sends a client (spec § 4.8): every
-- value a string, number or boolean, copied from the record, never the record itself.
-- Plan 2 (Task 11): the stomach fill. Plan 4 (Task 14, ruling 21): the pool_<key> keys are retired from the wire
-- (record.pool stays a diagnostic); the nutrient grades, the fluids and the acute scalars take their place.
-- A record whose kinetics has not yet run reads its stomach's own fill, else empty (ruling C-2), and zeros.
-- Plan 5 (Task 11): the 20 effects_* keys (K.mirror.effects) — a multiplier reads 0, not 1, until the record has an
-- effects table, so a reader that acts on one must treat 0 as absent.
local K = NutritionRevamp.kernel
K.mirror = {}

-- record: the stored inputs; meta: { mode, version, build }; order: the nutrient keys to carry as nut_<key>_g
-- (the adapter passes NR.data.records.ORDER; nil carries none). Returns a new flat table.
function K.mirror.build(record, meta, order)
    local m = {}
    m.v = record.v
    m.username = record.username
    m.firstSeen = record.firstSeen
    m.lastSeen = record.lastSeen
    m.resets = record.resets
    m.dead = record.dead
    m.mode = meta.mode
    m.version = meta.version
    m.build = meta.build
    K.mirror.stomach(m, record)
    K.mirror.nutrients(m, record.nutrients, order)
    K.mirror.fluids(m, record.fluids)
    K.mirror.acute(m, record.acute)
    K.mirror.body(m, record.body)
    K.mirror.effects(m, record.effects)
    return m
end

-- Plan 3 (Task 16): the body's scalars as body_<name>; 0 (the band "") when the record has no body yet.
function K.mirror.body(m, body)
    m.body_fm = 0
    m.body_lm = 0
    m.body_weight = 0
    m.body_band = ""
    m.body_energyState = 0
    m.body_tac = 0
    m.body_dmod = 0
    m.body_rmod = 0
    m.body_shownL = 0
    m.body_delta = 0
    m.body_ebDay = 0
    m.body_eeDay = 0
    m.body_inDay = 0
    m.body_dStr = 0
    m.body_dHyp = 0
    if body == nil then
        return
    end
    m.body_fm = body.fm
    m.body_lm = body.lm
    m.body_weight = body.fm + body.lm
    m.body_band = body.band
    m.body_energyState = body.energyState
    m.body_tac = body.tac
    m.body_dmod = body.dmod
    m.body_rmod = body.rmod
    m.body_shownL = body.shownL
    m.body_delta = body.delta
    m.body_ebDay = body.ebDay
    m.body_eeDay = body.eeDay
    m.body_inDay = body.inDay
    local dStr, dHyp = K.training.doses(body)
    m.body_dStr = dStr
    m.body_dHyp = dHyp
end

-- Plan 4 (Task 14): nut_<key>_g for each key of order, and the epoch; 0 when the sub-table or a key is absent.
-- Plan 7 (Task 3, ruling 4): beside it nut_<key>_p (the pool fraction, 1 = replete) and nut_<key>_x (the excess
-- rung, 0-3) for the interface's Numbers level and its excess class; 0 when absent, like the grade.
function K.mirror.nutrients(m, nutrients, order)
    m.nutrients_epoch = 0
    if nutrients ~= nil then
        m.nutrients_epoch = nutrients.epoch or 0
    end
    if order == nil then
        return
    end
    for i = 1, #order do
        local key = order[i]
        m["nut_" .. key .. "_g"] = 0
        m["nut_" .. key .. "_p"] = 0
        m["nut_" .. key .. "_x"] = 0
        if nutrients ~= nil and nutrients[key] ~= nil then
            m["nut_" .. key .. "_g"] = nutrients[key].g or 0
            m["nut_" .. key .. "_p"] = nutrients[key].p or 0
            m["nut_" .. key .. "_x"] = nutrients[key].x or 0
        end
    end
end

-- Plan 4 (Task 14): the fluids scalars; 0 when the record has no fluids yet.
function K.mirror.fluids(m, fluids)
    m.fluids_dehydPct = 0
    m.fluids_naPlasma = 0
    m.fluids_thirstTarget = 0
    if fluids == nil then
        return
    end
    m.fluids_dehydPct = fluids.dehydPct or 0
    m.fluids_naPlasma = fluids.naPlasma or 0
    m.fluids_thirstTarget = fluids.thirstTarget or 0
end

-- Plan 4 (Task 14): the acute scalars; 0 when the record has no acute state yet.
function K.mirror.acute(m, acute)
    m.acute_caf = 0
    m.acute_bac = 0
    m.acute_g = 0
    m.acute_bg = 0
    m.acute_awakeH = 0
    m.acute_debtH = 0
    m.acute_iu = 0
    m.acute_refeedRisk = 0
    if acute == nil then
        return
    end
    m.acute_caf = acute.caf or 0
    m.acute_bac = acute.bac or 0
    m.acute_g = acute.g or 0
    m.acute_bg = acute.bg or 0
    m.acute_awakeH = acute.awakeH or 0
    m.acute_debtH = acute.debtH or 0
    m.acute_iu = acute.iu or 0
    m.acute_refeedRisk = acute.refeedRisk or 0
end

-- Plan 5 (Task 11): the effects set as effects_<name>; 0 (false for the two trait flags) when record.effects or a
-- field is absent. Numeric reads only, a copy of what the effects adapter stamped.
local EFFECT_NUMBERS = { "epoch", "aimMul", "speedMul", "intoxTarget", "tempTarget", "healMul", "bleedMul", "infectMul",
    "coldMul", "drain", "lethal", "stressTarget", "panicTarget", "unhappyTarget", "foodSickTarget", "fOff", "mAcc", "rRec" }

function K.mirror.effects(m, eff)
    for i = 1, #EFFECT_NUMBERS do
        local k = EFFECT_NUMBERS[i]
        local v = 0
        if eff ~= nil and type(eff[k]) == "number" then
            v = eff[k]
        end
        m["effects_" .. k] = v
    end
    m.effects_nv = false
    m.effects_ss = false
    if eff ~= nil and type(eff.own) == "table" then
        m.effects_nv = eff.own.nv == true
        m.effects_ss = eff.own.ss == true
    end
end

-- Plan 11c Task 7 (ruling 11c-25): the stomach pair. stomachFill, the physical fill (K.stomach.recordFill, ruling C-2; the writer's fallback, the writer's F being W.satietyF),
-- and stomachMass, the stomach's whole mass in grams, both lanes (K.stomach.mass), rounded to 1 g, the Overfull
-- moodle's input (K.view.fullnessLevel; F clamps at 1 at 730 g and cannot place a level above it). 0 when the record
-- has no stomach or no solid buffer, and when the mass is not finite.
function K.mirror.stomach(m, record)
    m.stomachFill = K.stomach.recordFill(record)
    m.stomachMass = K.mirror.stomachMass(record)
end

-- The rounded whole mass in grams (K.mirror.stomach's field and the bus's push signature read it): 0 for no stomach,
-- no solid buffer or a non-finite mass.
function K.mirror.stomachMass(record)
    local s = record.stomach
    if s == nil or s.buffer == nil then
        return 0
    end
    local g = K.stomach.mass(s)
    if g ~= g or g == math.huge or g == -math.huge then
        return 0
    end
    return math.floor(g + 0.5)
end
