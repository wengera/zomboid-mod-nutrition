-- NR_Kernel_View.lua -- the interface's row model (Plan 7 Task 3, rulings 2-5 and 8): the client's stored
-- mirror (the flat scalar table of NR_Kernel_Mirror.lua) in, at one of three visibility levels, and an array of
-- rows out; the six symptom classes the moodles show; the tooltip lines of one food's resolved vector
-- (K.vector.resolve). Pure: no engine global, no getText -- every label is a translation KEY and every text is
-- a KEY (isKey true: the class, band and grade words) or a formatted string, resolved by the client files.
-- One statement per line (the coverage gate is line-granular). This file sorts after NR_Kernel.lua,
-- NR_Kernel_Fluids.lua and NR_Kernel_Nutrients.lua; every K.* reference is at call time.
-- A row is { key, label, text, level, isKey } plus cls and n (the class level 0-4) on a class row; level is the
-- visibility level the row belongs to (1 Symptoms, 2 Bands, 3 Numbers). Labels: a class row UI_NR_Class_<cls>; a
-- grade row UI_NR_Row_<nutrient>; every other row UI_NR_Row_<mirror key without the nut_ prefix> (vitC_p,
-- vitC_x, body_weight, acute_caf ...); a tooltip line UI_NR_Tip_Source_<source> or UI_NR_Row_<vector key>.
-- Texts: UI_NR_Class_<cls>_<0-4>, UI_NR_Band_<band or none>, UI_NR_Grade_<1-4>, UI_NR_Tip_Rich, UI_NR_Tip_Low.
local K = NutritionRevamp.kernel
K.view = {}

-- The visibility levels (ruling 3): the server option NR.VisibilityMode reads 1..3 and a Nutritionist trait grants 3.
K.view.LEVEL = { SYMPTOMS = 1, BANDS = 2, NUMBERS = 3 }

-- The six symptom classes (ruling 5), closed, in display order.
K.view.CLASSES = { "energy", "hydration", "deficiency", "excess", "stimulant", "sleep" }

-- Each class ladder is the four ascending lower bounds of class levels 1-4; below the first the class reads 0.
-- energy: the K.energy.state scalar (0.5..2.0, 1 neutral; Plan 3 ruling 14 -- deficit, fat depletion and glycogen
-- depletion raise it, surplus lowers it; the mirror's 0 is a record with no body yet). The map: below 1.10 (neutral,
-- surplus or absent) 0; 1.10 1; 1.25 2; 1.50 3; 1.75 4.
K.view.ENERGY_AT = {
    1.10, -- gc: level 1, a 300 kcal trailing-24 h deficit alone (0.5 x 300/1500, K.energy.state); rests on Plan 3 ruling 14
    1.25, -- gc: level 2, a 750 kcal deficit or half the fat-depletion term; rests on Plan 3 ruling 14
    1.50, -- gc: level 3, the full 1500 kcal deficit term; rests on Plan 3 ruling 14
    1.75, -- gc: level 4, a full deficit with fat or glycogen depletion on top; rests on Plan 3 ruling 14
}

