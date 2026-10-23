-- NR_Kernel_Mirror.lua -- the flat scalar table the server sends a client: every value a string, number or boolean,
-- copied from the record, never the record itself. Pitfall: an effects_* multiplier reads 0, not 1, until the record
-- has an effects table, so a reader that acts on one must treat 0 as absent.
local K = NutritionRevamp.kernel
K.mirror = {}

-- order: the nutrient keys carried as nut_<key>_g (nil carries none); P nil reads K.strength.DEFAULTS.
function K.mirror.build(record, meta, order, P)
    local m = {}
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
    K.mirror.body(m, record.body, P)
    K.mirror.effects(m, record.effects)
    K.mirror.drain(m, record.drain)
    return m
end

-- body_level is absent, never NaN, when the body or its lm, N0 or T is not finite (the view reads No data). The energy
-- state is not mirrored: no client surface reads it.

function K.mirror.body(m, body, P)
    m.body_fm = 0
    m.body_lm = 0
    m.body_weight = 0
    m.body_band = ""
    m.body_tac = 0
    m.body_rmod = 0
    m.body_delta = 0
    m.body_ebDay = 0
    m.body_eeDay = 0
    m.body_inDay = 0
    m.body_trend = 0
    if body == nil then
        return
    end
    m.body_fm = body.fm
    m.body_lm = body.lm
    m.body_weight = body.fm + body.lm + body.lx
    m.body_band = body.band
    m.body_tac = body.tac
    m.body_rmod = body.rmod
    m.body_delta = body.delta or 0
    m.body_ebDay = body.ebDay
    m.body_eeDay = body.eeDay
    m.body_inDay = body.inDay
    m.body_trend = K.mirror.trend(body, m.body_weight)
    if K.finite(body.S) then
        m.body_sets = body.S
    end
    if K.finite(body.lm) and K.finite(body.N0) and K.finite(body.T) then
        local level = K.strength.level(body.lm, body.N0, body.T, P or K.strength.DEFAULTS)
        if K.finite(level) then
            m.body_level = level
        end
    end
end

-- A fresh ring holds the creation mass, so a new body reads 0; 0 too when any read is not finite.
function K.mirror.trend(body, w)
    local ring = body.mass7
    if type(ring) ~= "table" or not K.finite(ring[1]) then
        return 0
    end
    local t = K.body.trend(ring, w)
    if not K.finite(t) then
        return 0
    end
    return t
end

-- 0 when the sub-table or a key is absent.
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

-- 0 (false for the two trait flags) when absent; a copy of what the effects adapter stamped.
local EFFECT_NUMBERS = { "epoch", "aimMul", "speedMul", "intoxTarget", "tempTarget", "healMul", "bleedMul", "infectMul",
    "coldMul", "stressTarget", "panicTarget", "unhappyTarget", "foodSickTarget", "fOff", "mAcc", "rRec" }

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

-- drain_state is the code with the smallest fraction among the active and recovering states; drain_rec's causes have
-- lapsed and their ceilings still apply.
function K.mirror.drain(m, D)
    m.drain_state = 0
    m.drain_target = K.drain.NONE
    m.drain_mask = 0
    m.drain_rec = 0
    if D == nil or D.active ~= true then
        return
    end
    m.drain_state = D.state
    m.drain_target = D.target
    if type(D.mask) == "number" then
        m.drain_mask = D.mask
    end
    if type(D.recovering) == "number" then
        m.drain_rec = D.recovering
    end
end

-- stomachMass is the Overfull moodle's input: the physical fill clamps at 1 at 730 g and cannot place a level above it.
function K.mirror.stomach(m, record)
    m.stomachFill = K.stomach.recordFill(record)
    m.stomachMass = K.mirror.stomachMass(record)
end

-- Read by K.mirror.stomach and the bus's push signature; 0 for no stomach, a malformed lane or a non-finite mass.
function K.mirror.stomachMass(record)
    local s = record.stomach
    if s == nil or s.buffer == nil or type(s.liquid) ~= "number" then
        return 0
    end
    local g = K.stomach.mass(s)
    if not K.finite(g) then
        return 0
    end
    return math.floor(g + 0.5)
end
