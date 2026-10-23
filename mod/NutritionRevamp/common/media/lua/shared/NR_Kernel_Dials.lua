-- NR_Kernel_Dials.lua -- the sandbox re-resolve of the dials (K.dials.row and get live in NR_Kernel.lua). The adapter
-- passes the sandbox table in, so the kernel never names SandboxVars. A field is written only when the read differs
-- from the last value seen, so a patch on a sandbox-backed field (a fit tool) survives the per-minute poll.
local K = NutritionRevamp.kernel

-- Sorted so the writes run in one order.
function K.dials.optIds(rows)
    local ids = {}
    for id, row in pairs(rows) do
        K.dials.addOpt(ids, id, row)
    end
    table.sort(ids)
    return ids
end

-- (the pairs body, kept out of the loop for the line-granular coverage gate)
function K.dials.addOpt(ids, id, row)
    if row.opt ~= nil and row.param ~= true then
        ids[#ids + 1] = id
    end
end

K.dials.OPT_IDS = K.dials.optIds(NutritionRevamp.data.dials)

-- seen is the caller's table of the last value seen by id, kept across polls. Returns the fields written.
function K.dials.apply(sv, seen)
    local ids = K.dials.OPT_IDS
    local n = 0
    for i = 1, #ids do
        n = n + K.dials.applyOne(sv, seen, ids[i])
    end
    return n
end

-- K.readLeaf's one clamp rule; on a change, written and the domain's derive() run. Returns 1 when written.
function K.dials.applyOne(sv, seen, id)
    local row = K.dials.row(id)
    local v = K.readLeaf(sv, row.opt, row.value, row.min, row.max, row.int ~= true)
    local last = seen[id]
    if last == nil then
        last = row.value
    end
    if v == last then
        return 0
    end
    seen[id] = v
    K.dials.bind(id, v)
    K.dials.derive(id)
    return 1
end

function K.dials.bind(id, v)
    local t = K
    local key = id
    local dot = string.find(key, ".", 1, true)
    while dot ~= nil do
        t = t[string.sub(key, 1, dot - 1)]
        key = string.sub(key, dot + 1)
        dot = string.find(key, ".", 1, true)
    end
    t[key] = v
end

function K.dials.derive(id)
    local dot = string.find(id, ".", 1, true)
    local domain = K[string.sub(id, 1, dot - 1)]
    if type(domain) == "table" and type(domain.derive) == "function" then
        domain.derive()
    end
end

-- A param row reads its option into its domain's own parameter table, never into the field (K.strength.params).
-- The option file writes a double's default to three places (tools/sandbox_options.py), hence WRITTEN_TOL.
K.dials.WRITTEN_PLACES = 1000 -- no row needed: the option file's three decimal places
K.dials.WRITTEN_TOL = 0.0005 -- no row needed: half the third decimal place

function K.dials.written(v)
    return math.floor(v * K.dials.WRITTEN_PLACES + 0.5) / K.dials.WRITTEN_PLACES
end

function K.dials.paramOptions(domain)
    local rows = NutritionRevamp.data.dials
    local ids = {}
    for id, row in pairs(rows) do
        K.dials.addParam(ids, id, row, domain .. ".")
    end
    table.sort(ids)
    local out = {}
    for i = 1, #ids do
        out[i] = K.dials.paramEntry(ids[i], rows[ids[i]])
    end
    return out
end

-- (the pairs body, kept out of the loop for the coverage gate)
function K.dials.addParam(ids, id, row, prefix)
    if row.param == true and string.sub(id, 1, string.len(prefix)) == prefix then
        ids[#ids + 1] = id
    end
end

function K.dials.paramEntry(id, row)
    local key = string.match(id, "([^%.]+)$")
    return { id = id, key = key, opt = row.opt, value = row.value, min = row.min, max = row.max, int = row.int, written = K.dials.written(row.value) }
end

-- A read within WRITTEN_TOL of the written default reads the default (StrengthMaintainShare's 0.333). The live field is
-- the default, never bound, because a bound field would move every derivation that reads DEFAULTS under any option.
function K.dials.readParam(sv, entry, default)
    local v = K.readLeaf(sv, entry.opt, default, entry.min, entry.max, entry.int ~= true)
    local written = K.dials.written(default)
    if written ~= default and math.abs(v - written) <= K.dials.WRITTEN_TOL then
        return default
    end
    return v
end