-- hydration: fluids_dehydPct (per cent of body mass) on the Plan 4 thirst ladder, K.fluids.THIRST_KNOTS -- the
-- vanilla thirst moodle levels 1-4 (#0509); the test pins these to the knots.
K.view.HYDRATION_AT = {
    1, -- gc: moodle level 1 at 1 % (Plan 4 ruling 8; open row S1098)
    2, -- level 2 on the 2 % performance threshold, S0092
    4, -- level 3 on the 4 % strain point, S0709
    6, -- gc: moodle level 4 at 6 % (Plan 4 ruling 8; open row S1098)
}

-- stimulant: acute_caf, the caffeine in the body in mg (K.acute.caffeine).
K.view.STIMULANT_AT = {
    50, -- gc: level 1, half a cup's worth on board; rests on S0899 (the rested effect) and S0900
    150, -- gc: level 2, about the 3 mg/kg effect dose at 50 kg (K.acute.CAF_EFFECT_MGKG, S0531); rests on S0900
    300, -- gc: level 3, the 200 mg-and-more doses that did more (S0899) half again; rests on S0900
    500, -- gc: level 4, well past every studied effect dose; rests on S0900
}

-- sleep: acute_debtH, the sleep debt in game hours (K.acute, capped at K.acute.DEBT_MAX).
K.view.SLEEP_AT = {
    2, -- gc: level 1, one short night; rests on S0742 (cumulative restriction) and S0736 (the two-process model)
    6, -- gc: level 2, about three restricted nights; rests on S0742
    12, -- gc: level 3, more than a night of total deprivation; rests on S0742
    24, -- gc: level 4, about the 2 nights of total deprivation S0742's 14-night restriction reached
}

-- deficiency and excess: the worst grade less one and the highest rung over the mirror's nut_<key>_g / _x, each
-- capped at the record engine's top rung, 3 (K.nutrients: g 1 replete .. 4 clinical, x 0..3).
K.view.RUNG_MAX = 3 -- the record engine's top rung (NR_Kernel_Nutrients grades and excess ladders)

-- The tooltip's "rich in" and "low" shares of the per-day requirement R a single item gives, and the lines of each.
K.view.RICH_SHARE = 0.25 -- gc: rich at 25 % of R per item (plan ruling 8)
K.view.LOW_SHARE = 0.05 -- gc: low at 5 % of R or less per item, the 5 %-of-a-daily-value "low" convention; no row
K.view.TIP_MAX = 3 -- gc: up to three rich and three low lines (plan ruling 8)

-- string.format patterns by digit count, never %d (the Kahlua %d rule, #0939).
K.view.FORMATS = { "%.1f", "%.2f", "%.3f" }
K.view.FORMATS[0] = "%.0f"

-- A number formatted with digits (0-3, default 0) after the point; "" for anything that is not a number or NaN.
function K.view.fmt(v, digits)
    if type(v) ~= "number" or v ~= v then
        return ""
    end
    local d = digits
    if type(d) ~= "number" then
        d = 0
    end
    d = K.clamp(math.floor(d), 0, 3)
    return string.format(K.view.FORMATS[d], v)
end

-- fmt with a unit after a space; "" when there is no number.
function K.view.unitText(v, digits, unit)
    local text = K.view.fmt(v, digits)
    if text ~= "" and unit ~= nil then
        text = text .. " " .. unit
    end
    return text
end

-- An amount with its digits chosen by size: 0 at 100 and over, 1 at 10 and over, else 2.
function K.view.amount(v, unit)
    local a = math.abs(v)
    local d = 2
    if a >= 100 then
        d = 0
    elseif a >= 10 then
        d = 1
    end
    return K.view.unitText(v, d, unit)
end

-- A visibility level clamped to 1..3 and floored; anything that is not a number reads 1, Symptoms.
function K.view.clampLevel(level)
    if type(level) ~= "number" or level ~= level then
        return 1
    end
    return K.clamp(math.floor(level), 1, 3)
end

-- The visibility level (ruling 3): max(the option, 3 with either Nutritionist trait), clamped 1..3.
function K.view.level(optionLevel, hasTrait)
    local o = K.view.clampLevel(optionLevel)
    if hasTrait == true then
        o = 3
    end
    return o
end

-- The one per-frame test a surface makes: the mirror's arrival counter or the level moved.
function K.view.changed(received, lastReceived, level, lastLevel)
    return received ~= lastReceived or level ~= lastLevel
end

-- The count of ladder thresholds v reaches (0 when v is not a number).
function K.view.rung(v, at)
    local n = 0
    if type(v) ~= "number" then
        return n
    end
    for i = 1, #at do
        if v >= at[i] then
            n = i
        end
    end
    return n
end

-- The six class levels of a mirror m (nil reads all zero). m is a Lua-shaped table (the client's stored copy),
-- so pairs is allowed; the deficiency and excess scans read every nut_<key>_g and nut_<key>_x it carries.
function K.view.classes(m)
    local c = { energy = 0, hydration = 0, deficiency = 0, excess = 0, stimulant = 0, sleep = 0 }
    if m == nil then
        return c
    end
    c.energy = K.view.rung(m.body_energyState, K.view.ENERGY_AT)
    c.hydration = K.view.rung(m.fluids_dehydPct, K.view.HYDRATION_AT)
    c.stimulant = K.view.rung(m.acute_caf, K.view.STIMULANT_AT)
    c.sleep = K.view.rung(m.acute_debtH, K.view.SLEEP_AT)
    for k, v in pairs(m) do
        K.view.scan(c, k, v)
    end
    return c
end

-- One mirror entry into the deficiency and excess classes: a numeric nut_<key>_g raises deficiency to g - 1, a
-- numeric nut_<key>_x raises excess to x, each capped at RUNG_MAX; anything else is skipped.
function K.view.scan(c, k, v)
    if type(v) ~= "number" or type(k) ~= "string" then
        return
    end
    if string.match(k, "^nut_.+_g$") ~= nil then
        c.deficiency = K.max(c.deficiency, K.clamp(v - 1, 0, K.view.RUNG_MAX))
    end
    if string.match(k, "^nut_.+_x$") ~= nil then
        c.excess = K.max(c.excess, K.clamp(v, 0, K.view.RUNG_MAX))
    end
end

-- One row.
function K.view.row(key, label, text, level, isKey)
    local r = {}
    r.key = key
    r.label = label
    r.text = text
    r.level = level
    r.isKey = isKey
    return r
end

-- Append a row to rows and return it.
function K.view.push(rows, key, label, text, level, isKey)
    local r = K.view.row(key, label, text, level, isKey)
    rows[#rows + 1] = r
    return r
end

-- The row model (ruling 2): m the mirror (nil reads empty), level 1..3, order the nutrient keys whose grade rows
-- are listed (nil: none; K.view.gradedOrder gives the graded ones). Every level: the six class rows; Bands and up:
-- the body block (band word, weight, energy word), the hydration word and each graded key's grade word (a key the
-- engine has not graded yet, g < 1, has no row); Numbers: the fat and lean mass, each listed key's pool percentage
-- and excess rung, and the caffeine, alcohol and sleep-debt figures.
function K.view.rows(m, level, order)
    local mm = m
    if mm == nil then
        mm = {}
    end
    local lv = K.view.clampLevel(level)
    local c = K.view.classes(mm)
    local rows = {}
    for i = 1, #K.view.CLASSES do
        local cls = K.view.CLASSES[i]
        local r = K.view.push(rows, cls, "UI_NR_Class_" .. cls, "UI_NR_Class_" .. cls .. "_" .. K.view.fmt(c[cls], 0), 1, true)
        r.cls = cls
        r.n = c[cls]
    end
    if lv < 2 then
        return rows
    end
    local band = mm.body_band
    if type(band) ~= "string" or band == "" then
        band = "none"
    end
    K.view.push(rows, "body_band", "UI_NR_Row_body_band", "UI_NR_Band_" .. band, 2, true)
    K.view.push(rows, "body_weight", "UI_NR_Row_body_weight", K.view.unitText(mm.body_weight, 1, "kg"), 2, false)
    K.view.push(rows, "body_energyState", "UI_NR_Row_body_energyState", "UI_NR_Class_energy_" .. K.view.fmt(c.energy, 0), 2, true)
    if lv >= 3 then
        K.view.push(rows, "body_fm", "UI_NR_Row_body_fm", K.view.unitText(mm.body_fm, 1, "kg"), 3, false)
        K.view.push(rows, "body_lm", "UI_NR_Row_body_lm", K.view.unitText(mm.body_lm, 1, "kg"), 3, false)
    end
    K.view.push(rows, "fluids_dehydPct", "UI_NR_Row_fluids_dehydPct", "UI_NR_Class_hydration_" .. K.view.fmt(c.hydration, 0), 2, true)
    if order ~= nil then
        for i = 1, #order do
            K.view.nutrientRows(rows, mm, order[i], lv)
        end
    end
    if lv >= 3 then
        K.view.push(rows, "acute_caf", "UI_NR_Row_acute_caf", K.view.unitText(mm.acute_caf, 0, "mg"), 3, false)
        K.view.push(rows, "acute_bac", "UI_NR_Row_acute_bac", K.view.unitText(mm.acute_bac, 3, "%"), 3, false)
        K.view.push(rows, "acute_debtH", "UI_NR_Row_acute_debtH", K.view.unitText(mm.acute_debtH, 1, "h"), 3, false)
    end
    return rows
end

-- One nutrient's rows: its grade word at Bands and up, its pool percentage and excess rung at Numbers; none while
-- the key is ungraded in the mirror (g absent or below 1).
function K.view.nutrientRows(rows, m, key, lv)
    local g = m["nut_" .. key .. "_g"]
    if type(g) ~= "number" or g < 1 then
        return
    end
    local grade = K.clamp(g, 1, K.view.RUNG_MAX + 1)
    K.view.push(rows, "nut_" .. key .. "_g", "UI_NR_Row_" .. key, "UI_NR_Grade_" .. K.view.fmt(grade, 0), 2, true)
    if lv < 3 then
        return
    end
    local p = m["nut_" .. key .. "_p"]
    if type(p) == "number" then
        p = p * 100
    end
    K.view.push(rows, "nut_" .. key .. "_p", "UI_NR_Row_" .. key .. "_p", K.view.unitText(p, 1, "%"), 3, false)
    K.view.push(rows, "nut_" .. key .. "_x", "UI_NR_Row_" .. key .. "_x", K.view.fmt(m["nut_" .. key .. "_x"], 0), 3, false)
end

-- The ORDER keys of a records table ({ ORDER, REC }, NR.data.records) whose kind is graded (not in
-- K.nutrients.UNGRADED): the order a panel lists grade rows for. nil reads none.
function K.view.gradedOrder(records)
    local out = {}
    if records == nil then
        return out
    end
    for i = 1, #records.ORDER do
        local key = records.ORDER[i]
        local rec = records.REC[key]
        if rec ~= nil and K.nutrients.UNGRADED[rec.kind] == nil then
            out[#out + 1] = key
        end
    end
    return out
end

-- The per-key daily requirement map the tooltip's rich and low test reads: R[sex] (1 male, 2 female) of every
-- record with a numeric R and no scale (a per-MJ, per-kg or per-protein R is not a daily amount) whose unit is
-- the vector's own for that key (units is NR.data.UNITS). nil records or units read an empty map.
function K.view.requirements(records, sex, units)
    local out = {}
    if records == nil or units == nil then
        return out
    end
    for i = 1, #records.ORDER do
        local key = records.ORDER[i]
        local rec = records.REC[key]
        if rec ~= nil and rec.scale == nil and type(rec.R) == "table" and type(rec.R[sex]) == "number" and rec.unit == units[key] then
            out[key] = rec.R[sex]
        end
    end
    return out
end

-- The share of the daily requirement R[key] one item's vector gives (a missing or non-number value reads 0), or
-- nil when the key has no positive requirement.
function K.view.share(vector, R, key)
    local r = R[key]
    if type(r) ~= "number" or r <= 0 then
        return nil
    end
    local v = vector[key]
    if type(v) ~= "number" then
        v = 0
    end
    return v / r
end

-- Whether share f beats the best so far: rich ranks the highest share at RICH_SHARE and over, low the lowest at
-- LOW_SHARE and under; a tie keeps the earlier key.
function K.view.better(f, bestF, best, rich)
    if rich then
        return f >= K.view.RICH_SHARE and (best == nil or f > bestF)
    end
    return f <= K.view.LOW_SHARE and (best == nil or f < bestF)
end

-- The best key of keys not yet picked, or nil.
function K.view.pickOne(vector, R, keys, picked, rich)
    local best = nil
    local bestF = 0
    for i = 1, #keys do
        local k = keys[i]
        local f = K.view.share(vector, R, k)
        if f ~= nil and picked[k] == nil and K.view.better(f, bestF, best, rich) then
            best = k
            bestF = f
        end
    end
    return best
end

-- Up to TIP_MAX rich (or low) lines appended to out, text the word key.
function K.view.pickLines(out, vector, R, keys, picked, rich, word)
    for n = 1, K.view.TIP_MAX do
        local k = K.view.pickOne(vector, R, keys, picked, rich)
        if k == nil then
            return
        end
        picked[k] = true
        K.view.push(out, k, "UI_NR_Row_" .. k, word, 2, true)
    end
end

-- The tooltip lines of one food (ruling 8): vector and source from K.vector.resolve, level 1..3, keys the keys
-- considered (nil: K.vector.KEYS), data { R = K.view.requirements(...), UNITS = NR.data.UNITS } or nil. Symptoms:
-- the source line alone; Bands: the four macros as amounts, then up to three rich-in and three low keys; Numbers:
-- every non-zero key of keys with its amount and unit. A nil vector (the source "missing") is the source line alone.
function K.view.tooltip(vector, source, level, keys, data)
    local out = {}
    local src = source
    if type(src) ~= "string" then
        src = "missing"
    end
    K.view.push(out, "source", "UI_NR_Tip_Source_" .. src, "", 1, false)
    local lv = K.view.clampLevel(level)
    if vector == nil or lv < 2 then
        return out
    end
    local ks = keys
    if ks == nil then
        ks = K.vector.KEYS
    end
    local units = {}
    local R = {}
    if data ~= nil then
        units = data.UNITS or units
        R = data.R or R
    end
    if lv >= 3 then
        for i = 1, #ks do
            local k = ks[i]
            local v = vector[k]
            if type(v) == "number" and v ~= 0 then
                K.view.push(out, k, "UI_NR_Row_" .. k, K.view.amount(v, units[k]), 3, false)
            end
        end
        return out
    end
    for i = 1, #K.vector.MACROS do
        local k = K.vector.MACROS[i]
        K.view.push(out, k, "UI_NR_Row_" .. k, K.view.amount(vector[k] or 0, units[k]), 2, false)
    end
    local picked = {}
    K.view.pickLines(out, vector, R, ks, picked, true, "UI_NR_Tip_Rich")
    K.view.pickLines(out, vector, R, ks, picked, false, "UI_NR_Tip_Low")
    return out
end

-- The moodle value map (Plan 7 Task 8, rulings 10 and T8-1): a class level onto MoodleFramework's 0..1 value, which
-- the framework reads against eight thresholds (MF_ISMoodle.lua getLevel :127). A symptom is a BAD moodle, so the
-- map runs down the framework's bad side: neutral is the framework's own stored default, 0.5 (MF_ISMoodle.lua :75),
-- where the moodle leaves the UI manager; each class's top level reaches 0.0, so a four-level class steps 0.125 a
-- level down and deficiency and excess (top rung 3) step one sixth.
K.view.MOODLE_NEUTRAL = 0.5 -- gc: the framework's default stored value (MF_ISMoodle.lua:75), neutral under its thresholds
K.view.MOODLE_LEVELS = 4 -- the class ladders' top level (ENERGY_AT, HYDRATION_AT, STIMULANT_AT, SLEEP_AT)

-- A class's top level: RUNG_MAX for deficiency and excess, else MOODLE_LEVELS.
function K.view.moodleTop(cls)
    if cls == "deficiency" or cls == "excess" then
        return K.view.RUNG_MAX
    end
    return K.view.MOODLE_LEVELS
end

-- The value a class level sets (floored, clamped 0..top; anything that is not a number reads 0): neutral 0.5 at 0
-- and 0.0 at the class's top, linear between (four-level 0.375 / 0.25 / 0.125 / 0.0; deficiency and excess 0.33333 /
-- 0.16667 / 0.0), clamped 0..1 by the mod because the framework never clamps (#2535).
function K.view.moodleValue(level, cls)
    local top = K.view.moodleTop(cls)
    local n = level
    if type(n) ~= "number" or n ~= n then
        n = 0
    end
    n = K.clamp(math.floor(n), 0, top)
    return K.clamp(K.view.MOODLE_NEUTRAL - K.view.MOODLE_NEUTRAL * n / top, 0, 1)
end

-- The framework's bad-side threshold k (1..4, bad1 the nearest to neutral) for a class: midway between the values of
-- levels k - 1 and k, so the framework's level equals the class level with no float tie (four-level 0.4375 / 0.3125 /
-- 0.1875 / 0.0625; deficiency and excess 0.41667 / 0.25 / 0.08333 and nil); nil above the class's top (the framework
-- then reads that threshold as unreachable, MF_ISMoodle.lua setThresholds :161-164).
function K.view.moodleThreshold(k, cls)
    local top = K.view.moodleTop(cls)
    if k > top then
        return nil
    end
    return K.view.MOODLE_NEUTRAL - K.view.MOODLE_NEUTRAL * (k - 0.5) / top
end
