-- NR_Kernel_Nutrients.lua -- the generic nutrient record engine: one loop over a declarative record table, stepping each
-- pool once a slow minute, grading it and testing its excess ladder. Each pool is the fraction p of its replete store,
-- dp/dt = kEff (i/R - p), stepped in the zero-order-hold form p = p e + (1 - e) i/R, e = exp(-kEff dtD), so intake at
-- the requirement holds p at 1 exactly. The records are injected; this file never names NR.data. ctx.kMul is a
-- file-scope table the adapter owns, never allocated per minute. Slow-clock code, so math.exp and math.log are allowed.
local K = NutritionRevamp.kernel
K.nutrients = {}

-- Every dial's meaning and source is its row in NR_Data_Dials.lua.
K.nutrients.LADDER = { K.dials.get("nutrients.LADDER.1"), K.dials.get("nutrients.LADDER.2"), K.dials.get("nutrients.LADDER.3") }

K.nutrients.HYST = K.dials.get("nutrients.HYST")

K.nutrients.EXCESS_HOLD_D = K.dials.get("nutrients.EXCESS_HOLD_D")

K.nutrients.ACUTE_DECAY_H = K.dials.get("nutrients.ACUTE_DECAY_H")

K.nutrients.DIAL_SLOW_DAYS = K.dials.get("nutrients.DIAL_SLOW_DAYS")

K.nutrients.ACUTE_EMPTY_FILL = K.dials.get("nutrients.ACUTE_EMPTY_FILL")
K.nutrients.ACUTE_EMPTY_MULT = K.dials.get("nutrients.ACUTE_EMPTY_MULT")

-- Pool is stepped here; the rest are not stepped at all.
K.nutrients.NO_TWO = { pool = true, ledger = true, fast = true, acute = true }

K.nutrients.UNGRADED = { ledger = true, excessOnly = true, fast = true, acute = true }

function K.nutrients.calib(f, days)
    return math.log(1 / f) / days
end

-- i0overR = i0/R: the onset observed at a nonzero intake.
function K.nutrients.calibAt(f, days, i0overR)
    return -math.log((f - i0overR) / (1 - i0overR)) / days
end

function K.nutrients.kFromHalfLife(tHalf)
    return math.log(2) / tHalf
end

function K.nutrients.fFromThreshold(iThreshold, R)
    return iThreshold / R
end

-- ax is the acute flag's hours left and axr the rung it stamped.
function K.nutrients.newKey()
    return { p = 1, p2 = 1, g = 1, gl = 1, ah = 0, x = 0, e24 = 0, dmg = 0, ext = 0, ax = 0, axr = 0 }
end

function K.nutrients.newState(records)
    local state = { epoch = 0, allReplete = true, ironGrade = 1, anaemia = false, vitDClinical = false }
    -- ORDER is a Lua table, so # is a Lua length, never a Java list (#0940).
    for i = 1, #records.ORDER do
        state[records.ORDER[i]] = K.nutrients.newKey()
    end
    return state
end

function K.nutrients.ladderOf(rec)
    if rec.ladder ~= nil then
        return rec.ladder
    end
    return K.nutrients.LADDER
end

-- The default absorption is a game choice (open row S1060).
function K.nutrients.requirement(rec, ctx)
    if rec.R == nil then
        return 0
    end
    local r = rec.R[ctx.sex]
    local scale = rec.scale
    if scale == "perMJ" then
        r = r * ctx.eeMJ
    elseif scale == "perKg" then
        r = r * ctx.w
    elseif scale == "perProteinGMax" then
        r = K.max(r, rec.Rscale * ctx.pDay)
    end
    if rec.absorb ~= nil then
        r = r * rec.absorb
    end
    return r
end

-- An explicit rec.dialExp wins; a record with no k is never dialled.
function K.nutrients.dialExp(rec)
    if rec.dialExp ~= nil then
        return rec.dialExp
    end
    if rec.k == nil then
        return 0
    end
    if math.log(1 / K.nutrients.ladderOf(rec)[3]) / rec.k > K.nutrients.DIAL_SLOW_DAYS then
        return 1
    end
    return 0
