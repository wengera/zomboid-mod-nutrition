-- NR_Kernel_Dials.lua -- the sandbox re-resolve of the tuning dials (Plan 19, spec Part A; ruling T1-1). K.dials.row and
-- K.dials.get live in NR_Kernel.lua, which loads before every kernel file; its K.dials.OPT_IDS is built at load from
-- NR.data.dials, which sorts before it (NR_Data_ < NR_Kernel_), and its functions run only when an options poll calls
-- them. A dial whose row names an option (opt) is read from the
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

-- id onto ids when its row names an option K.dials.apply writes: not a param row, whose option its domain reads into a
-- table of its own (the pairs body, kept out of the loop for the line-granular coverage gate).
function K.dials.addOpt(ids, id, row)
    if row.opt ~= nil and row.param ~= true then
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

-- The param options: a row with param reads its option into its domain's own parameter table, never into the field
-- (K.strength.params: one P table a server, threaded through the kernel). A domain builds its entries once at load.
-- The option file writes a double's default to three decimal places (tools/sandbox_options.py); WRITTEN_TOL is half the
-- third place, so a read that equals the written default reads the row's exact value.
K.dials.WRITTEN_PLACES = 1000 -- no row needed: the option file's three decimal places
K.dials.WRITTEN_TOL = 0.0005 -- no row needed: half the third decimal place

-- The option file's form of a number v: rounded half up to three decimal places (tools/sandbox_options.py written).
function K.dials.written(v)
    return math.floor(v * K.dials.WRITTEN_PLACES + 0.5) / K.dials.WRITTEN_PLACES
end

-- The entries of domain's param rows, sorted by id: { id, key (the last segment of the id), opt, value, min, max, int,
-- written (the value as the option file declares it) }.
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

-- id onto ids when its row is a param row under prefix (the pairs body, kept out of the loop for the coverage gate).
function K.dials.addParam(ids, id, row, prefix)
    if row.param == true and string.sub(id, 1, string.len(prefix)) == prefix then
        ids[#ids + 1] = id
    end
end

-- One param entry of row id.
function K.dials.paramEntry(id, row)
    local key = string.match(id, "([^%.]+)$")
    return { id = id, key = key, opt = row.opt, value = row.value, min = row.min, max = row.max, int = row.int, written = K.dials.written(row.value) }
end

-- A param option's read from sv (SandboxVars.NR, or nil) by the one clamp rule (K.readLeaf: a double clamps into the
-- entry's range, an int entry's out-of-range value reads the default); a read within WRITTEN_TOL of a written default
-- that is not the exact value (StrengthMaintainShare's 0.333 for m's third) reads the exact value.
function K.dials.readParam(sv, entry)
    local v = K.readLeaf(sv, entry.opt, entry.value, entry.min, entry.max, entry.int ~= true)
    if entry.written ~= entry.value and math.abs(v - entry.written) <= K.dials.WRITTEN_TOL then
        return entry.value
    end
    return v
end
