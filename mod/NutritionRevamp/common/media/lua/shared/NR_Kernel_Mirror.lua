-- NR_Kernel_Mirror.lua -- the flat scalar table the server sends a client (spec § 4.8): every
-- value a string, number or boolean, copied from the record, never the record itself.
-- Plan 2 (Task 11): the stomach fill. Plan 4 (Task 14, ruling 21): the pool_<key> keys are retired from the wire
-- (record.pool stays a diagnostic); the nutrient grades, the fluids and the acute scalars take their place.
-- A record whose kinetics has not yet run reads full (the seed) and zeros.
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
    m.stomachFill = record.stomachFill or 1
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
        if nutrients ~= nil and nutrients[key] ~= nil then
            m["nut_" .. key .. "_g"] = nutrients[key].g or 0
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