end

function K.nutrients.kEff(rec, k, dial)
    if K.nutrients.dialExp(rec) == 1 then
        return k * dial
    end
    return k
end

function K.nutrients.cap(s, rec)
    if type(rec.pCap) == "number" then
        if s.p > rec.pCap then
            s.p = rec.pCap
        end
    end
end

-- A zero step is a no-op; a zero R adds no intake.
function K.nutrients.stepPool(s, rec, aAbs, R, kEff, dtD)
    if dtD <= 0 then
        return s.p
    end
    local e = math.exp(-kEff * dtD)
    local iOverR = 0
    if R > 0 then
        iOverR = aAbs / dtD / R
    end
    s.p = s.p * e + (1 - e) * iOverR
    K.nutrients.cap(s, rec)
    return s.p
end

-- 1 replete (p > marginal), 2 marginal, 3 depleted, 4 clinical (p <= clinical).
function K.nutrients.grade(p, ladder)
    if p > ladder[1] then
        return 1
    end
    if p > ladder[2] then
        return 2
    end
    if p > ladder[3] then
        return 3
    end
    return 4
end

-- A worse grade applies at once; a better one climbs one rung at a time while p clears it by HYST.
function K.nutrients.gradeHyst(p, ladder, gPrev)
    local g = K.nutrients.grade(p, ladder)
    if g >= gPrev then
        return g
    end
    local h = gPrev
    while h > g and p > ladder[h - 1] + K.nutrients.HYST do
        h = h - 1
    end
    return h
end

-- Clinical reads the functional p2 alone; marginal and depleted read the store p.
function K.nutrients.gradeTwo(p, p2, ladder, gPrev, thrP2)
    local gp = gPrev
    if gp == 4 then
        gp = 3
    end
    local g = K.nutrients.gradeHyst(p, ladder, gp)
    if g == 4 then
        g = 3
    end
    local thr = thrP2
    if gPrev == 4 then
        thr = K.min(thr + K.nutrients.HYST, 1)
    end
    if p2 < thr then
        g = 4
    end
    return g
end

-- e24 is the 1-day exponential sum of the INGESTED amount. A "supplement" ulBasis is a UL set on supplemental forms,
-- which food intake never meets, so it raises no rung 1. Returns the rung 0..3.
function K.nutrients.excess(s, rec, aIngested, dtD, w)
    s.e24 = s.e24 * math.exp(-dtD) + aIngested
    local rung = 0
    if rec.ul ~= nil and rec.ulBasis ~= "supplement" then
        if s.e24 >= rec.ul then
            rung = 1
        end
    end
    local ch = rec.chronic
    if ch ~= nil then
        if ch.perDay ~= nil then
            if s.e24 > ch.perDay then
                s.ext = s.ext + dtD
            else
                s.ext = 0
            end
            local holdD = ch.holdD or K.nutrients.EXCESS_HOLD_D
            if s.ext >= holdD then
                rung = 2
            end
        end
        if type(ch.store) == "number" then
            if s.p >= ch.store then
                rung = 2
            end
        end
    end
    s.ax = K.max(s.ax - dtD * 24, 0)
    if s.ax > 0 then
        rung = K.max(rung, s.axr)
    end
    return rung
end

-- The caller stamps s.ax = ACUTE_DECAY_H and s.axr = the rung.
function K.nutrients.acuteTest(rec, doseIngested, w, stomachFill)
    local a = rec.acute
    if a == nil then
        return 0
    end
    if a.perKg ~= nil then
        local d = doseIngested / w
        if stomachFill < K.nutrients.ACUTE_EMPTY_FILL then
            d = d * K.nutrients.ACUTE_EMPTY_MULT
        end
        if d >= a.perKg[2] then
            return 3
        end
        if d >= a.perKg[1] then
            return 2
        end
        return 0
    end
    if doseIngested >= a.abs then
        return 2
    end
    return 0
