-- NR_Kernel_Effects.lua -- the effects layer's pure kernel (Plan 5, rulings 2, 5-6, 9-10, 12-13, 17-18, 23; T1-1):
-- the twelve-band vector and its change test, the protein-energy grade, the energy-availability band and accrual
-- factor, the composer that folds the declarative table (NR_Data_Effects.lua, passed in as an argument -- the
-- kernel never reads NR.data) into record.effects, the fatigue offset, the vanilla accrual and recovery factors,
-- the night-vision machine, Short Sighted, the health drains, the intoxication target and the vitamin C cold
-- credit. The model is the formulas briefing's sections A1-A4, B1, B3-B5, D1-D3, F1-F2, H2 and J1.
-- The coefficient set is a pure function of (the nutrient grades and rungs, the band vector, the closed-day pe and
-- ea, the flags, the dial snapshot) and is rebuilt only when K.effects.changed says the key moved (ruling 2); the
-- per-minute scalars (fOff, the night-vision machine, the drains, the intoxication target) bypass it.
-- The band vector b is a Lua array of twelve integers at the indices K.effects.B names (caf, wd, bac, alc, hang,
-- bg, iuS, debt, iu, dehyd, hypo, ex). The wd band carries round(4 x wd x cafTol): both withdrawal rows scale by
-- wdQ x cafTol (A4), so banding the product keeps the set a function of the bands.
-- Time: dtD is real game days (the night-vision counter does not take the onset dial, ruling 6); ah is game
-- hours. Sex is indexed 1 male, 2 female (Plan 3's convention). Slow-clock code with no fast region:
-- math.floor is used; every K.clamp / K.min / K.max / K.fluids / K.training reference is at call time.
local K = NutritionRevamp.kernel
K.effects = {}

-- The record.effects schema version.
K.effects.EV = 1 -- schema version, no row needed

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
K.effects.CAF_STEP = 50 -- mg: game choice step (open S1178)
K.effects.CAF_BANDS = 16 -- 800 mg, the panic row's top: game choice (open S1178)
K.effects.WD_BANDS = 4 -- quarters of wd x cafTol: game choice (open S1178)
-- The alcohol episode-peak edges, per cent BAC: S0813's 0.50 and 0.85 g/kg over 10 r with r 0.68 (open S1104).
K.effects.ALC_EDGES = {
    0.0735, -- 0.50 / 6.8, S0813 (r open S1104)
    0.125, -- 0.85 / 6.8, S0813 (r open S1104)
}
-- The blood-glucose edges, mmol/L, descending: band 1 below 3.5, 2 below 3.0, 3 below 2.6.
K.effects.BG_EDGES = {
    3.5, -- game choice: the report's former knee, read by no row (open S1178)
    3.0, -- S0897 / S0898 (impairment from 3.0)
    2.6, -- S0897 (2.6-3.0 the impairment band)
}
K.effects.IUS_STEP = 0.125 -- IU: 3 h awake: game choice (open S1178)
K.effects.IUS_BANDS = 12 -- 1.5 IU, the sleep term's cap (K.acute.IU_SLEEP_MAX): game choice (open S1178)
-- The sleep-debt edges, hours: game choice mapping of S0993's nightly hours onto the debt (open S1157).
K.effects.DEBT_EDGES = {
    4, -- S0993 (6-7 h a night); game choice map (open S1157)
    8, -- S0993 (under 6 h a night); game choice map (open S1157)
}
K.effects.IU_STEP = 0.1 -- IU: the aim multiplier's resolution 0.025: game choice (open S1178)
K.effects.IU_BANDS = 25 -- 2.5 IU, K.acute.IU_MAX: game choice (open S1178)
-- The dehydration edges, per cent body mass.
K.effects.DEHYD_EDGES = {
    1, -- S0894 (the studied range starts at 1 %)
    1.5, -- S0098 / S0099 (1.36-1.59 %)
    2, -- S0706 / S0707 / S0895 (the 2 % line)
    2.5, -- game choice curve knot (open S1121)
    3, -- game choice curve knot (open S1121)
    4, -- S0895 / S0706 / S0707 (the 4 % line)
    6, -- the thirst level-4 region #0509
    10, -- severe dehydration (open S1101)
}
K.effects.EX_STEP = 7.5 -- minutes of exEma: a quarter of EX_FULL 30, game choice (open S1148)
K.effects.EX_BANDS = 4 -- full credit at 30 min: game choice (open S1148)

-- Energy availability (closed day, kcal per kg lean mass): the band edges, descending, and the accrual knots.
K.effects.EA_EDGES = {
    30, -- S0691 (unaffected at 30)
    20, -- S0990 (22 kcal/kg immune markers); game choice rung (open S1156)
    10, -- S0991 (OR 3.8 at the low end); game choice rung (open S1156)
}
K.effects.EA_FULL = 30 -- S0691: no accrual cost at or above
K.effects.EA_MID = 15 -- game choice extrapolation knot (open S0846)
K.effects.EA_MID_M = 1.25 -- game choice extrapolation (open S0846)
K.effects.EA_LOW = 5 -- game choice knot (open S0846)
K.effects.EA_LOW_M = 1.40 -- game choice extrapolation, held below 5 (open S0846)

-- The protein-energy grade (F1, ruling 18).
K.effects.PE_BMI_OK = 18.5 -- S0115
K.effects.PE_BMI_THIN = 17 -- game choice: the WHO thinness class (open S1179)
K.effects.PE_BMI_LOW = 16 -- S0115
K.effects.PE_STARVED_3 = 5 -- days, S0115
K.effects.PE_STARVED_4 = 10 -- days, S0115
K.effects.PE_PROT_OK = 0.8 -- g/kg/d, S0509
K.effects.PE_PROT_2 = 0.6 -- g/kg/d: game choice rung (open S1180)
K.effects.PE_PROT_3 = 0.4 -- g/kg/d: game choice rung (open S1180)

-- The aiming multiplier (D1, ruling 5): clamp(1 + AIM_K x IU, AIM_LO, AIM_HI), IU at the band's lower edge.
K.effects.AIM_K = 0.25 -- game choice (open S1134)
K.effects.AIM_LO = 0.90 -- game choice (open S1135); unreachable, the IU never falls below 0
K.effects.AIM_HI = 1.60 -- game choice (open S1135)

-- The fatigue offset (B1, ruling 11): fOff = min(DEBT_K x debtH, DEBT_F_MAX) - cafOffset + fOffNut.
K.effects.DEBT_K = 0.005 -- per debt hour: game choice, debt under-felt (S0742 direction; open S1131)
K.effects.DEBT_F_MAX = 0.10 -- game choice: 20 h of debt (open S1131)
K.effects.CAF_OFF_MAX = 0.35 -- game choice sized on S0900 vs S0750 (open S1124)
K.effects.CAF_EC50 = 150 -- mg: game choice (open S1124)
K.effects.CAF_TOL_BLUNT = 0.6 -- S0807 direction (tolerance to subjective effects); game choice (open S1125)

-- Caffeine at sleep (A4, B6): satC = clamp((caf - zero) / (full - zero), 0, 1).
K.effects.CAF_SLEEP_FULL = 107 -- mg, the coffee of S0797
K.effects.CAF_SLEEP_ZERO = 32.1 -- mg = 0.3 x 107: S0797 x S0793 (2^(-8.8/5) = 0.2952)

-- The engine part of accrual (B3) and recovery (B4): vanilla's own factors, clamped.
K.effects.END_FLOOR = 0.3 -- the endDef floor, VANILLA #2270
K.effects.REST_DIV = 1.5 -- sitting or resting divides the accrual, VANILLA #2270
K.effects.M_LO = 0.2 -- game choice clamp (open S1133)
K.effects.M_HI = 5.0 -- game choice clamp (open S1133)
K.effects.R_LO = 0.25 -- game choice clamp (open S1133)
K.effects.R_HI = 2.0 -- game choice clamp (open S1133)

-- The night-vision machine (D2, ruling 6).
K.effects.NV_GRANT = 14 -- days: game choice anchored on S0869's six weeks (open S1140)
K.effects.NV_SLOW = 0.5 -- the rate under iron or riboflavin depletion, S0871 direction; game choice (open S1141)
K.effects.NV_REGRANT = 3 -- days after a lapse: game choice hysteresis (open S1142)
K.effects.NV_ZINC = 3 -- zinc must stay under the depleted grade, S0872 / S0873 direction (open S0942)

-- The health drains (H2, ruling 13): health per game minute, indexed by the lethal code.
K.effects.DRAIN_RATE = {
    0.023148148148148147, -- 1 starvation: 100 in 72 h; game choice duration (open S1166)
    0.00992063492063492, -- 2 terminal scurvy: 100 in 168 h (S0965 can be fatal); game choice (open S1168)
    0.023148148148148147, -- 3 cardiac beriberi: 100 in 72 h (S0244 / S0245 rapid); game choice (open S1169)
    0.00496031746031746, -- 4 pellagra: 100 in 336 h (S0272 if untreated, death); game choice (open S1170)
    0.2777777777777778, -- 5 severe hyponatraemia: 100 in 6 h (S1047 respiratory failure); game choice (open S1171)
    0.1388888888888889, -- 6 severe dehydration: 100 in 12 h; game choice (open S1172)
    0.06944444444444445, -- 7 the iron lethal rung: 100 in 24 h (S1033); game choice (open S1173)
}
-- The fat fraction at which starvation's reserves count as exhausted, by sex.
K.effects.BF_FLOOR = {
    0.04, -- male: game choice (open S1167)
    0.10, -- female: game choice (open S1167)
}
K.effects.BMI_LETHAL = 12 -- kg/m2: S0112 direction (below 10 can be compatible with life); game choice (open S1166)
K.effects.SCURVY_H = 720 -- 30 days at clinical vitamin C: game choice (open S1168)
K.effects.BERIBERI_H = 168 -- 7 days at clinical thiamine: game choice (open S1169)
K.effects.PELLAGRA_H = 1440 -- 60 days at clinical niacin: game choice (open S1170)

-- The intoxication target (ruling 19): clamp(100 x bac / 0.20, 0, 100).
K.effects.INTOX_FULL_BAC = 0.20 -- per cent: game choice map (open S1106)
K.effects.INTOX_MAX = 100 -- the stat's range #2369

-- The vitamin C cold credit's gates (F2): replete, at least 200 mg/d, exerting, cold-exposed.
K.effects.CREDIT_E24 = 200 -- mg/d, S0980 (at least 0.2 g/d regular)
K.effects.CREDIT_B1 = 60 -- moderate minutes in the day: game choice (open S1155)
K.effects.CREDIT_COLD_H = 0.25 -- coldH hours on its 6 h memory: game choice (open S1155)

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
        ev = K.effects.EV,
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
        fOffNut = 0,
        bruise = 0,
        drain = 0,
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
        lethal = 0,
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

-- The protein-energy grade 1..4 at the day close (F1, ruling 18): the worse of the energy side (BMI, 0 =
-- unknown; starved days) and the protein side (the 7-day mean g/kg/d; nil or negative = unknown, grade 1).
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
-- unless flag not true, its selector matching.
function K.effects.active(row, nut, b, pe, ea, flags, bonusOn, vitdOn)
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

-- The Severity dial on one folded surface (ruling 23): mul 1 + (v - 1) x sev, add v x sev, a boolean with
-- sevMin false below it; a max surface (identity 0) v x sev, a min surface (identity 1) 1 - (1 - v) x sev; the
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
    if op == "min" then
        return 1 - (1 - v) * sev
    end
    if op == "or" and sevMin ~= nil and sev < sevMin then
        return false
    end
    return v
end

-- One surface's step of the composer: 1 resets it to its identity, 2 applies the Severity dial, 3 clamps it.
-- A machine surface (nightVision, drain) is left to its own function.
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
-- The machine surfaces (nightVision, drain) are left to their own functions.
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

-- The fatigue offset the fast clock adds to S + circ (B1): the felt debt, less caffeine's offset blunted by
-- tolerance, plus the nutritional offset.
function K.effects.fOff(debtH, caf, cafTol, fOffNut)
    local E = K.effects
    local debt = K.min(E.DEBT_K * debtH, E.DEBT_F_MAX)
    local cafOff = E.CAF_OFF_MAX * caf / (caf + E.CAF_EC50) * (1 - E.CAF_TOL_BLUNT * cafTol)
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

-- One night-vision minute (D2, ruling 6): while vitamin A is replete, zinc not depleted and the preformed-retinol
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

-- Short Sighted (D3, ruling 7): clinical vitamin A at Severity 1 or more.
function K.effects.ssWant(vitAg, sev)
    return vitAg == 4 and sev >= 1
end

-- The lethal pick: the larger rate wins (ties keep the earlier code).
function K.effects.pick(d, code, c)
    local r = K.effects.DRAIN_RATE[c]
    if r > d then
        return r, c
    end
    return d, code
end

-- The health drain per game minute (H2, ruling 13): the max over the active rows, its code on E.lethal (1
-- starvation, 2 scurvy, 3 beriberi, 4 pellagra, 5 hyponatraemia, 6 dehydration, 7 the iron rung); 0 and code 0
-- when canKill is false. Stamps E.drain.
function K.effects.drain(E, nut, fluids, acute, pe, bodyFatFrac, sex, canKill)
    local A = K.effects
    local d = 0
    local code = 0
    if canKill then
        if pe == 4 then
            if bodyFatFrac <= A.BF_FLOOR[sex] or (acute.bmi > 0 and acute.bmi < A.BMI_LETHAL) then
                d, code = A.pick(d, code, 1)
            end
        end
        if nut.vitC.g == 4 and nut.vitC.ah >= A.SCURVY_H then
            d, code = A.pick(d, code, 2)
        end
        if nut.thiamine.g == 4 and nut.thiamine.ah >= A.BERIBERI_H then
            d, code = A.pick(d, code, 3)
        end
        if nut.niacin.g == 4 and nut.niacin.ah >= A.PELLAGRA_H then
            d, code = A.pick(d, code, 4)
        end
        if K.fluids.hyponatGrade(fluids.naPlasma) == 3 then
            d, code = A.pick(d, code, 5)
        end
        if fluids.dehydPct >= K.fluids.SEVERE_DEHYD_PCT then
            d, code = A.pick(d, code, 6)
        end
        if nut.iron.x == 3 then
            d, code = A.pick(d, code, 7)
        end
    end
    E.drain = d
    E.lethal = code
    return d
end

-- The INTOXICATION target (ruling 19): 100 x bac / 0.20, clamped to the stat's range.
function K.effects.intoxTarget(bac)
    local E = K.effects
    return K.clamp(E.INTOX_MAX * bac / E.INTOX_FULL_BAC, 0, E.INTOX_MAX)
end

-- The temperature offset the fast handler targets (G): the composed surface.
function K.effects.tempOffset(E)
    return E.tempOffset
end
