-- NR_Kernel_Mirror.lua -- the flat scalar table the server sends a client (spec § 4.8): every
-- value a string, number or boolean, copied from the record, never the record itself.
-- Plan 2 (Task 11): the stomach fill and the pool's named scalars, flattened as pool_<key>; a record
-- whose kinetics has not yet run reads full (the seed) and an all-zero pool.
local K = NutritionRevamp.kernel
K.mirror = {}

-- record: the stored inputs; meta: { mode, version, build }. Returns a new flat table.
function K.mirror.build(record, meta)
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
    local pool = record.pool
    local keys = K.vector.KEYS
    for i = 1, #keys do
        local k = keys[i]
        m["pool_" .. k] = 0
        if pool ~= nil then
            m["pool_" .. k] = pool[k] or 0
        end
    end
    K.mirror.body(m, record.body)
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
