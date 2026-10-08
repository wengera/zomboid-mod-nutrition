-- NR_Kernel_Sched.lua -- the slow minute's budgeted queue (Plan 11 Task 9; Decision 6 (b); rules #3497 and #3444):
-- which names run their minute and how many a tick. Pure: lists and numbers in, lists and numbers out.
local K = NutritionRevamp.kernel
K.sched = {}

K.sched.FLOOR_MS = 15 -- #3489, #3490: the smallest fixed cap that starved none at N = 60 at both spacings (Decision 6)
K.sched.HEADROOM = 1.5 -- game choice (Plan 11 ruling 2): 15 ms over the 10 ms that ran at the margin (#3476)
K.sched.SEED_MS = 1.6 -- #3387: one player-run in play cost 1583 us; the mean before any run is timed
K.sched.MIN_MEAN_MS = 0.1 -- game choice: a run timed at 0 ms on the 1 ms clock never drives the cap to infinity
K.sched.EMA_W = 0.2 -- game choice: the weight the harness's budget arm used (ghost.load budget<ms>)
K.sched.TPM_DEFAULT = 6 -- #3346: 6.27 ticks a game minute at DayLength 1, the shortest day measured

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

-- The ticks a minute the budget divides by: the smaller of the last two minutes' counts (a 6-tick minute after a
-- 7-tick one starved the drafted spread, #3478); TPM_DEFAULT before a count exists. A count of 0 is no count: every
-- minute event is followed by at least one tick (#3348-#3350), so 0 is only the boot's first minute.
function K.sched.ticksPerMinute(last, prev)
    local t = last
    if t == nil or t < 1 then
        t = K.sched.TPM_DEFAULT
    end
    if prev ~= nil and prev >= 1 and prev < t then
        t = prev
    end
    return t
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
