-- NR_Kernel_Sched.lua -- the slow minute's budgeted queue (rules #3497 and #3444):
-- which names run their minute and how many a tick. Pure: lists and numbers in, lists and numbers out.
local K = NutritionRevamp.kernel
K.sched = {}

K.sched.FLOOR_MS = K.dials.get("sched.FLOOR_MS")
K.sched.HEADROOM = K.dials.get("sched.HEADROOM")
K.sched.SEED_MS = K.dials.get("sched.SEED_MS")
K.sched.MIN_MEAN_MS = K.dials.get("sched.MIN_MEAN_MS")
K.sched.EMA_W = K.dials.get("sched.EMA_W")
K.sched.TPM_DEFAULT = K.dials.get("sched.TPM_DEFAULT")
K.sched.MIN_TICKS = K.dials.get("sched.MIN_TICKS")

-- The pending queue from position head, kept in order for every name still in the roster and never doubled, then
-- every roster name not already queued, in roster order. Returns a new list.
function K.sched.merge(pending, head, roster)
    local out = {}
    local queued = {}
    local live = {}
    for i = 1, #roster do
        live[roster[i]] = true
    end
    for i = head, #pending do
        local u = pending[i]
        if live[u] == true and queued[u] == nil then
            out[#out + 1] = u
            queued[u] = true
        end
    end
    for i = 1, #roster do
        local u = roster[i]
        if queued[u] == nil then
            out[#out + 1] = u
            queued[u] = true
        end
    end
    return out
end

-- The ticks a minute the budget divides by: the smaller of the last two minutes' counts of at least MIN_TICKS (a 6-tick
-- minute after a 7-tick one starved the drafted spread, #3478), or the one such count. A count under MIN_TICKS is a
-- minute that passed inside one tick: two in a row are a fast clock (every frame a minute frame, #3349), read as 1 so
-- the budget is the whole queue; a lone one is a stall (a world save, a GC pause, the last minute of a fast-forward)
-- and is not read, so the frames after a hitch do not each run the whole queue. TPM_DEFAULT before a count exists. A
-- count of 0 is no count: every minute event is followed by at least one tick (#3348-#3350), so 0 is only the boot's
-- first minute. At the onset of a fast clock one minute is still sized at the old tick count, and two minutes after a
-- 2-tick read the budget halves the queue: staleness, not lost time.
function K.sched.ticksPerMinute(last, prev)
    local S = K.sched
    local t = nil
    if last ~= nil and last >= S.MIN_TICKS then
        t = last
    end
    if prev ~= nil and prev >= S.MIN_TICKS then
        if t == nil or prev < t then
            t = prev
        end
    end
    if t ~= nil then
        return t
    end
    if last ~= nil and prev ~= nil and last >= 1 and prev >= 1 then
        return 1
    end
    return S.TPM_DEFAULT
end

-- The per-tick budget in ms: the minute's work spread over its ticks with headroom, never under the floor. Under a
-- fast clock (one tick a minute event) it is the whole queue's work, so every queued name runs each tick.
function K.sched.budgetMs(meanMs, queued, tpm)
    local need = meanMs * queued / tpm * K.sched.HEADROOM
    return K.max(K.sched.FLOOR_MS, need)
end

-- The most runs a tick may make at the mean cost: at least one, so the queue always moves.
function K.sched.runCap(budgetMs, meanMs)
    local n = math.floor(budgetMs / meanMs)
    if n < 1 then
        return 1
    end
    return n
end

-- The per-run mean, an EMA of each tick's timed cost a run, never under MIN_MEAN_MS.
function K.sched.ema(mean, perRun)
    if mean == nil then
        return K.max(K.sched.MIN_MEAN_MS, perRun)
    end
    return K.max(K.sched.MIN_MEAN_MS, mean + (perRun - mean) * K.sched.EMA_W)
end
