-- NR_Kernel_View.lua -- the interface's row model: the client's stored
-- mirror (the flat scalar table of NR_Kernel_Mirror.lua) in, at one of three visibility levels, and an array of
-- rows out; the four symptom classes the moodles show; the tooltip lines of one food's resolved vector
-- (K.vector.resolve). Pure: no engine global, no getText -- every label is a translation KEY and every text is
-- a KEY (isKey true: the class, band and grade words) or a formatted string, resolved by the client files.
-- One statement per line (the coverage gate is line-granular). This file sorts after NR_Kernel.lua,
-- NR_Kernel_Fluids.lua and NR_Kernel_Nutrients.lua; every K.* reference is at call time.
-- A row is { key, label, text, level, isKey } plus cls and n (the class level 0-4) on a class row; level is the
-- visibility level the row belongs to (1 Symptoms, 2 Bands, 3 Numbers). Labels: a class row UI_NR_Class_<cls>; a
-- grade row UI_NR_Row_<nutrient>; every other row UI_NR_Row_<mirror key without the nut_ prefix> (vitC_p,
-- vitC_x, body_weight, acute_caf ...); a tooltip line UI_NR_Tip_Source_<source> or UI_NR_Row_<vector key>.
-- Texts: UI_NR_Class_<cls>_<0-4> (deficiency and excess stop at 3), UI_NR_Band_<band or none>, UI_NR_Grade_<1-4>, UI_NR_Tip_Rich, UI_NR_Tip_Low,
-- UI_NR_Drain_<state name> (a drain row), UI_NR_Trend_<word> (the weight trend), UI_NR_Tip_Fills* (the tooltip's fill line).
local K = NutritionRevamp.kernel
K.view = {}

-- The four symptom classes, closed, in display order. The Energy and Hydration classes are removed (Plan 15 Task 9;
-- spec section 4, items 1 and 10e): vanilla's calibrated hunger moodle, reaching Starving, and its thirst moodle,
-- reaching Parched, are the signals; the internal energy state stays (record.body.energyState), and the panel shows the
-- drain state, the weight trend and the dehydration per cent instead.
K.view.CLASSES = { "deficiency", "excess", "stimulant", "sleep" }

-- Each class ladder is the four ascending lower bounds of class levels 1-4; below the first the class reads 0.
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

-- A number formatted with digits (0-3, default 0) after the point; "" for anything that is not a number, NaN or an infinity.
function K.view.fmt(v, digits)
    if type(v) ~= "number" or v ~= v then
        return ""
    end
    if v == math.huge or v == -math.huge then
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

-- The visibility level: max(the option, 3 with either Nutritionist trait), clamped 1..3.
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

-- The four class levels of a mirror m (nil reads all zero). m is a Lua-shaped table (the client's stored copy), so
-- pairs is allowed; the excess scan reads every nut_<key>_x it carries, the deficiency scan only the nut_<key>_g of a key
-- in def, the set of nutrients whose grade drives an effect (K.view.deficiencyKeys; nil reads none).
function K.view.classes(m, def)
    local c = { deficiency = 0, excess = 0, stimulant = 0, sleep = 0 }
    if m == nil then
        return c
    end
    c.stimulant = K.view.rung(m.acute_caf, K.view.STIMULANT_AT)
    c.sleep = K.view.rung(m.acute_debtH, K.view.SLEEP_AT)
    for k, v in pairs(m) do
        K.view.scan(c, k, v, def)
    end
    return c
end

-- The live state that marks a push, as one integer (Plan 15 Task 9): the sleep rung (units), the stimulant rung (tens),
-- the Overfull level (hundreds; massG, the mirror's stomachMass), the whole dehydration per cent (thousands, 0-9:
-- K.view.dehydDigit, the panel's figure), the weight trend word (ten-thousands, K.view.trendIndex 0-2) and the active
-- drain set (from the hundred-thousands, K.drain's mask 0-127), so a new drain line, trend word or per cent reaches
-- the panel at the next slow minute. Deficiency and excess move with the nutrient epoch, which already marks a push.
-- nil reads 0 (the trend 1, steady).
function K.view.pushSignature(dehydPct, caf, debtH, massG, drainMask, trend)
    local s = K.view.rung(caf or 0, K.view.STIMULANT_AT)
    local sl = K.view.rung(debtH or 0, K.view.SLEEP_AT)
    local o = K.view.fullnessLevel(massG)
    local d = K.view.digit(dehydPct, 9)
    local t = K.view.digit(trend or 1, 2)
    return K.view.digit(drainMask, 127) * 100000 + t * 10000 + d * 1000 + o * 100 + s * 10 + sl
end

-- A whole number from v, floored and clamped 0..hi; anything that is not a finite number reads 0.
function K.view.digit(v, hi)
    if not K.finite(v) then
        return 0
    end
    return K.clamp(math.floor(v), 0, hi)
end

-- A player's push phase inside the gap (rule #3498): a rolling hash of the username modulo the gap,
-- so players first seen together make their first push in different frames (#3456); it spreads only that first gap.
function K.view.pushOffset(username, gapMs)
    return K.nameHash(username) % gapMs
end

-- One mirror entry into the deficiency and excess classes: a numeric nut_<key>_g of a key in def (nil reads none)
-- raises deficiency to g - 1, a numeric nut_<key>_x raises excess to x, each capped at RUNG_MAX; anything else is
-- skipped.
function K.view.scan(c, k, v, def)
    if type(v) ~= "number" or type(k) ~= "string" then
        return
    end
    local key = string.match(k, "^nut_(.+)_g$")
    if key ~= nil and def ~= nil and def[key] == true then
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

-- The row model: m the mirror (nil reads empty), level 1..3, order the nutrient keys whose grade rows
-- are listed (nil: none; K.view.gradedOrder gives the graded ones), fat the client's body-fat state { female, last }
-- (nil reads a man with no word held; K.view.fatRow), ungraded the keys with no grade whose excess still raises the
-- Excess class (nil: none; K.view.ungradedOrder), def the deficiency key set (K.view.classes). Every level: the four
-- class rows, then one line per active drain state (K.view.drainRows); Bands and up: the body block (band word, weight,
-- weight-trend word, body-fat word, Strength), the dehydration per cent above DEHYD_SHOW, each graded key's grade word
-- (a key the engine has not graded yet, g < 1, has no grade row: the panel lists every graded key, whether or not its
-- grade drives an effect) and every listed key's excess word while its rung is above 0; Numbers: the fat and lean mass
-- and the trend in kg a day, each graded key's pool percentage and excess rung, an ungraded key's rung while above 0,
-- and the caffeine, alcohol and sleep-debt figures.
function K.view.rows(m, level, order, fat, ungraded, def)
    local mm = m
    if mm == nil then
        mm = {}
    end
    local lv = K.view.clampLevel(level)
    local c = K.view.classes(mm, def)
    local rows = {}
    for i = 1, #K.view.CLASSES do
        local cls = K.view.CLASSES[i]
        local r = K.view.push(rows, cls, "UI_NR_Class_" .. cls, "UI_NR_Class_" .. cls .. "_" .. K.view.fmt(c[cls], 0), 1, true)
        r.cls = cls
        r.n = c[cls]
    end
    K.view.drainRows(rows, mm.drain_mask)
    if lv < 2 then
        return rows
    end
    K.view.push(rows, "body_band", "UI_NR_Row_body_band", K.view.bandKey("UI_NR_Band_", mm.body_band), 2, true)
    K.view.push(rows, "body_weight", "UI_NR_Row_body_weight", K.view.unitText(mm.body_weight, 1, "kg"), 2, false)
    K.view.trendRow(rows, mm)
    K.view.fatRow(rows, mm, fat)
    K.view.levelRow(rows, mm)
    if lv >= 3 then
        K.view.push(rows, "body_fm", "UI_NR_Row_body_fm", K.view.unitText(mm.body_fm, 1, "kg"), 3, false)
        K.view.push(rows, "body_lm", "UI_NR_Row_body_lm", K.view.unitText(mm.body_lm, 1, "kg"), 3, false)
        K.view.push(rows, "body_trendKg", "UI_NR_Row_body_trendKg", K.view.unitText(mm.body_trend, 2, "kg/day"), 3, false)
    end
    K.view.dehydRow(rows, mm.fluids_dehydPct)
    if order ~= nil then
        for i = 1, #order do
            K.view.nutrientRows(rows, mm, order[i], lv)
        end
    end
    if ungraded ~= nil then
        for i = 1, #ungraded do
            K.view.excessRow(rows, mm, ungraded[i], lv, false)
        end
    end
    if lv >= 3 then
        K.view.push(rows, "acute_caf", "UI_NR_Row_acute_caf", K.view.unitText(mm.acute_caf, 0, "mg"), 3, false)
        K.view.push(rows, "acute_bac", "UI_NR_Row_acute_bac", K.view.unitText(mm.acute_bac, 3, "%"), 3, false)
        K.view.push(rows, "acute_debtH", "UI_NR_Row_acute_debtH", K.view.unitText(mm.acute_debtH, 1, "h"), 3, false)
    end
    return rows
end

-- One graded nutrient's rows: its grade word at Bands and up, its pool percentage at Numbers, then its excess row
-- (K.view.excessRow, the rung always at Numbers); while the mirror has not graded the key (g absent or below 1), the
-- excess row alone, and only while its rung is above 0.
function K.view.nutrientRows(rows, m, key, lv)
    local g = m["nut_" .. key .. "_g"]
    if type(g) ~= "number" or g < 1 then
        K.view.excessRow(rows, m, key, lv, false)
        return
    end
    local grade = K.clamp(g, 1, K.view.RUNG_MAX + 1)
    K.view.push(rows, "nut_" .. key .. "_g", "UI_NR_Row_" .. key, "UI_NR_Grade_" .. K.view.fmt(grade, 0), 2, true)
    if lv >= 3 then
        local p = m["nut_" .. key .. "_p"]
        if type(p) == "number" then
            p = p * 100
        end
        K.view.push(rows, "nut_" .. key .. "_p", "UI_NR_Row_" .. key .. "_p", K.view.unitText(p, 1, "%"), 3, false)
    end
    K.view.excessRow(rows, m, key, lv, true)
end

-- One nutrient's excess row, labelled UI_NR_Row_<key>_x: at Numbers its rung as a figure (always, or only while
-- above 0); at Bands, while the rung is above 0, the Excess class word of that rung (capped at RUNG_MAX), amber
-- like a class row. None at Symptoms. A rung that is not a number above 0 (NaN included) is not above 0.
function K.view.excessRow(rows, m, key, lv, always)
    local x = m["nut_" .. key .. "_x"]
    local raised = type(x) == "number" and x > 0
    if lv >= 3 and (always or raised) then
        K.view.push(rows, "nut_" .. key .. "_x", "UI_NR_Row_" .. key .. "_x", K.view.fmt(x, 0), 3, false)
    elseif lv == 2 and raised then
        local n = K.clamp(x, 1, K.view.RUNG_MAX)
        local r = K.view.push(rows, "nut_" .. key .. "_x", "UI_NR_Row_" .. key .. "_x", "UI_NR_Class_excess_" .. K.view.fmt(n, 0), 2, true)
        r.cls = "excess"
        r.n = n
    end
end

-- --- the panel's signal lines (Plan 15 Task 9; spec section 4) -------------------------------------------------------
-- The drain lines: one row per active drain state, in code order, its label UI_NR_Row_drain and its text the state's
-- plain words, UI_NR_Drain_<name> (K.drain.states[code].name: "weakened by starvation", "suffering from dehydration",
-- "scurvy" ...), amber like a raised class. mask is the mirror's drain_mask (K.drain's set of active codes, code c the
-- bit 2^(c - 1)); a mask that is not a finite number reads none. Pushed at level 1: the drain is the body's damage
-- signal the removed Energy moodle carried (decisions item 1), so every visibility level shows it.
function K.view.drainRows(rows, mask)
    if not K.finite(mask) or mask <= 0 then
        return
    end
    -- K.drain.states is a kernel-built Lua array, so # is its length
    for code = 1, #K.drain.states do
        if K.view.hasBit(mask, code) then
            local name = K.drain.states[code].name
            local r = K.view.push(rows, "drain_" .. name, "UI_NR_Row_drain", "UI_NR_Drain_" .. name, 1, true)
            r.cls = "drain"
            r.n = 1
        end
    end
end

-- Whether drain code c's bit, 2^(c - 1), is set in mask (Lua 5.1 has no bit operators).
function K.view.hasBit(mask, c)
    return math.floor(mask / 2 ^ (c - 1)) % 2 == 1
end

-- The weight trend: the server's 7-day body-mass slope (the mirror's body_trend, K.body.trend over the closed-day ring
-- body.mass7, kg a day) as a word at Bands, "losing", "steady" or "gaining", or No data while the mirror carries no body.
-- The word reads K.body.flags, the direction flags this mod sets vanilla's weight arrows from (NR_Server_Weight, ruling
-- 17), so the panel and the character screen's arrows never disagree (Plan 15 Task 9 fix 1, review M2): one threshold.
K.view.TREND_WORDS = { "steady", "gaining" }
K.view.TREND_WORDS[0] = "losing"

-- The trend word's index of a slope in kg a day: 0 losing (K.body.flags' decreasing), 2 gaining (its increasing), else
-- 1 steady; a slope that is not a finite number reads 1.
function K.view.trendIndex(kgPerDay)
    if not K.finite(kgPerDay) then
        return 1
    end
    local inc, _, dec = K.body.flags(kgPerDay)
    if dec then
        return 0
    end
    if inc then
        return 2
    end
    return 1
