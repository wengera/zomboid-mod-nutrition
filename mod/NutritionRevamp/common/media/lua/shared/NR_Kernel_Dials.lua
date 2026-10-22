-- NR_Kernel_Dials.lua -- the sandbox re-resolve of the tuning dials (Plan 19, spec Part A; ruling T1-1). K.dials.row and
-- K.dials.get live in NR_Kernel.lua, which loads before every kernel file; this file runs only when an options poll
-- calls it, so its place in the load order does not matter. A dial whose row names an option (opt) is read from the
-- sandbox table the adapter passes in (the server's options poll, NR_Server_Options; the client's start,
-- NR_Client_Options), so the kernel never names SandboxVars, and its value is written into the dial's kernel field
-- only when the read differs from the last value seen: a read equal to it, the row's default included, writes nothing,
-- so a patch on a sandbox-backed field (replay_live.set_constants, a fit tool) survives the per-minute poll. A domain
-- with derived constants defines K.<domain>.derive(), called after a write so they follow.
local K = NutritionRevamp.kernel

-- The ids of rows (an id-keyed table of dial rows) that name an option, sorted so the writes run in one order.
function K.dials.optIds(rows)
    local ids = {}
    for id, row in pairs(rows) do
        K.dials.addOpt(ids, id, row)
    end
    table.sort(ids)
    return ids
end

-- id onto ids when its row names an option (the pairs body, kept out of the loop for the line-granular coverage gate).
function K.dials.addOpt(ids, id, row)
    if row.opt ~= nil then
        ids[#ids + 1] = id
    end
end

K.dials.OPT_IDS = K.dials.optIds(NutritionRevamp.data.dials)

-- The re-resolve: each sandbox-backed dial read from sv (SandboxVars.NR, or nil) and written when it changed against
-- seen (the caller's table of the last value seen by id, kept across polls). Returns the number of fields written.
function K.dials.apply(sv, seen)
    local ids = K.dials.OPT_IDS
    local n = 0
    for i = 1, #ids do
        n = n + K.dials.applyOne(sv, seen, ids[i])
    end
    return n
end

-- One dial's re-resolve: the option read by the one clamp rule (K.readLeaf: a double option clamps into the row's
-- range, an int row's out-of-range value reads the default), compared with the last value seen (the row's value
-- before any), and on a change written into the field and the domain's derive() run. Returns 1 when written, else 0.
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

-- Write v into the kernel field dial id names, walking its dotted path from K (monotony.SLOPE is K.monotony.SLOPE).
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

-- Run the derive() of dial id's domain (the first segment of its id), when the domain defines one.
function K.dials.derive(id)
    local dot = string.find(id, ".", 1, true)
    local domain = K[string.sub(id, 1, dot - 1)]
    if type(domain) == "table" and type(domain.derive) == "function" then
        domain.derive()
    end
end
