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
    return m
end