end

-- The trend row at Bands: its word key UI_NR_Trend_<word>, or No data with no body (a body_weight that is not a positive
-- number or a body_trend that is not a finite number).
function K.view.trendRow(rows, m)
    local text = K.view.NO_DATA
    if K.finite(m.body_trend) and K.finite(m.body_weight) and m.body_weight > 0 then
        text = "UI_NR_Trend_" .. K.view.TREND_WORDS[K.view.trendIndex(m.body_trend)]
    end
    K.view.push(rows, "body_trend", "UI_NR_Row_body_trend", text, 2, true)
end

-- The dehydration row at Bands: the body-water deficit in per cent of body mass to one decimal, only above DEHYD_SHOW
-- (a figure that is not a finite number shows nothing). Vanilla's thirst moodle, reaching Parched, is the signal
-- (decisions item 10e); this row is its figure.
K.view.DEHYD_SHOW = 1 -- per cent: shown only above it (Plan 15 Task 9 amendments section 5); game choice (spec section 4's dehydration line; spec section 10: display), under the 1.5 % the effects table's first dehydration band starts at (S0098)
function K.view.dehydRow(rows, pct)
    if not K.finite(pct) or pct <= K.view.DEHYD_SHOW then
        return
    end
    K.view.push(rows, "fluids_dehydPct", "UI_NR_Row_fluids_dehydPct", K.view.unitText(pct, 1, "%"), 2, false)
end

-- --- the Deficiency moodle's nutrients (Plan 15 Task 9; spec section 4, item 8) ------------------------------------
-- The nutrients whose grade drives an effect: the Deficiency moodle and its class row read these alone (the panel's
-- grade rows still list every graded nutrient). Built from the tables at load, never a hand list (the test keeps the
-- set in step with them): every effects row on a nutrient's grade (on = "grade", whose src is the nutrient key), a gated
-- row only while its gate names a table flag that is true (fix 1, review L2: the composer folds a gated row only when its
-- gate holds, K.effects.active, so a gate the table does not set true, VITD_EFFECTS or a sandbox gate, never counts);
-- the members of the two grade aggregates the rows
-- read as flags, bgroupMax (K.effects.BGROUP) and anaemia (K.nutrients.ANAEMIA, with vitamin B12 through BGROUP); and
-- the nutrients of the drain engine's clinical onsets (K.drain.NUTRIENT). effects is NR.data.effects ({ ROWS, ... });
-- nil reads the onsets alone. Returns a set { [key] = true }.
function K.view.deficiencyKeys(effects)
    local out = {}
    for _, key in pairs(K.drain.NUTRIENT) do
        out[key] = true
    end
    if effects == nil or type(effects.ROWS) ~= "table" then
        return out
    end
    -- ROWS is the data file's Lua array, so # is its length
    for i = 1, #effects.ROWS do
        K.view.deficiencyRow(out, effects, effects.ROWS[i])
    end
    return out
end

-- One effects row into the deficiency set (the loop body, kept apart so the line-granular coverage gate sees each
-- outcome): a gated row whose table flag is not true adds nothing; a grade row adds its src; a flag row on a grade
-- aggregate adds every member.
function K.view.deficiencyRow(out, effects, row)
    if row.gated ~= nil and effects[row.gated] ~= true then
        return
    end
    if row.on == "grade" then
        out[row.src] = true
        return
    end
    local members = K.view.aggregateOf(row)
    if members == nil then
        return
    end
    -- an aggregate's members are a kernel-built Lua array, so # is its length
    for i = 1, #members do
        out[members[i]] = true
    end
end

-- The members of the grade aggregate a flag row reads (bgroupMax: K.effects.BGROUP; anaemia: K.nutrients.ANAEMIA), or
-- nil for any other row.
function K.view.aggregateOf(row)
    if row.on ~= "flag" then
        return nil
    end
    if row.src == "bgroupMax" then
        return K.effects.BGROUP
    end
    if row.src == "anaemia" then
        return K.nutrients.ANAEMIA
    end
    return nil
end

-- The ORDER keys of a records table ({ ORDER, REC }, NR.data.records) whose kind is graded (not in
-- K.nutrients.UNGRADED): the order a panel lists grade rows for. nil reads none.
function K.view.gradedOrder(records)
    return K.view.kindOrder(records, true)
end

-- The ORDER keys whose kind is ungraded (in K.nutrients.UNGRADED): no grade row, but an excess that raises the Excess
-- class, so the panel names it (K.view.excessRow). nil reads none.
function K.view.ungradedOrder(records)
    return K.view.kindOrder(records, false)
end

-- The ORDER keys of records whose kind is graded (graded true) or ungraded (false), in order.
function K.view.kindOrder(records, graded)
    local out = {}
    if records == nil then
        return out
    end
    for i = 1, #records.ORDER do
        local key = records.ORDER[i]
        local rec = records.REC[key]
        if rec ~= nil and (K.nutrients.UNGRADED[rec.kind] == nil) == graded then
            out[#out + 1] = key
        end
    end
    return out
end

-- The vector keys whose record sits under another key (#3240): the vector carries vitamin A as
-- retinol, the record engine as vitA (NR_Data_Records.lua: REC.vitA.key = "retinol"). The test pins this table to
-- every record whose own key field differs from its REC key; no other record differs.
K.view.RECORD_KEY = { retinol = "vitA" }

-- The body mass a per-kg requirement is read at for the band. gc: a game choice, the 70 kg
-- reference adult of the DRI tables; the band ranks one item against a fixed daily amount, never the
-- character's own mass (the client holds no body).
K.view.REF_KG = 70

-- The daily requirement of one record for a sex, or nil when it has none: R[sex] for an unscaled record; the
-- floor R[sex] for a per-protein maximum (max(R, Rscale x protein) is never below it); R[sex] x REF_KG for a
-- per-kg record; the record's RDA Rmin[sex] for a per-MJ record (its R is per MJ expended, not a daily amount;
-- the engine never reads Rmin, the band does); nil for any other scale or a missing number.
function K.view.dailyR(rec, sex)
    if type(rec.R) ~= "table" or type(rec.R[sex]) ~= "number" then
        return nil
    end
    local r = rec.R[sex]
    local scale = rec.scale
    if scale == nil or scale == "perProteinGMax" then
        return r
    end
    if scale == "perKg" then
        return r * K.view.REF_KG
    end
    if scale == "perMJ" and type(rec.Rmin) == "table" and type(rec.Rmin[sex]) == "number" then
        return rec.Rmin[sex]
    end
    return nil
end

-- The per-key daily requirement map the tooltip's rich and low test reads, keyed by the VECTOR key (units is
-- NR.data.UNITS, whose keys are the vector's): for each unit key, the record under it (through RECORD_KEY) when
-- its unit is the vector's own, at K.view.dailyR for the sex (1 male, 2 female). nil records or units read an
-- empty map.
function K.view.requirements(records, sex, units)
    local out = {}
    if records == nil or units == nil then
        return out
    end
    for key, unit in pairs(units) do
        K.view.requirementOf(out, records, sex, key, unit)
    end
    return out
end

-- One unit key of the requirement map: the record under the key (through RECORD_KEY) when its unit is unit, at
-- K.view.dailyR for the sex, written into out.
function K.view.requirementOf(out, records, sex, key, unit)
    local recKey = K.view.RECORD_KEY[key]
    if recKey == nil then
        recKey = key
    end
    local rec = records.REC[recKey]
    if rec ~= nil and rec.unit == unit then
        out[key] = K.view.dailyR(rec, sex)
    end
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

-- The tooltip lines of one food: vector and source from K.vector.resolve, level 1..3, keys the keys
-- considered (nil: K.vector.KEYS), data { R = K.view.requirements(...), UNITS = NR.data.UNITS, fillH = the item's
-- fill hours (NR.data.fills.get) or nil } or nil. Every level: the fill line first when data.fillH is a number and the
-- vector carries its calories (K.view.fillRow; it stands in for vanilla's hunger line, which the client hides), then
-- the source line; Bands: the four macros as amounts, then up to three rich-in and three low keys; Numbers: every
-- non-zero key of keys with its amount and unit. A nil vector (the source "missing") is the source line alone.
function K.view.tooltip(vector, source, level, keys, data)
    local out = {}
    local src = source
    if type(src) ~= "string" then
        src = "missing"
    end
    if vector ~= nil and data ~= nil then
        K.view.fillRow(out, data.fillH, vector.calories)
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

-- The fill line (Plan 15 Task 9; decisions item 4): "A whole one fills you for about N h, K kcal" in place of vanilla's hunger
-- line, N the hours a precomputed replay of the item alone holds h_model under Peckish (tools/food_fills.py, the
-- generated NR_Data_Fills.lua; never a per-frame or per-hover simulation), shown to the nearest half hour; under
-- FILL_MIN_H "... under half an hour", at FILL_CAP_H or more "... more than FILL_CAP_H h". Per whole item (fix 1, L3). The row's
-- sep is the separator the client joins its label and text with. Nothing for an hours or a kcal that is not a finite
-- number.
K.view.FILL_MIN_H = 0.5 -- game choice (spec section 4's tooltip line, decisions item 4; spec section 10: display): the shown half-hour step; under it the item reads under half an hour
K.view.FILL_CAP_H = 24 -- the replay's horizon in game hours (tools/food_fills.py CAP_H), no row needed

function K.view.fillRow(out, hours, kcal)
    if not K.finite(hours) or not K.finite(kcal) then
        return
    end
    local cal = K.view.fmt(kcal, 0) .. " kcal"
    local r = nil
    if hours < K.view.FILL_MIN_H then
        r = K.view.push(out, "fill", "UI_NR_Tip_FillsUnder", cal, 1, false)
        r.sep = ", "
        return
    end
    local label = "UI_NR_Tip_Fills"
    local h = math.floor(hours / K.view.FILL_MIN_H + 0.5) * K.view.FILL_MIN_H
    if hours >= K.view.FILL_CAP_H then
        label = "UI_NR_Tip_FillsOver"
        h = K.view.FILL_CAP_H
    end
    local digits = 1
    if h == math.floor(h) then
        digits = 0
    end
    r = K.view.push(out, "fill", label, K.view.fmt(h, digits) .. " h, " .. cal, 1, false)
    r.sep = " "
end

-- The moodle value map: a class level onto MoodleFramework's 0..1 value, which
-- the framework reads against eight thresholds (MF_ISMoodle.lua getLevel :127). A symptom is a BAD moodle, so the
-- map runs down the framework's bad side: neutral is the framework's own stored default, 0.5 (MF_ISMoodle.lua :75),
-- where the moodle leaves the UI manager; each class's top level reaches 0.0, so a four-level class steps 0.125 a
-- level down and deficiency and excess (top rung 3) step one sixth.
K.view.MOODLE_NEUTRAL = 0.5 -- gc: the framework's default stored value (MF_ISMoodle.lua:75), neutral under its thresholds
K.view.MOODLE_LEVELS = 4 -- the class ladders' top level (STIMULANT_AT, SLEEP_AT, and Overfull's four levels)

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

-- The soft cap shown as the mod's own Overfull moodle, a fifth moodle class beside
-- the four (the panel's class rows stay the four of K.view.CLASSES). Its level reads the stomach's whole mass, both
-- lanes (the mirror's stomachMass), through K.satiety.discomfort over the comfortable maximum K.stomach.CAPACITY_MAX_G
-- (730 g) and the full scale K.stomach.CAPACITY_HARD_G (1100 g), 0-100; never the physical fill, which clamps at 1 at 730 g, nor the satiety F.
-- At level 4 the server refuses eating through vanilla's food timer (K.view.foodTimer, Plan 15 Task 8).
K.view.OVERFULL_AT = {
    100 / 3, -- gc: level 2 from a third of the way to the full scale (about 853 g); a game choice on ruling 11c-8's inferences, S1250 and S1253
    200 / 3, -- gc: level 3 from two thirds (about 977 g); a game choice on S1250 and S1253
    100, -- gc: level 4 at the full scale, 1100 g, S1253's maximal discomfort (a labelled inference)
}

-- The Overfull level of a stomach mass in grams: 0 at or under 730 g (no discomfort), 1 above it, 2 from a third of
-- the scale, 3 from two thirds, 4 at 1100 g and over; a non-number, NaN or +infinity reads 0 (a negative mass reads
-- no discomfort, so 0).
function K.view.fullnessLevel(massG)
    if type(massG) ~= "number" or massG ~= massG or massG == math.huge then
        return 0
    end
    local d = K.satiety.discomfort(massG, K.stomach.CAPACITY_MAX_G, K.stomach.CAPACITY_HARD_G)
    if d <= 0 then
        return 0
    end
    return 1 + K.view.rung(d, K.view.OVERFULL_AT)
end

-- The Overfull level of a record's stomach (Plan 15 Task 8): K.view.fullnessLevel over the mirror's rounded stomachMass
-- (K.mirror.stomachMass), the very number the client's Overfull moodle reads, so the server's refusal and Overfull
-- effects change level with the moodle the player sees. A record with no stomach, or a solid buffer with a mass key
-- that is not a number (malformed: Kinetics heals it on its own minute), reads 0, so neither the writer nor the effects
-- step raises on it.
K.view.MASS_KEYS = { "water", "proteins", "carbs", "lipids", "fibre" } -- K.stomach.massOf's keys, no row needed
function K.view.overfullOf(record)
    local s = record.stomach
    if s == nil or type(s.buffer) ~= "table" then
        return 0
    end
    -- MASS_KEYS is this file's Lua array, so # is its length
    for i = 1, #K.view.MASS_KEYS do
        if type(s.buffer[K.view.MASS_KEYS[i]]) ~= "number" then
            return 0
        end
    end
    return K.view.fullnessLevel(K.mirror.stomachMass(record))
end

-- --- the food-timer bridge (Plan 15 Task 8; spec sections 2.3 and 2.4; jar-checks Check 1) ---------
-- The mod owns vanilla's health-from-food timer, which alone drives the FOOD_EATEN moodle (Well Fed) against 0, 1600,
-- 3200 and 4800 (#0511) and every vanilla eat and drink refusal at its level 3 (jar-checks Check 1c): the server writes
-- it each minute from the mod's own state and the client's copy follows in the 1 Hz stats packet (#3896). Vanilla
-- drains it by one unit per multiplier unit, 2 x dayMin a game minute (180 at the 90-minute day; #2385, #2922), so each
-- written value is sized from the day length (K.view.timerValues) to keep its band until the next write.
K.view.TIMER_WELL_FED = 1000 -- game choice (spec section 10: the Well Fed mapping): FOOD_EATEN level 1 (over 0, #0511) at the 90-minute day, the floor of K.view.timerValues
K.view.TIMER_WELL_FED_2 = 2800 -- game choice (spec section 10: the Well Fed mapping): level 2 (over 1600, #0511) at the 90-minute day, the floor of K.view.timerValues
K.view.TIMER_FULL = 4400 -- game choice (spec section 2.3): level 3 (over 3200, #0511), vanilla's refusal, at the 90-minute day, the floor of K.view.timerValues; not 3300, which the drain takes under 3200 in 34 game seconds
K.view.HOLD_MIN = 2 -- game choice (spec section 10: the Well Fed mapping): the game minutes a written value must survive, S0-1's quantized 1.6 rounded up
-- The meal pool M (weighted kcal, K.satiety) at or above which the character reads sated after a satisfying meal.
K.view.WELL_FED_M = 435 -- game choice (spec section 10: the Well Fed mapping): a 667 kcal mixed meal (15/50/35 % of energy, 788.5 weighted kcal) clears to it in 0.50 game hours at MEAL_HALF_LIFE_H, inside vanilla's Well Fed after a whole can (3120 units, 17 game minutes raw, 35 heated, at the 90-minute day; #0054, #0530); a 400 kcal meal 0.07 h; a 200 kcal snack never
K.view.WELL_FED_2_AT = 2 -- game choice (spec section 10: the Well Fed mapping): Well Fed level 2 from Overfull 2, a large meal
K.view.REFUSE_AT = 4 -- spec section 2.3: Overfull 4, the 1100 g hard capacity, refuses eating

-- The timer the bridge writes for an Overfull level, a meal pool M and whether a drain state is active: TIMER_FULL at
-- Overfull 4, whatever else holds (the stomach is full, starving or not); 0 while a drain is active (a starving body is
-- not Well Fed); TIMER_WELL_FED_2 while sated at Overfull 2 or 3, TIMER_WELL_FED while sated below it; else 0. An M that
-- is not a number at least WELL_FED_M (NaN included) reads unsated. Each value is K.view.timerValues(dayMin)'s; a nil
-- dayMin reads the 90-minute day (K.drain.DAY_MINUTES), so a caller may test the target against 0 before reading the day.
function K.view.foodTimer(level, M, draining, dayMin)
    local wf1, wf2, full = K.view.timerValues(dayMin or K.drain.DAY_MINUTES)
    if level >= K.view.REFUSE_AT then
        return full
    end
    if draining then
        return 0
    end
    if not (type(M) == "number" and M >= K.view.WELL_FED_M) then
        return 0
    end
    if level >= K.view.WELL_FED_2_AT then
        return wf2
    end
    return wf1
end

-- The three written values at a day length of dayMin real minutes: each keeps its band through HOLD_MIN game minutes of
-- vanilla's drain (2 x dayMin units a game minute, #2385, #2922), never below the 90-minute values; the Well Fed values
-- stop at their band's top (1600, 3200), where a day over 800 real minutes can no longer hold a level for a whole minute
-- with one write; the refusal has no top (level 4, above 4800, refuses alike).
function K.view.timerValues(dayMin)
    local d = K.drain.UNITS_PER_MIN * dayMin * K.view.HOLD_MIN
    local wf1 = K.min(1600, K.max(K.view.TIMER_WELL_FED, d + 1))
    local wf2 = K.min(3200, K.max(K.view.TIMER_WELL_FED_2, 1600 + d + 1))
    local full = K.max(K.view.TIMER_FULL, 3200 + d + 1)
    return wf1, wf2, full
end

-- The FOOD_EATEN band of a timer value, the bands the push is keyed on (#0511, strict greater-than, #0507): 0 at or
-- under 0, 1 to 1600, 2 to 3200, 3 above (the refusal; level 4 above 4800 refuses alike).
function K.view.timerBand(t)
    if t > 3200 then
        return 3
    end
    if t > 1600 then
        return 2
    end
    if t > 0 then
        return 1
    end
    return 0
end

-- The moodle classes of a mirror m (nil reads all zero): the four K.view.classes reads (def its deficiency set),
-- plus overfull from the mirror's stomachMass (a mirror without it reads 0).
function K.view.moodleClasses(m, def)
    local c = K.view.classes(m, def)
    c.overfull = 0
    if m == nil then
        return c
    end
    c.overfull = K.view.fullnessLevel(m.stomachMass)
    return c
end

-- The level-1 hide option (Plan 15 Task 9; spec section 4, item 10d): the client's own option hides level 1 of the
-- Stimulant, Sleep and Excess moodles, the three whose first level is a mild state the player need not act on; the
-- panel's class rows always show the level.
K.view.HIDE_ONE = { stimulant = true, sleep = true, excess = true }

-- The level a moodle shows for class cls at level n: 0 while hideOne is true, n is 1 and the class is one of HIDE_ONE,
-- else n.
function K.view.shownLevel(cls, n, hideOne)
    if hideOne == true and n == 1 and K.view.HIDE_ONE[cls] == true then
        return 0
    end
    return n
end

-- --- the Body fat row (Bands and up): the fat fraction as a sex-specific word, with a hold --------------------------
-- The fraction is body_fm / body_weight off the mirror, so no new mirror field is sent. The cuts are the 20-39 y column
-- of the percent-body-fat table at the BMI cut-offs 18.5, 25 and 30 (Gallagher 2000, Table 4), used for every age: a game
-- choice. Each sex lists the four ascending lower bounds of bands 1-4 (lean, healthy, high, very high); below the first
-- the band is 0, very lean. Fractions, not percent.
K.view.FAT_CUTS_MALE = {
    0.06, -- gc: game choice, the lean band from 6 %, inside the 4-6 % floor of healthy active men in a prolonged deficit (S1910)
    0.08, -- the healthy band from 8 %, the BMI 18.5 body fat of men aged 20-39 y (S1905)
    0.20, -- the high band from 20 %, the BMI 25 body fat of men aged 20-39 y (S1905)
    0.25, -- the very high band from 25 %, the BMI 30 body fat of men aged 20-39 y (S1905)
}
K.view.FAT_CUTS_FEMALE = {
    0.13, -- gc: game choice, the lean band from 13 %, the 12.7 % a competition diet brought healthy women to, rounded (S1911)
    0.21, -- the healthy band from 21 %, the BMI 18.5 body fat of women aged 20-39 y (S1904)
    0.33, -- the high band from 33 %, the BMI 25 body fat of women aged 20-39 y (S1904)
    0.39, -- the very high band from 39 %, the BMI 30 body fat of women aged 20-39 y (S1904)
}
K.view.FAT_WORDS = { "lean", "healthy", "high", "veryHigh" }
K.view.FAT_WORDS[0] = "veryLean"
K.view.FAT_BAND = 0.005 -- gc: game choice, half a percentage point of body fat: a shown word holds until the fraction leaves its band by more than this, so a fraction on a cut does not flicker; the width informed by the 3-4 % relative coefficient of variation of a DXA fat reading (about 0.6-0.8 percentage points at 20 % fat) (S1909)
K.view.NO_DATA = "UI_NR_Band_none" -- the band words' No data key, the row text when a mirror has no body

-- A key from prefix and word: the word when it is a non-empty string, else "none" (the band words' No data).
function K.view.bandKey(prefix, word)
    if type(word) ~= "string" or word == "" then
        return prefix .. "none"
    end
    return prefix .. word
end

-- The band of v on the ascending lower bounds at, held: last (a whole number 0..#at) stays while v lies within band
-- of last's own range (last's lower bound less band up to its upper bound plus band); otherwise the plain rung of v.
-- A last that is not a whole number in range reads none.
function K.view.heldRung(v, at, last, band)
    local n = K.view.rung(v, at)
    if type(v) ~= "number" or type(last) ~= "number" or last ~= math.floor(last) or last < 0 or last > #at then
        return n
    end
    local lo = -math.huge
    if last > 0 then
        lo = at[last]
    end
    local hi = math.huge
    if last < #at then
        hi = at[last + 1]
    end
    if v >= lo - band and v <= hi + band then
        return last
    end
    return n
end

-- The body-fat band index (0 very lean .. 4 very high) of a mirror m for a sex (female true), holding last, or nil when
-- the mirror has no body (a body_weight that is not a positive number, or a body_fm that is not a number).
function K.view.fatBand(m, female, last)
    local w = m.body_weight
    local fm = m.body_fm
    if type(w) ~= "number" or type(fm) ~= "number" or not (w > 0) then
        return nil
    end
    local cuts = K.view.FAT_CUTS_MALE
    if female == true then
        cuts = K.view.FAT_CUTS_FEMALE
    end
    return K.view.heldRung(fm / w, cuts, last, K.view.FAT_BAND)
end

-- The Strength row, pushed at level 2 (ruling 13-19): the true level truncated to one decimal, never rounded up (a 9.96 reads
-- 9.9, not 10.0 beside a native 9; a level built on an integer reads it whole), or No data when the mirror carries no finite body_level.
function K.view.levelRow(rows, m)
    local v = m.body_level
    if not K.finite(v) then
        K.view.push(rows, "body_level", "UI_NR_Row_body_level", K.view.NO_DATA, 2, true)
        return
    end
    local shown = K.max(0, math.floor((v + 1e-9) * 10) / 10) -- the epsilon of K.strength.shown; a negative level reads 0.0 (the perk is clamped at 0)
    K.view.push(rows, "body_level", "UI_NR_Row_body_level", K.view.fmt(shown, 1), 2, false)
end

-- The Body fat row, pushed at level 2: its text the band word (UI_NR_FatBand_<word>) or No data, its fatBand the index the
-- client holds for the next build (nil with no body). fat is { female, last } or nil.
function K.view.fatRow(rows, m, fat)
    local female = false
    local last = nil
    if fat ~= nil then
        female = fat.female
        last = fat.last
    end
    local idx = K.view.fatBand(m, female, last)
    local text = K.view.NO_DATA
    if idx ~= nil then
        text = K.view.bandKey("UI_NR_FatBand_", K.view.FAT_WORDS[idx])
    end
    local r = K.view.push(rows, "body_fat", "UI_NR_Row_body_fat", text, 2, true)
    r.fatBand = idx
end