end

function K.nutrients.gradeOf(state, key)
    local s = state[key]
    if s == nil then
        return 1
    end
    return s.g
end

-- A key the state lacks reads grade 1.
function K.nutrients.allRepleteOf(state, records)
    for i = 1, #records.ORDER do
        local key = records.ORDER[i]
        local kind = records.REC[key].kind
        if kind == "pool" or kind == "pool2" then
            if K.nutrients.gradeOf(state, key) ~= 1 then
                return false
            end
        end
    end
    return true
end

-- The Deficiency moodle reads the same list (K.view.deficiencyKeys), so a member added here shows there.
K.nutrients.ANAEMIA = { "iron", "folate", "vitB6", "copper" } -- the clinical grades that make the aggregate (A8), no row needed: the keys
function K.nutrients.anaemic(state)
    -- # on this file's own Lua array
    for i = 1, #K.nutrients.ANAEMIA do
        if K.nutrients.gradeOf(state, K.nutrients.ANAEMIA[i]) == 4 then
            return true
        end
    end
    local b12 = state.vitB12
    if b12 ~= nil then
        if b12.p2 < 1 then
            return true
        end
    end
    return false
end

-- One slow-clock pass of dtM minutes. The excess is forced to 0 at the output when ctx.excessOn == false while the
-- state still integrates. A missing key in absorbed or ingested reads 0.
function K.nutrients.minute(state, records, absorbed, ingested, ctx, dtM)
    local dtD = dtM / 1440
    local dtH = dtM / 60
    local dial = ctx.dial
    if dial == nil then
        dial = 1
    end
    -- ORDER is a Lua table, so # is a Lua length, never a Java list (#0940).
    for i = 1, #records.ORDER do
        local key = records.ORDER[i]
        local rec = records.REC[key]
        local s = state[key]
        if s == nil then
            s = K.nutrients.newKey()
            state[key] = s
        end
        local aAbs = absorbed[key] or 0
        local aIng = ingested[key] or 0
        local kind = rec.kind
        if kind == "pool" then
            local R = K.nutrients.requirement(rec, ctx)
            local k = rec.k
            if ctx.kMul ~= nil then
                local m = ctx.kMul[key]
                if m ~= nil then
                    k = k * m
                end
            end
            local kEff = K.nutrients.kEff(rec, k, dial)
            K.nutrients.stepPool(s, rec, aAbs, R, kEff, dtD)
        elseif K.nutrients.NO_TWO[kind] == nil then
            if type(ctx.two) == "function" then
                ctx.two(key, s, rec, aAbs, ctx, dtD, dtH)
                K.nutrients.cap(s, rec)
            end
        end
        local x = K.nutrients.excess(s, rec, aIng, dtD, ctx.w)
        if ctx.excessOn == false then
            x = 0
        end
        local g = 1
        if rec.clinicalOnP2 == true then
            g = K.nutrients.gradeTwo(s.p, s.p2, K.nutrients.ladderOf(rec), s.g, rec.p2Clinical or K.nutrients.ladderOf(rec)[3])
        elseif K.nutrients.UNGRADED[kind] == nil then
            g = K.nutrients.gradeHyst(s.p, K.nutrients.ladderOf(rec), s.g)
        end
        local changed = false
        if g ~= s.g then
            s.gl = s.g
            s.g = g
            s.ah = 0
            changed = true
        else
            s.ah = s.ah + dtH
        end
        if x ~= s.x then
            s.x = x
            changed = true
        end
        if changed then
            state.epoch = state.epoch + 1
        end
    end
    state.allReplete = K.nutrients.allRepleteOf(state, records)
    state.ironGrade = K.nutrients.gradeOf(state, "iron")
    state.anaemia = K.nutrients.anaemic(state)
    state.vitDClinical = K.nutrients.gradeOf(state, "vitD") == 4
    return state
end
