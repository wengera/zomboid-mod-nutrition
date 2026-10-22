-- NR_Kernel_Effects.lua -- the effects layer's pure kernel (T1-1):
-- the twelve-band vector and its change test, the protein-energy grade, the energy-availability band and accrual
-- factor, the composer that folds the declarative table (NR_Data_Effects.lua, passed in as an argument -- the
-- kernel never reads NR.data) into record.effects, the fatigue offset, the vanilla accrual and recovery factors,
-- the night-vision machine, Short Sighted, the intoxication target and the vitamin C cold credit. The model is the
-- formulas briefing's sections A1-A4, B1, B3-B5, D1-D3, F1-F2 and J1; the health drains are K.drain's
-- (NR_Kernel_Drain.lua, Plan 15 Task 4).
-- The coefficient set is a pure function of (the nutrient grades and rungs, the band vector, the closed-day pe and
-- ea, the flags, the dial snapshot) and is rebuilt only when K.effects.changed says the key moved; the
-- per-minute scalars (fOff, the night-vision machine, the intoxication target) bypass it.
-- The band vector b is a Lua array of twelve integers at the indices K.effects.B names (caf, wd, bac, alc, hang,
-- bg, iuS, debt, iu, dehyd, hypo, ex). The wd band carries round(4 x wd x cafTol): both withdrawal rows scale by
-- wdQ x cafTol (A4), so banding the product keeps the set a function of the bands.
-- Time: dtD is real game days (the night-vision counter does not take the onset dial); ah is game
-- hours. Sex is indexed 1 male, 2 female (Plan 3's convention). Slow-clock code with no fast region:
-- math.floor is used; every K.clamp / K.min / K.max / K.fluids / K.training reference is at call time.
local K = NutritionRevamp.kernel
K.effects = {}

-- The band vector's indices and length.
K.effects.B = {
    caf = 1, -- no row needed: an index
    wd = 2, -- no row needed: an index
    bac = 3, -- no row needed: an index
    alc = 4, -- no row needed: an index
    hang = 5, -- no row needed: an index
    bg = 6, -- no row needed: an index
    iuS = 7, -- no row needed: an index
    debt = 8, -- no row needed: an index
    iu = 9, -- no row needed: an index
    dehyd = 10, -- no row needed: an index
    hypo = 11, -- no row needed: an index
    ex = 12, -- no row needed: an index
}
K.effects.NB = 12 -- the band count, no row needed

-- The band steps and edges (A2). Every step is a game choice resting on open S1178 (the quantisation steps).
K.effects.BAND_EPS = 1e-9 -- a floating-point guard on floor(x / step) (0.3 / 0.1 is 2.9999999999999996), no row needed
K.effects.CAF_STEP = K.dials.get("effects.CAF_STEP")
K.effects.CAF_BANDS = K.dials.get("effects.CAF_BANDS")
K.effects.WD_BANDS = K.dials.get("effects.WD_BANDS")
-- The alcohol episode-peak edges, per cent BAC: S0813's 0.50 and 0.85 g/kg over 10 r with r 0.68 (open S1104).
K.effects.ALC_EDGES = {
    K.dials.get("effects.ALC_EDGES.1"),
    K.dials.get("effects.ALC_EDGES.2"),
}
-- The blood-glucose edges, mmol/L, descending: band 1 below 3.5, 2 below 3.0, 3 below 2.6.
K.effects.BG_EDGES = {
    K.dials.get("effects.BG_EDGES.1"),
    K.dials.get("effects.BG_EDGES.2"),
    K.dials.get("effects.BG_EDGES.3"),
}
K.effects.IUS_STEP = K.dials.get("effects.IUS_STEP")
K.effects.IUS_BANDS = K.dials.get("effects.IUS_BANDS")
-- The sleep-debt edges, hours: game choice mapping of S0993's nightly hours onto the debt (open S1157).
K.effects.DEBT_EDGES = {
    K.dials.get("effects.DEBT_EDGES.1"),
    K.dials.get("effects.DEBT_EDGES.2"),
}
K.effects.IU_STEP = K.dials.get("effects.IU_STEP")
K.effects.IU_BANDS = K.dials.get("effects.IU_BANDS")
-- The dehydration edges, per cent body mass.
K.effects.DEHYD_EDGES = {
    K.dials.get("effects.DEHYD_EDGES.1"),
    K.dials.get("effects.DEHYD_EDGES.2"),
    K.dials.get("effects.DEHYD_EDGES.3"),
    K.dials.get("effects.DEHYD_EDGES.4"),
    K.dials.get("effects.DEHYD_EDGES.5"),
    K.dials.get("effects.DEHYD_EDGES.6"),
    K.dials.get("effects.DEHYD_EDGES.7"),
    K.dials.get("effects.DEHYD_EDGES.8"),
}
K.effects.EX_STEP = K.dials.get("effects.EX_STEP")
K.effects.EX_BANDS = K.dials.get("effects.EX_BANDS")

-- Energy availability (closed day, kcal per kg lean mass): the band edges, descending, and the accrual knots.
K.effects.EA_EDGES = {
    K.dials.get("effects.EA_EDGES.1"),
    K.dials.get("effects.EA_EDGES.2"),
    K.dials.get("effects.EA_EDGES.3"),
}
K.effects.EA_FULL = K.dials.get("effects.EA_FULL")
K.effects.EA_MID = K.dials.get("effects.EA_MID")
K.effects.EA_MID_M = K.dials.get("effects.EA_MID_M")
K.effects.EA_LOW = K.dials.get("effects.EA_LOW")
K.effects.EA_LOW_M = K.dials.get("effects.EA_LOW_M")

-- The protein-energy grade (F1).
K.effects.PE_BMI_OK = K.dials.get("effects.PE_BMI_OK")
K.effects.PE_BMI_THIN = K.dials.get("effects.PE_BMI_THIN")
K.effects.PE_BMI_LOW = K.dials.get("effects.PE_BMI_LOW")
K.effects.PE_STARVED_3 = K.dials.get("effects.PE_STARVED_3")
K.effects.PE_STARVED_4 = K.dials.get("effects.PE_STARVED_4")
K.effects.PE_PROT_OK = K.dials.get("effects.PE_PROT_OK")
K.effects.PE_PROT_2 = K.dials.get("effects.PE_PROT_2")
K.effects.PE_PROT_3 = K.dials.get("effects.PE_PROT_3")

-- The aiming multiplier (D1): clamp(1 + AIM_K x IU, AIM_LO, AIM_HI), IU at the band's lower edge.
K.effects.AIM_K = K.dials.get("effects.AIM_K")
K.effects.AIM_LO = K.dials.get("effects.AIM_LO")
K.effects.AIM_HI = K.dials.get("effects.AIM_HI")

-- The fatigue offset (B1): fOff = min(DEBT_K x debtH, DEBT_F_MAX) - cafOffset + fOffNut; the caffeine offset's
-- ceiling CAF_OFF_MAX is the active stimulant set's (K.acute.C, Plan 15 Task 10).
K.effects.DEBT_K = K.dials.get("effects.DEBT_K")
K.effects.DEBT_F_MAX = K.dials.get("effects.DEBT_F_MAX")
K.effects.CAF_EC50 = K.dials.get("effects.CAF_EC50")
K.effects.CAF_TOL_BLUNT = K.dials.get("effects.CAF_TOL_BLUNT")

-- Caffeine at sleep (A4, B6): satC = clamp((caf - zero) / (full - zero), 0, 1).
K.effects.CAF_SLEEP_FULL = K.dials.get("effects.CAF_SLEEP_FULL")
K.effects.CAF_SLEEP_ZERO = K.dials.get("effects.CAF_SLEEP_ZERO")

-- The engine part of accrual (B3) and recovery (B4): vanilla's own factors, clamped.
K.effects.END_FLOOR = 0.3 -- VANILLA #2270: the endDef floor
K.effects.REST_DIV = 1.5 -- VANILLA #2271: sitting or resting divides the accrual
K.effects.M_LO = K.dials.get("effects.M_LO")
K.effects.M_HI = K.dials.get("effects.M_HI")
K.effects.R_LO = K.dials.get("effects.R_LO")
K.effects.R_HI = K.dials.get("effects.R_HI")

-- The night-vision machine (D2).
K.effects.NV_GRANT = K.dials.get("effects.NV_GRANT")
K.effects.NV_SLOW = K.dials.get("effects.NV_SLOW")
K.effects.NV_REGRANT = K.dials.get("effects.NV_REGRANT")
K.effects.NV_ZINC = K.dials.get("effects.NV_ZINC")

-- The intoxication target: clamp(100 x bac / INTOX_FULL_BAC, 0, 100), the full BAC the active stimulant set's
-- (K.acute.C: 0.20 % Realistic, 0.31 % Game; Plan 15 Task 10).
K.effects.INTOX_MAX = K.dials.get("effects.INTOX_MAX")

-- The vitamin C cold credit's gates (F2): replete, at least 200 mg/d, exerting, cold-exposed.
K.effects.CREDIT_E24 = K.dials.get("effects.CREDIT_E24")
K.effects.CREDIT_B1 = K.dials.get("effects.CREDIT_B1")
K.effects.CREDIT_COLD_H = K.dials.get("effects.CREDIT_COLD_H")

-- The B vitamins whose worst grade drives the stress rows (A4).
K.effects.BGROUP = {
    "thiamine",
    "riboflavin",
    "niacin",
    "vitB6",
    "folate",
    "vitB12",
}

-- A fresh record.effects (J1): every surface at its identity, the key unmatchable, the machine at rest.
function K.effects.new()
    return {
        epoch = 0,
        key = { ep = -1, day = -1, dials = 0, b = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 } },
        mNut = 1,
        rNut = 1,
        stressTarget = 0,
        unhappyTarget = 0,
        panicTarget = 0,
        foodSickTarget = 0,
        poisonTarget = 0,
        healMul = 1,
        bleedMul = 1,
        infectMul = 1,
        coldMul = 1,
        tempOffset = 0,
        tempHeat = 0,
        speedMul = 1,
        rowEndCap = 1,
        symCap = 1,
        enduranceCap = 1,
        stressFloor = 0,
        unhappyFloor = 0,
        pain = { [0] = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 },
        painOn = false,
        foodSickStep = 0,
        fOffNut = 0,
        bruise = 0,
        nightVision = false,
        shortSighted = false,
        aimMul = 1,
        fOff = 0,
        solAddH = 0,
        solMul = 1,
        pe = 1,
        ea = 30,
        nvDays = 0,
        own = { nv = false, ss = false },
        intoxTarget = 0,
        tempTarget = 0,
        mAcc = 1,
        rRec = 1,
    }
