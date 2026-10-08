-- NR_Kernel_Nutrients.lua -- the generic nutrient record engine (Plan 4): one loop over a declarative record
-- table, stepping each record's pool once per game minute on the slow clock, grading it on its status
-- ladder, testing its excess ladder and bumping the epoch Plan 5 rebuilds its coefficients on.
-- The model (formulas briefing A0, A3, A7, A8; plan rulings 2, 4, 5, 18): each pool is the fraction p of
-- its replete store (1 = replete) and obeys dp/dt = kEff (i/R - p), i the absorbed intake per day and R the
-- absorbed requirement per day. Refinement of A0 (the controller's ruling): the step is the zero-order-hold
-- form p = p e + (1 - e) i/R with e = exp(-kEff dtD) and i = aAbs/dtD, exact at constant intake within a
-- step, so intake at the requirement holds p at 1 exactly; at zero intake it is the pure exp(-kEff t).
-- The records are injected as { ORDER = {key, ...}, REC = { [key] = rec } } (Task 7 writes them); this
-- file never names NR.data. The record fields read here: kind, R, scale, Rscale, absorb, k, pCap, ladder,
-- clinicalOnP2, p2Clinical, ul, chronic.perDay, chronic.store, acute.perKg, acute.abs, dialExp. Sex is indexed 1 male,
-- 2 female (Plan 3's K.body convention); ctx carries sex, w, eeMJ, pDay, dial, excessOn and two,
-- and optionally kMul, a table {[key] = multiplier} on a pool's rate k that the adapter owns (file-scope,
-- never allocated per minute); thiamine's alcohol term K.interact.thiamineAlcoholK is the first user.
-- Pure: numbers and Lua tables in, numbers and Lua tables out, no Java. Slow-clock code with no fast region,
-- so math.exp and math.log are allowed. This file sorts after NR_Kernel.lua, and every K.max reference is
-- at call time.
local K = NutritionRevamp.kernel
K.nutrients = {}

-- The record.nutrients schema version.
K.nutrients.NV = 1

-- The generic status ladder on p, {marginal, depleted, clinical}, where a record has no sourced rung.
K.nutrients.LADDER = { 0.70, 0.45, 0.25 } -- design-phase-v1 game choice, ruling 4 (open row S1057: the store fractions at the three rungs)

-- The grade hysteresis: a grade improves one rung only when p clears that rung's threshold by HYST.
K.nutrients.HYST = 0.02 -- game choice, ruling 4

-- The days a chronic-excess threshold must hold before rung 2.
K.nutrients.EXCESS_HOLD_D = 7 -- game choice, ruling 4 (open row S1058)

-- The hours an acute excess flag stays raised after the eat that set it.
K.nutrients.ACUTE_DECAY_H = 48 -- the 48 h vomiting window, S1028

-- The replete-to-clinical days at zero intake above which a record takes the onset dial.
K.nutrients.DIAL_SLOW_DAYS = 90 -- game choice, ruling 5

-- The acute per-kg dose counts ACUTE_EMPTY_MULT times on a stomach filled below ACUTE_EMPTY_FILL.
K.nutrients.ACUTE_EMPTY_FILL = 0.2 -- game choice, ruling 18 (S1032 gives the direction only)
K.nutrients.ACUTE_EMPTY_MULT = 1.5 -- game choice, ruling 18 (S1032 gives the direction only)

-- The kinds whose step is not ctx.two's: pool is stepped here, the rest are not stepped at all.
K.nutrients.NO_TWO = { pool = true, ledger = true, fast = true, acute = true }

-- The kinds that are never graded: they keep g = 1.
K.nutrients.UNGRADED = { ledger = true, excessOnly = true, fast = true, acute = true }

-- The onset rate k (/day) that takes a pool from replete to the fraction f in the given days at zero intake.
function K.nutrients.calib(f, days)
    return math.log(1 / f) / days
end

-- The onset rate when the onset was observed at a nonzero intake i0 (i0overR = i0/R).
function K.nutrients.calibAt(f, days, i0overR)
    return -math.log((f - i0overR) / (1 - i0overR)) / days
end

-- The rate from a half-life in days.
function K.nutrients.kFromHalfLife(tHalf)
    return math.log(2) / tHalf
end

-- The clinical fraction as the steady state of a threshold intake.
function K.nutrients.fFromThreshold(iThreshold, R)
    return iThreshold / R
end

-- A fresh per-key state: replete, graded 1, no excess. ax is the acute flag's hours left and axr the rung it stamped.
function K.nutrients.newKey()
    return { p = 1, p2 = 1, g = 1, gl = 1, ah = 0, x = 0, e24 = 0, dmg = 0, ext = 0, ax = 0, axr = 0 }
end

-- A fresh record.nutrients for the given records.
function K.nutrients.newState(records)
    local state = { nv = K.nutrients.NV, epoch = 0, allReplete = true, ironGrade = 1, anaemia = false, vitDClinical = false }
    -- ORDER is a Lua table the record file built, so # is a Lua length, never a Java list (#0940).
    for i = 1, #records.ORDER do
        state[records.ORDER[i]] = K.nutrients.newKey()
    end
    return state
end

-- The record's ladder, or the generic one.
function K.nutrients.ladderOf(rec)
    if rec.ladder ~= nil then
        return rec.ladder
    end
    return K.nutrients.LADDER
end

-- The absorbed requirement per day for this character: R[sex], scaled, times the default absorption. The default absorption is a game choice (open row S1060).
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

-- The onset dial's exponent (ruling 5): 1 when the record's replete-to-clinical time at zero intake
-- exceeds DIAL_SLOW_DAYS, else 0; an explicit rec.dialExp wins; a record with no k is never dialled.
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

-- The effective rate: k times the dial for a slow record, k unchanged for a fast one.
function K.nutrients.kEff(rec, k, dial)
    if K.nutrients.dialExp(rec) == 1 then
        return k * dial
    end
    return k
end

-- The repletion cap (A3): p held at pCap when the record has one.
function K.nutrients.cap(s, rec)
    if type(rec.pCap) == "number" then
        if s.p > rec.pCap then
            s.p = rec.pCap
        end
    end
end

-- One first-order step of dtD days with aAbs absorbed (record units) over it, R the absorbed requirement
-- per day, in the zero-order-hold form; then the cap. A zero step is a no-op; a zero R adds no intake.
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

-- The grade of p on the ladder: 1 replete (p > marginal), 2 marginal, 3 depleted, 4 clinical (p <= clinical).
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

-- The grade with hysteresis upward only: a worse grade applies at once; a better one climbs from gPrev one
-- rung at a time while p clears the next rung's threshold by HYST.
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

-- A two-compartment grade (rec.clinicalOnP2): marginal and depleted on the store p, clinical on the
-- functional p2 alone, with the same upward hysteresis on leaving clinical.
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

-- The excess ladder (A7): e24, the 1-day exponential sum of the INGESTED amount; rung 1 at e24 >= ul;
-- rung 2 when e24 has exceeded chronic.perDay for EXCESS_HOLD_D days (ext counts them, 0 when not) or p
-- has reached chronic.store; the acute flag ax (hours left) decays and holds its stamped rung axr. Returns
-- the rung 0..3. w is the body mass, kept for a per-kg UL (none ships in Plan 4).
function K.nutrients.excess(s, rec, aIngested, dtD, w)
    s.e24 = s.e24 * math.exp(-dtD) + aIngested
    local rung = 0
    if rec.ul ~= nil then
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

-- The acute test on one eat's ingested dose (ruling 18) -> rung 0, 2 or 3: acute.perKg = {r2, r3} on the
-- dose per kg (times ACUTE_EMPTY_MULT on an emptyish stomach), acute.abs on the absolute dose. The caller
-- stamps s.ax = ACUTE_DECAY_H and s.axr = the rung.
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

-- The grade of a key in the state, 1 (neutral) when the key is absent.
function K.nutrients.gradeOf(state, key)
    local s = state[key]
    if s == nil then
        return 1
    end
    return s.g
end

-- Whether every pool and pool2 record sits at grade 1 (the minute's allReplete, read off the grades the
-- state holds; a key the state lacks reads grade 1).
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

-- The anaemia aggregate (A8): iron, folate, B6 or copper clinical, or B12's functional p2 below 1.
function K.nutrients.anaemic(state)
    if K.nutrients.gradeOf(state, "iron") == 4 then
        return true
    end
    if K.nutrients.gradeOf(state, "folate") == 4 then
        return true
    end
    if K.nutrients.gradeOf(state, "vitB6") == 4 then
        return true
    end
    if K.nutrients.gradeOf(state, "copper") == 4 then
        return true
    end
    local b12 = state.vitB12
    if b12 ~= nil then
        if b12.p2 < 1 then
            return true
        end
    end
    return false
end

-- One slow-clock pass of dtM minutes over every record: the step by kind (pool here; pool2, counter,
-- derived and excessOnly through the injected ctx.two(key, s, rec, aAbs, ctx, dtD, dtH) then the cap;
-- ledger, fast and acute not stepped), the excess (forced to 0 at the output when ctx.excessOn == false,
-- the state still integrating), the grade, the bookkeeping (gl, g, x, ah, epoch), then the aggregates.
-- absorbed and ingested are vectors by key in record units for this pass; a missing key reads 0.
function K.nutrients.minute(state, records, absorbed, ingested, ctx, dtM)
    local dtD = dtM / 1440
    local dtH = dtM / 60
    local dial = ctx.dial
    if dial == nil then
        dial = 1
    end
    -- ORDER is a Lua table the record file built, so # is a Lua length, never a Java list (#0940).
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