end

-- min(n, max(0, floor(x / w))) with the floating-point guard.
function K.effects.step(x, w, n)
    local q = math.floor(x / w + K.effects.BAND_EPS)
    return K.clamp(q, 0, n)
end

-- The count of ascending edges at or below x (0 .. #edges).
function K.effects.atOrAbove(x, edges)
    local n = 0
    -- edges is a kernel-built Lua array (no Java list), so # is its length
    for i = 1, #edges do
        if x >= edges[i] then
            n = i
        end
    end
    return n
end

-- The count of descending edges strictly above x (0 .. #edges).
function K.effects.below(x, edges)
    local n = 0
    -- edges is a kernel-built Lua array (no Java list), so # is its length
    for i = 1, #edges do
        if x < edges[i] then
            n = i
        end
    end
    return n
end

-- Fill the twelve integer bands in place from record.acute and record.fluids (A2). No allocation.
function K.effects.bands(b, acute, fluids)
    local E = K.effects
    local I = E.B
    b[I.caf] = E.step(acute.caf, E.CAF_STEP, E.CAF_BANDS)
    b[I.wd] = K.clamp(math.floor(acute.wd * acute.cafTol * E.WD_BANDS + 0.5), 0, E.WD_BANDS)
    local bac = 0
    if acute.bac > 0 then
        bac = 1
    end
    b[I.bac] = bac
    b[I.alc] = E.atOrAbove(acute.alcPeak, E.ALC_EDGES)
    local hang = 0
    if acute.hang == 1 then
        hang = 1
    end
    b[I.hang] = hang
    b[I.bg] = E.below(acute.bg, E.BG_EDGES)
    b[I.iuS] = E.step(acute.iuSleep, E.IUS_STEP, E.IUS_BANDS)
    b[I.debt] = E.atOrAbove(acute.debtH, E.DEBT_EDGES)
    b[I.iu] = E.step(acute.iu, E.IU_STEP, E.IU_BANDS)
    b[I.dehyd] = E.atOrAbove(fluids.dehydPct, E.DEHYD_EDGES)
    b[I.hypo] = K.fluids.hyponatGrade(fluids.naPlasma)
    b[I.ex] = E.step(acute.exEma, E.EX_STEP, E.EX_BANDS)
    return b
end

-- Whether the rebuild key moved: the nutrient epoch, the closed day, the dial snapshot or any band.
function K.effects.changed(key, ep, day, dials, b)
    if key.ep ~= ep or key.day ~= day or key.dials ~= dials then
        return true
    end
    local kb = key.b
    for i = 1, K.effects.NB do
        if kb[i] ~= b[i] then
            return true
        end
    end
    return false
end

-- Stamp the key element-wise (no allocation).
function K.effects.stampKey(key, ep, day, dials, b)
    key.ep = ep
    key.day = day
    key.dials = dials
    local kb = key.b
    for i = 1, K.effects.NB do
        kb[i] = b[i]
    end
    return key
end

-- The protein-energy grade 1..4 at the day close (F1): the worse of the energy side (BMI, 0 =
-- unknown; starved days) and the protein side (the 7-day mean g/kg/d; nil or negative = unknown, grade 1).
-- starvedDays is the acute record's calendar count of low-intake days (K.acute.refeedDay), S0115's days of little or no
-- intake, kept apart from the drain's continuous unfed clock (K.drain.unfedH, which a nibble resets): the two can
-- disagree by up to a day at a fast's start (Plan 15 close, L4).
function K.effects.peGrade(bmi, starvedDays, p7meanGkg)
    local E = K.effects
    local e = 1
    if bmi > 0 then
        if bmi < E.PE_BMI_LOW then
            e = 4
        elseif bmi < E.PE_BMI_THIN then
            e = 3
        elseif bmi < E.PE_BMI_OK then
            e = 2
        end
    end
    if starvedDays > E.PE_STARVED_4 then
        e = 4
    elseif starvedDays > E.PE_STARVED_3 then
        e = K.max(e, 3)
    end
    local p = 1
    if p7meanGkg ~= nil and p7meanGkg >= 0 then
        if p7meanGkg < E.PE_PROT_3 then
            p = 4
        elseif p7meanGkg < E.PE_PROT_2 then
            p = 3
        elseif p7meanGkg < E.PE_PROT_OK then
            p = 2
        end
    end
    return K.max(e, p)
end

-- The energy-availability band for the cold rows: 0 at 30 or more, 1 in [20, 30), 2 in [10, 20), 3 below 10.
function K.effects.eaBand(ea)
    return K.effects.below(ea, K.effects.EA_EDGES)
end

-- The accrual factor of a low energy availability (A4): 1 at 30 or more, linear to 1.25 at 15 and to 1.40 at 5,
-- held below.
function K.effects.eaAccrual(ea)
    local E = K.effects
    if ea >= E.EA_FULL then
        return 1
    end
    if ea >= E.EA_MID then
        return 1 + (E.EA_MID_M - 1) * (E.EA_FULL - ea) / (E.EA_FULL - E.EA_MID)
    end
    if ea >= E.EA_LOW then
        return E.EA_MID_M + (E.EA_LOW_M - E.EA_MID_M) * (E.EA_MID - ea) / (E.EA_MID - E.EA_LOW)
    end
    return E.EA_LOW_M
end

-- The selector's value for a row: a grade, a rung, a band, the pe grade, the ea band or a flag.
function K.effects.selValue(row, nut, b, pe, ea, flags)
    local on = row.on
    if on == "grade" then
        return nut[row.src].g
    end
    if on == "rung" then
        return nut[row.src].x
    end
    if on == "band" then
        return b[K.effects.B[row.src]]
    end
    if on == "pe" then
        return pe
    end
    if on == "ea" then
        return K.effects.eaBand(ea)
    end
    return flags[row.src]
end

-- Whether a selector value matches at: nil matches true; a {lo, hi} matches a number in the inclusive range;
-- a number matches itself.
function K.effects.atMatch(v, at)
    if at == nil then
        return v == true
    end
    if type(at) == "table" then
        return type(v) == "number" and v >= at[1] and v <= at[2]
    end
    return v == at
end

-- Whether a row folds: its gate on (VITD_EFFECTS -> vitdOn, BalanceBonus -> bonusOn, any other -> off), its
-- unless flag not true, its stimulant set (stim, Plan 15 Task 10) the flags' stim (nil reads 1, Game, the option's
-- default), its selector matching.
function K.effects.active(row, nut, b, pe, ea, flags, bonusOn, vitdOn)
    if row.stim ~= nil and row.stim ~= (flags.stim or 1) then
        return false
    end
    local g = row.gated
    if g == "VITD_EFFECTS" and not vitdOn then
        return false
    end
    if g == "BalanceBonus" and not bonusOn then
        return false
    end
    if g ~= nil and g ~= "VITD_EFFECTS" and g ~= "BalanceBonus" then
        return false
    end
    if row.unless ~= nil and flags[row.unless] == true then
        return false
    end
    return K.effects.atMatch(K.effects.selValue(row, nut, b, pe, ea, flags), row.at)
end

-- One fold step by the surface's operator.
function K.effects.fold(op, cur, v)
    if op == "mul" then
        return cur * v
    end
    if op == "add" then
        return cur + v
    end
    if op == "max" then
        return K.max(cur, v)
    end
    if op == "min" then
        return K.min(cur, v)
    end
    return cur or v ~= 0
end

-- Fold every active row's entries: the penalty pass (bonusPass false) takes the entries without bonus, the
-- bonus pass the two exceptions.
function K.effects.foldRows(E, T, nut, b, pe, ea, flags, bonusOn, vitdOn, bonusPass)
    local S = T.SURF
    local rows = T.ROWS
    -- ROWS and each list are Lua arrays the data file builds (no Java list), so # is their length
    for i = 1, #rows do
        local row = rows[i]
        if K.effects.active(row, nut, b, pe, ea, flags, bonusOn, vitdOn) then
            local list = row.list
            for j = 1, #list do
                local e = list[j]
                if (e.bonus == true) == bonusPass then
                    E[e.s] = K.effects.fold(S[e.s].op, E[e.s], e.v)
                end
            end
        end
    end
    return E
end

-- The Severity dial on one folded surface: mul 1 + (v - 1) x sev, add v x sev, a boolean with
-- sevMin false below it; a max surface (identity 0) v x sev, a min surface (identity 1) 1 - (1 - v) x sev, or, with a
-- sevMin, v at or above it and 1 below (an on/off effect, never partial: the Overfull slowing, Plan 15 Task 8 fix 1); the
-- machine surfaces untouched (surfaceStep skips them).
function K.effects.sevScale(op, v, sev, sevMin)
    if op == "mul" then
        return 1 + (v - 1) * sev
    end
    if op == "add" then
        return v * sev
    end
    if op == "max" then
        return v * sev
    end
    if op == "min" and sevMin ~= nil then
        if sev < sevMin then
            return 1
        end
        return v
    end
    if op == "min" then
        return 1 - (1 - v) * sev
    end
    if op == "or" and sevMin ~= nil and sev < sevMin then
        return false
    end
    return v
end

-- One surface's step of the composer: 1 resets it to its identity, 2 applies the Severity dial, 3 clamps it.
-- A machine surface (nightVision) is left to its own function.
function K.effects.surfaceStep(E, name, s, stage, sev)
    if s.machine then
        return E
    end
    if stage == 1 then
        E[name] = s.id
        return E
    end
    if stage == 2 then
        E[name] = K.effects.sevScale(s.op, E[name], sev, s.sevMin)
        return E
    end
    if s.lo ~= nil then
        E[name] = K.clamp(E[name], s.lo, s.hi)
    end
    return E
end

-- Compose record.effects from the table (A3's six steps): identity; the penalty fold (and the energy-availability
-- accrual factor on mNut); the Severity scaling; the bonus fold; the clamp; aimMul from the iu band; epoch + 1.
-- The machine surface (nightVision) is left to its own function, and E.enduranceCap (the lower of rowEndCap and the
-- symptom cap) to K.effects.symptoms, which the server runs every minute after any compose.
function K.effects.compose(E, T, nut, b, pe, ea, flags, sev, bonusOn, vitdOn)
    local S = T.SURF
    for name, s in pairs(S) do
        K.effects.surfaceStep(E, name, s, 1, sev)
    end
    K.effects.foldRows(E, T, nut, b, pe, ea, flags, bonusOn, vitdOn, false)
    E.mNut = E.mNut * K.effects.eaAccrual(ea)
    for name, s in pairs(S) do
        K.effects.surfaceStep(E, name, s, 2, sev)
    end
    K.effects.foldRows(E, T, nut, b, pe, ea, flags, bonusOn, vitdOn, true)
    for name, s in pairs(S) do
        K.effects.surfaceStep(E, name, s, 3, sev)
    end
    local A = K.effects
    E.aimMul = K.clamp(1 + A.AIM_K * b[A.B.iu] * A.IU_STEP, A.AIM_LO, A.AIM_HI)
    E.epoch = E.epoch + 1
    return E
end

-- The worst grade over the B vitamins (the stress rows' flag bgroupMax).
function K.effects.bgroupMax(nut)
    local m = 1
    local G = K.effects.BGROUP
    -- BGROUP is a kernel-built Lua array, so # is its length
    for i = 1, #G do
        m = K.max(m, nut[G[i]].g)
    end
    return m
end

-- The vitamin C cold credit's gate (F2): replete, at least 200 mg/d ingested over a day, an exerting day (a
-- training band-2 day, K.training.HARD_DAY_MIN, or 60 moderate minutes) and cold exposure on the 6 h memory.
function K.effects.coldCredit(vitCg, vitCe24, band1Day, band2Day, coldH)
    local E = K.effects
    if vitCg ~= 1 or vitCe24 < E.CREDIT_E24 or coldH < E.CREDIT_COLD_H then
        return false
    end
    if band2Day >= K.training.HARD_DAY_MIN then
        return true
    end
    return band1Day >= E.CREDIT_B1
end

-- The fatigue offset the writer adds to S + circ (B1): the felt debt, less caffeine's offset blunted by
-- tolerance, plus the nutritional offset. The offset's ceiling is the active stimulant set's (K.acute.C).
function K.effects.fOff(debtH, caf, cafTol, fOffNut)
    local E = K.effects
    local debt = K.min(E.DEBT_K * debtH, E.DEBT_F_MAX)
    local cafOff = K.acute.C.CAF_OFF_MAX * caf / (caf + E.CAF_EC50) * (1 - E.CAF_TOL_BLUNT * cafTol)
    return debt - cafOff + fOffNut
end

-- Caffeine's saturation at sleep (A4, B6): 0 at 32.1 mg, 1 at 107 mg.
function K.effects.satC(caf)
    local E = K.effects
    return K.clamp((caf - E.CAF_SLEEP_ZERO) / (E.CAF_SLEEP_FULL - E.CAF_SLEEP_ZERO), 0, 1)
end

-- Vanilla's own accrual factors (B3, #2270) as one relative factor: the endurance deficit (floor 0.3), resting,
-- the thermoregulator's fatigue multiplier, the sleep trait and StatsDecrease, clamped.
function K.effects.mEngine(endLast, resting, thermoFatigue, sleepTrait, statsDecrease)
    local E = K.effects
    local m = K.max(E.END_FLOOR, 1 - endLast) / E.END_FLOOR
    if resting then
        m = m / E.REST_DIV
    end
    return K.clamp(m * thermoFatigue * sleepTrait * statsDecrease, E.M_LO, E.M_HI)
end

-- Vanilla's recovery factors (B4, #2276 / #2277): the bed ladder times the trait factor ff / t, clamped.
function K.effects.rEngine(bed, trait)
    local E = K.effects
    return K.clamp(bed * trait, E.R_LO, E.R_HI)
end

-- One night-vision minute (D2): while vitamin A is replete, zinc not depleted and the preformed-retinol
-- EMA meets the requirement, the counter runs (half speed under iron or riboflavin depletion); otherwise it drops
-- to NV_GRANT - NV_REGRANT at most and runs down. Returns whether the trait is wanted; stamps E.nightVision.
function K.effects.nvMinute(E, vitAg, zincG, ironG, riboG, retOk, dtD)
    local A = K.effects
    local cond = vitAg == 1 and zincG < A.NV_ZINC and retOk == true
    if cond then
        local rate = 1
        if ironG >= 3 or riboG >= 3 then
            rate = A.NV_SLOW
        end
        E.nvDays = E.nvDays + dtD * rate
    else
        E.nvDays = K.max(0, K.min(E.nvDays, A.NV_GRANT - A.NV_REGRANT) - dtD)
    end
    local want = cond and E.nvDays >= A.NV_GRANT
    E.nightVision = want
    return want
end

-- Short Sighted (D3): clinical vitamin A at Severity 1 or more.
function K.effects.ssWant(vitAg, sev)
    return vitAg == 4 and sev >= 1
end

-- The INTOXICATION target: 100 x bac / the active stimulant set's INTOX_FULL_BAC, clamped to the stat's range.
function K.effects.intoxTarget(bac)
    local E = K.effects
    return K.clamp(E.INTOX_MAX * bac / K.acute.C.INTOX_FULL_BAC, 0, E.INTOX_MAX)
end

-- The temperature offset the writer targets (G): the composed surface.
function K.effects.tempOffset(E)
    return E.tempOffset
end

-- The symptoms of the lethal causes (Plan 18; spec docs/superpowers/specs/2026-10-21-symptoms-design.md, sections 1-2):
-- each cause code 1-7 of K.drain carries a list of rows in the table's SYMPTOMS.CAUSES (NR_Data_Effects.lua), read on the
-- cause's progress p = 1 - D.frac[code], 0 at onset and 1 at its death point, so the symptoms follow the death pace and
-- ease while the ceiling recovers (Plan 17 R2). A row names a lever (endurance, pain, stress, unhappy), a shape (flat,
-- linear, knots) and its magnitude; pain also names its body parts. Overlap: the lowest endurance cap, pain summed per
-- body part under a cap, the highest stress and unhappiness floors. Pain applies only while the cause is active (its
-- bit in D.mask), never while it is merely recovering. Severity scales every magnitude (a cap by the min surface's
-- 1 - (1 - v) x sev); Overlay (vanilla owns HUNGER and THIRST) drops the causes marked overlayOff. Per minute, with no
-- allocation; with no cause applied the loop never runs.
K.effects.PAIN_PARTS = 17 -- BodyPartType's 17 parts, indices 0..16 (MAX excluded): no row needed
-- The pain modifier per part index (VANILLA BodyPartType.<clinit> L13-L29, the first float argument painModifier,
-- BodyPartType.<init> @11-@14 L51; read on 42.21, Plan 18 Task 1 J5): PAIN's target is the sum of part pain x it.
K.effects.PAIN_MOD = {
    [0] = 0.5, -- VANILLA L13: Hand_L
    0.5, -- VANILLA L14: Hand_R
    0.6, -- VANILLA L15: ForeArm_L
    0.6, -- VANILLA L16: ForeArm_R
    0.6, -- VANILLA L17: UpperArm_L
    0.6, -- VANILLA L18: UpperArm_R
    0.7, -- VANILLA L19: Torso_Upper
    0.78, -- VANILLA L20: Torso_Lower (the float 0.7799999713897705)
    0.8, -- VANILLA L21: Head
    0.8, -- VANILLA L22: Neck
    0.7, -- VANILLA L23: Groin
    0.7, -- VANILLA L24: UpperLeg_L
    0.7, -- VANILLA L25: UpperLeg_R
    0.6, -- VANILLA L26: LowerLeg_L
    0.6, -- VANILLA L27: LowerLeg_R
    0.5, -- VANILLA L28: Foot_L
    0.5, -- VANILLA L29: Foot_R
}
-- Half of one game minute's added-pain decay per real minute of day length: VANILLA BodyPart.DamageUpdate @2312-@2353
-- L500-L503 lowers it 0.005 a multiplier unit (Plan 18 Task 1 J3), 2 x dayMin units a game minute (#2922), so 0.01 x
-- dayMin a minute; measured 0.899983361325089 at the 90-minute day (x491-20261021-061440) and 0.15000031795638447 at
-- the 15-minute day (x492-20261021-062157). Added on top of a part's set value, it centres the dip between writes.
-- Centred, a cause's summed PAIN target stays inside Pain level 1 while 0.005 x dayMin x the sum of its parts' modifiers is
-- under 5: to about dayMin 833 for both lower legs, 1250 for Head and 1282 for Torso_Lower; on a longer day no
-- once-a-minute set holds level 1 (a limitation for the guide).
K.effects.PAIN_HALF_DIP = 0.005 -- VANILLA BodyPart.DamageUpdate L500-L503 (the comment above)
-- A cause code's bit in D.mask and D.recovering, 2^(code - 1) (K.drain.consider): no row needed.
K.effects.BIT = { 1, 2, 4, 8, 16, 32, 64 }

-- A shape's value at progress p (0..1): flat v; linear from a at p 0 to b at p 1; knots, a flat array of (p, v) pairs
-- in ascending p, piecewise linear between them and held beyond the first and the last.
function K.effects.shapeAt(r, p)
    local sh = r.shape
    if sh == "flat" then
        return r.v
    end
    if sh == "linear" then
        return r.a + (r.b - r.a) * p
    end
    local k = r.k
    -- k is a Lua array the data file builds (no Java list), so # is its length
    local n = #k
    if p <= k[1] then
        return k[2]
    end
    for i = 3, n - 1, 2 do
        if p <= k[i] then
            local p0 = k[i - 2]
            local v0 = k[i - 1]
            return v0 + (k[i + 1] - v0) * (p - p0) / (k[i] - p0)
        end
    end
    return k[n]
end

-- Whether a cause code's bit is set in a mask (D.mask or D.recovering).
function K.effects.hasBit(mask, code)
    return math.floor(mask / K.effects.BIT[code]) % 2 == 1
end

-- One cause's rows folded into the running cap and floors (returned) and, while active, its pain into E.pain.
function K.effects.symptomRows(E, list, p, active, sev, cap, st, un)
    -- list is a Lua array the data file builds (no Java list), so # is its length
    for j = 1, #list do
        local r = list[j]
        local lever = r.lever
        local v = K.effects.shapeAt(r, p)
        if lever == "endurance" then
            cap = K.min(cap, 1 - (1 - v) * sev)
        elseif lever == "stress" then
            st = K.max(st, v * sev)
        elseif lever == "unhappy" then
            un = K.max(un, v * sev)
        elseif lever == "pain" and active then
            K.effects.painShare(E, r.parts, v * sev)
        end
    end
    return cap, st, un
end

-- A cause's PAIN target t shared across its parts: each part gains t / n / its modifier of added pain.
function K.effects.painShare(E, parts, t)
    if not (t > 0) then
        return
    end
    local P = E.pain
    local mod = K.effects.PAIN_MOD
    -- parts is a Lua array the data file builds (no Java list), so # is its length
    local share = t / #parts
    for k = 1, #parts do
        local i = parts[k]
        P[i] = P[i] + share / mod[i]
    end
    E.painOn = true
end

-- Each painful part capped at top / its modifier (the level-1 band's top at Severity 1), then the half dip added,
-- centring the minute's fall on the target.
function K.effects.painCap(P, top, dayMin)
    local A = K.effects
    local dip = A.PAIN_HALF_DIP * dayMin
    for i = 0, A.PAIN_PARTS - 1 do
        if P[i] > 0 then
            P[i] = K.min(P[i], top / A.PAIN_MOD[i]) + dip
        end
    end
end

-- The minute's symptoms (spec sections 1.1-1.6): E.symCap (the causes' lowest endurance cap, clamped), E.enduranceCap
-- (the lower of it and the rows' Overfull cap), E.stressFloor and E.unhappyFloor (the highest, clamped), E.pain[i] (the
-- added pain per part index, summed, capped at the level-1 band's top over the part's modifier, plus the half dip on
-- every day length; 0 when none) and E.painOn (any pain). T is the effects table, D record.drain (frac, mask, recovering), sev
-- the Severity dial, overlay Mode 2, dayMin the day length (read only for pain; 0 when no cause is active).
function K.effects.symptoms(E, T, D, sev, overlay, dayMin)
    local S = T.SYMPTOMS
    local P = E.pain
    if E.painOn then
        for i = 0, K.effects.PAIN_PARTS - 1 do
            P[i] = 0
        end
        E.painOn = false
    end
    local cap = 1
    local st = 0
    local un = 0
    if D.mask > 0 or D.recovering > 0 then
        local C = S.CAUSES
        -- CAUSES is a Lua array the data file builds (no Java list), so # is its length
        for code = 1, #C do
            local c = C[code]
            local f = D.frac[code]
            if f ~= nil and not (overlay and c.overlayOff) then
                local active = K.effects.hasBit(D.mask, code)
                cap, st, un = K.effects.symptomRows(E, c.list, K.clamp(1 - f, 0, 1), active, sev, cap, st, un)
            end
        end
    end
    if E.painOn then
        K.effects.painCap(P, S.PAIN_TOP * sev, dayMin)
    end
    E.symCap = K.clamp(cap, S.CAP_LO, 1)
    E.enduranceCap = K.min(E.rowEndCap, E.symCap)
    E.stressFloor = K.min(st, S.STRESS_HI)
    E.unhappyFloor = K.min(un, S.UNHAPPY_HI)
    return E
end
