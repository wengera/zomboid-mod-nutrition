-- NR_Kernel_View.lua: the interface's row model: the client's stored mirror (NR_Kernel_Mirror.lua) in, at one of three
-- visibility levels (1 Symptoms, 2 Bands, 3 Numbers), an array of rows out; the moodle classes; a food's tooltip lines.
-- Pure: no engine global, no getText: every label and word is a translation KEY (isKey true) the client resolves.
-- A row is { key, label, text, level, isKey } plus cls and n on a class row. One statement per line for the coverage
-- gate. Sorts after NR_Kernel.lua, NR_Kernel_Fluids.lua and NR_Kernel_Nutrients.lua; K.* resolves at call time.
local K = NutritionRevamp.kernel
K.view = {}

-- The Energy and Hydration classes are removed: vanilla's calibrated hunger and thirst moodles are the signals, and the
-- panel shows the drain state, the weight trend and the dehydration per cent instead.
K.view.CLASSES = { "deficiency", "excess", "stimulant", "sleep" }

-- Each ladder is the four ascending lower bounds of class levels 1-4; below the first the class reads 0.
-- stimulant: acute_caf, mg in the body.
K.view.STIMULANT_AT = {
    K.dials.get("view.STIMULANT_AT.1"),
    K.dials.get("view.STIMULANT_AT.2"),
    K.dials.get("view.STIMULANT_AT.3"),
    K.dials.get("view.STIMULANT_AT.4"),
}

-- sleep: acute_debtH, game hours (capped at K.acute.DEBT_MAX).
K.view.SLEEP_AT = {
    K.dials.get("view.SLEEP_AT.1"),
    K.dials.get("view.SLEEP_AT.2"),
    K.dials.get("view.SLEEP_AT.3"),
    K.dials.get("view.SLEEP_AT.4"),
}

-- deficiency and excess: the worst grade less one and the highest rung, each capped at the top rung, 3.
K.view.RUNG_MAX = 3

-- Shares of the per-day requirement one item gives.
K.view.RICH_SHARE = K.dials.get("view.RICH_SHARE")
K.view.LOW_SHARE = K.dials.get("view.LOW_SHARE")
K.view.TIP_MAX = K.dials.get("view.TIP_MAX")

-- Patterns by digit count, never %d (the Kahlua %d rule, #0939).
K.view.FORMATS = { "%.1f", "%.2f", "%.3f" }
K.view.FORMATS[0] = "%.0f"

-- "" for anything that is not a finite number.
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

function K.view.unitText(v, digits, unit)
    local text = K.view.fmt(v, digits)
    if text ~= "" and unit ~= nil then
        text = text .. " " .. unit
    end
    return text
end

-- 0 digits at 100 and over, 1 at 10 and over, else 2.
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

-- Anything that is not a number reads 1, Symptoms.
function K.view.clampLevel(level)
    if type(level) ~= "number" or level ~= level then
        return 1
    end
    return K.clamp(math.floor(level), 1, 3)
end

-- 3 with either Nutritionist trait.
function K.view.level(optionLevel, hasTrait)
    local o = K.view.clampLevel(optionLevel)
    if hasTrait == true then
        o = 3
    end
    return o
end

-- The one per-frame test a surface makes.
function K.view.changed(received, lastReceived, level, lastLevel)
    return received ~= lastReceived or level ~= lastLevel
end

-- 0 when v is not a number.
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

-- m is the client's Lua-shaped copy, so pairs is allowed. The excess scan reads every nut_<key>_x,
-- the deficiency scan only the nut_<key>_g of a key in def (K.view.deficiencyKeys; nil reads none).
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

-- The live state that marks a push, as one integer of digits (sleep, stimulant, Overfull, dehydration %, trend word,
-- then the drain sets), so a new drain line, trend word or per cent reaches the panel at the next slow minute.
-- Deficiency and excess move with the nutrient epoch, which already marks a push.
function K.view.pushSignature(dehydPct, caf, debtH, massG, drainSig, trend)
    local s = K.view.rung(caf or 0, K.view.STIMULANT_AT)
    local sl = K.view.rung(debtH or 0, K.view.SLEEP_AT)
    local o = K.view.fullnessLevel(massG)
    local d = K.view.digit(dehydPct, 9)
    local t = K.view.digit(trend or 1, 2)
    return K.view.digit(drainSig, 16383) * 100000 + t * 10000 + d * 1000 + o * 100 + s * 10 + sl
end

-- The active mask plus 128 x the recovering mask while a ceiling applies, else 0.
function K.view.drainSignal(D)
    if type(D) ~= "table" or D.active ~= true or not K.finite(D.mask) or not K.finite(D.recovering) then
        return 0
    end
    return D.mask + 128 * D.recovering
end

-- Anything that is not a finite number reads 0.
function K.view.digit(v, hi)
    if not K.finite(v) then
        return 0
    end
    return K.clamp(math.floor(v), 0, hi)
end

-- A rolling hash of the username (#3456), so players first seen together push in different frames; only the first gap.
function K.view.pushOffset(username, gapMs)
    return K.nameHash(username) % gapMs
end

-- nil def reads none; anything not numeric is skipped.
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

function K.view.row(key, label, text, level, isKey)
    local r = {}
    r.key = key
    r.label = label
    r.text = text
    r.level = level
    r.isKey = isKey
    return r
end

function K.view.push(rows, key, label, text, level, isKey)
    local r = K.view.row(key, label, text, level, isKey)
    rows[#rows + 1] = r
    return r
end

-- Every level: the four class rows, then one line per drain state (K.view.drainRows); Bands and up: the body block, the
-- dehydration per cent above DEHYD_SHOW and each graded key's grade and excess words (a key not yet graded, g < 1, has no
-- grade row); Numbers: the figures. order nil lists no grade rows; fat nil reads a man with no word held.
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
    K.view.drainRows(rows, mm.drain_mask, mm.drain_rec)
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

-- An ungraded key (g absent or under 1) shows its excess row alone, only while its rung is above 0.
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

-- At Numbers the rung as a figure; at Bands the Excess word while above 0; none at Symptoms. NaN is not above 0.
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

-- --- the panel's signal lines -----------------------------------------------------------------------------------------
-- One row per active or recovering drain state, in code order, UI_NR_Drain_<name> or UI_NR_DrainRec_<name>. Pushed at
-- level 1: the drain is the body's damage signal the removed Energy moodle carried, so every level shows it.
function K.view.drainRows(rows, mask, rec)
    if not K.finite(mask) or mask < 0 then
        mask = 0
    end
    if not K.finite(rec) or rec < 0 then
        rec = 0
    end
    if mask + rec <= 0 then
        return
    end
    for code = 1, #K.drain.states do
        local name = K.drain.states[code].name
        local text = nil
        if K.view.hasBit(mask, code) then
            text = "UI_NR_Drain_" .. name
        elseif K.view.hasBit(rec, code) then
            text = "UI_NR_DrainRec_" .. name
        end
        if text ~= nil then
            local r = K.view.push(rows, "drain_" .. name, "UI_NR_Row_drain", text, 1, true)
            r.cls = "drain"
            r.n = 1
        end
    end
end

-- Lua 5.1 has no bit operators.
function K.view.hasBit(mask, c)
    return math.floor(mask / 2 ^ (c - 1)) % 2 == 1
end

-- The weight trend word reads K.body.flags, the flags that set vanilla's weight arrows (NR_Server_Weight), so the panel
-- and the character screen never disagree: one threshold.
K.view.TREND_WORDS = { "steady", "gaining" }
K.view.TREND_WORDS[0] = "losing"

-- A slope that is not a finite number reads 1, steady.
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

-- No data with no body (a non-positive body_weight or a non-finite body_trend).
function K.view.trendRow(rows, m)
    local text = K.view.NO_DATA
    if K.finite(m.body_trend) and K.finite(m.body_weight) and m.body_weight > 0 then
        text = "UI_NR_Trend_" .. K.view.TREND_WORDS[K.view.trendIndex(m.body_trend)]
    end
    K.view.push(rows, "body_trend", "UI_NR_Row_body_trend", text, 2, true)
end

-- Vanilla's thirst moodle is the signal; this row is its figure, shown only above DEHYD_SHOW.
K.view.DEHYD_SHOW = K.dials.get("view.DEHYD_SHOW")
function K.view.dehydRow(rows, pct)
    if not K.finite(pct) or pct <= K.view.DEHYD_SHOW then
        return
    end
    K.view.push(rows, "fluids_dehydPct", "UI_NR_Row_fluids_dehydPct", K.view.unitText(pct, 1, "%"), 2, false)
end

-- --- the Deficiency moodle's nutrients ---------------------------------------------------------------------------------
-- The nutrients whose grade drives an effect, built from the tables at load, never a hand list: every grade row, a gated
-- row only while its table flag is true (the composer folds a gated row only then), the grade aggregates' members and
-- the drain's clinical onsets. nil effects reads the onsets alone.
function K.view.deficiencyKeys(effects)
    local out = {}
    for _, key in pairs(K.drain.NUTRIENT) do
        out[key] = true
    end
    if effects == nil or type(effects.ROWS) ~= "table" then
        return out
    end
    for i = 1, #effects.ROWS do
        K.view.deficiencyRow(out, effects, effects.ROWS[i])
    end
    return out
end

-- The loop body, kept apart so the line-granular coverage gate sees each outcome.
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
    for i = 1, #members do
        out[members[i]] = true
    end
end

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

-- Kind not in K.nutrients.UNGRADED. nil reads none.
function K.view.gradedOrder(records)
    return K.view.kindOrder(records, true)
end

-- No grade row, but an excess that raises the Excess class. nil reads none.
function K.view.ungradedOrder(records)
    return K.view.kindOrder(records, false)
end

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

-- Vitamin A is retinol in the vector and vitA in the records (#3240); the test pins every key that differs.
K.view.RECORD_KEY = { retinol = "vitA" }

-- gc: a game choice, the DRI tables' 70 kg reference adult; the band ranks one item against a fixed daily amount,
-- never the character's own mass (the client holds no body).
K.view.REF_KG = K.dials.get("view.REF_KG")

-- A per-protein maximum reads its floor R; a per-kg record R x REF_KG; a per-MJ record its RDA Rmin (its R is per MJ
-- expended, not a daily amount; the engine never reads Rmin, the band does); nil for any other scale.
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

-- Keyed by the VECTOR key; a record counts only when its unit is the vector's own. nil records or units read empty.
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

-- A missing or non-number value reads 0; nil when the key has no positive requirement.
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

-- A tie keeps the earlier key.
function K.view.better(f, bestF, best, rich)
    if rich then
        return f >= K.view.RICH_SHARE and (best == nil or f > bestF)
    end
    return f <= K.view.LOW_SHARE and (best == nil or f < bestF)
end

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

-- Every level: the fill line first (it stands in for vanilla's hunger line, which the client hides), then the source
-- line; Bands: the macros and up to three rich and three low keys; Numbers: every non-zero key. A nil vector is the
-- source line alone.
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

-- The fill line: the hours a precomputed replay of the item alone holds h_model under Peckish (tools/food_fills.py,
-- NR_Data_Fills.lua; never a per-frame or per-hover simulation), to the nearest half hour, per whole item.
K.view.FILL_MIN_H = K.dials.get("view.FILL_MIN_H")
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

-- A symptom is a BAD moodle, so the map runs down MoodleFramework's bad side from its stored default 0.5, where the
-- moodle leaves the UI manager (MF_ISMoodle.lua :75), to 0.0 at each class's top level.
K.view.MOODLE_NEUTRAL = 0.5 -- gc: the framework's default stored value (MF_ISMoodle.lua:75), neutral under its thresholds
K.view.MOODLE_LEVELS = 4 -- the class ladders' top level (STIMULANT_AT, SLEEP_AT, and Overfull's four levels)

-- RUNG_MAX for deficiency and excess.
function K.view.moodleTop(cls)
    if cls == "deficiency" or cls == "excess" then
        return K.view.RUNG_MAX
    end
    return K.view.MOODLE_LEVELS
end

-- Clamped 0..1 by the mod because the framework never clamps (#2535).
function K.view.moodleValue(level, cls)
    local top = K.view.moodleTop(cls)
    local n = level
    if type(n) ~= "number" or n ~= n then
        n = 0
    end
    n = K.clamp(math.floor(n), 0, top)
    return K.clamp(K.view.MOODLE_NEUTRAL - K.view.MOODLE_NEUTRAL * n / top, 0, 1)
end

-- Midway between levels k - 1 and k, so the framework's level equals the class level with no float tie; nil above the
-- class's top, which the framework reads as unreachable (MF_ISMoodle.lua :161-164).
function K.view.moodleThreshold(k, cls)
    local top = K.view.moodleTop(cls)
    if k > top then
        return nil
    end
    return K.view.MOODLE_NEUTRAL - K.view.MOODLE_NEUTRAL * (k - 0.5) / top
end

-- Overfull reads the stomach's whole mass, both lanes, through K.satiety.discomfort: never the physical fill, which
-- clamps at 1, nor the satiety F. At level 4 the server refuses eating through vanilla's food timer (K.view.foodTimer).
K.view.OVERFULL_AT = {
    K.dials.get("view.OVERFULL_AT.1"),
    K.dials.get("view.OVERFULL_AT.2"),
    K.dials.get("view.OVERFULL_AT.3"),
}

-- 0 at or under CAPACITY_MAX_G; a non-number, NaN, +infinity or negative mass reads 0.
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

-- Over the mirror's rounded stomachMass, the very number the client's moodle reads, so the server's refusal changes level
-- with the moodle the player sees. A malformed buffer reads 0, so neither the writer nor the effects step raises on it.
K.view.MASS_KEYS = { "water", "proteins", "carbs", "lipids", "fibre" } -- K.stomach.massOf's keys, no row needed
function K.view.overfullOf(record)
    local s = record.stomach
    if s == nil or type(s.buffer) ~= "table" then
        return 0
    end
    for i = 1, #K.view.MASS_KEYS do
        if type(s.buffer[K.view.MASS_KEYS[i]]) ~= "number" then
            return 0
        end
    end
    return K.view.fullnessLevel(K.mirror.stomachMass(record))
end

-- --- the food-timer bridge ---------------------------------------------------------------------------------------------
-- The mod owns vanilla's food timer, which alone drives Well Fed (#0511) and every vanilla eat and drink refusal at its
-- level 3; the client's copy follows in the stats packet (#3896). Vanilla drains it 2 x dayMin units a game minute
-- (#2922), so each written value is sized from the day length to keep its band until the next write.
K.view.TIMER_WELL_FED = K.dials.get("view.TIMER_WELL_FED")
K.view.TIMER_WELL_FED_2 = K.dials.get("view.TIMER_WELL_FED_2")
K.view.TIMER_FULL = K.dials.get("view.TIMER_FULL")
K.view.HOLD_MIN = K.dials.get("view.HOLD_MIN")
K.view.WELL_FED_M = K.dials.get("view.WELL_FED_M")
K.view.WELL_FED_2_AT = K.dials.get("view.WELL_FED_2_AT")
K.view.REFUSE_AT = K.dials.get("view.REFUSE_AT")
K.view.TIMER_BAND_2 = K.dials.get("view.TIMER_BAND_2")
K.view.TIMER_BAND_3 = K.dials.get("view.TIMER_BAND_3")

-- TIMER_FULL at Overfull 4 whatever else holds; 0 while a drain is active (a starving body is not Well Fed); else the Well
-- Fed values while sated. A nil dayMin reads the 90-minute day, so a caller may test the target against 0 first.
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

-- Never below the 90-minute values; the Well Fed values stop at their band's top, where a day over 800 real minutes can
-- no longer hold a level for a whole minute with one write.
function K.view.timerValues(dayMin)
    local d = K.drain.UNITS_PER_MIN * dayMin * K.view.HOLD_MIN
    local wf1 = K.min(K.view.TIMER_BAND_2, K.max(K.view.TIMER_WELL_FED, d + 1))
    local wf2 = K.min(K.view.TIMER_BAND_3, K.max(K.view.TIMER_WELL_FED_2, K.view.TIMER_BAND_2 + d + 1))
    local full = K.max(K.view.TIMER_FULL, K.view.TIMER_BAND_3 + d + 1)
    return wf1, wf2, full
end

-- Strict greater-than (#0507); level 4 above 4800 refuses alike.
function K.view.timerBand(t)
    if t > K.view.TIMER_BAND_3 then
        return 3
    end
    if t > K.view.TIMER_BAND_2 then
        return 2
    end
    if t > 0 then
        return 1
    end
    return 0
end

-- A mirror without stomachMass reads overfull 0.
function K.view.moodleClasses(m, def)
    local c = K.view.classes(m, def)
    c.overfull = 0
    if m == nil then
        return c
    end
    c.overfull = K.view.fullnessLevel(m.stomachMass)
    return c
end

-- Hides level 1 of the three classes whose first level needs no action; the panel's class rows always show it.
K.view.HIDE_ONE = { stimulant = true, sleep = true, excess = true }

-- 0 while hideOne is true, n is 1 and the class is in HIDE_ONE.
function K.view.shownLevel(cls, n, hideOne)
    if hideOne == true and n == 1 and K.view.HIDE_ONE[cls] == true then
        return 0
    end
    return n
end

-- --- the Body fat row ------------------------------------------------------------------------------------------------
-- body_fm / body_weight off the mirror, so no new field is sent. The cuts are Gallagher 2000's 20-39 y column at the BMI
-- cut-offs, used for every age (a game choice). Fractions, not percent.
K.view.FAT_CUTS_MALE = {
    K.dials.get("view.FAT_CUTS_MALE.1"),
    K.dials.get("view.FAT_CUTS_MALE.2"),
    K.dials.get("view.FAT_CUTS_MALE.3"),
    K.dials.get("view.FAT_CUTS_MALE.4"),
}
K.view.FAT_CUTS_FEMALE = {
    K.dials.get("view.FAT_CUTS_FEMALE.1"),
    K.dials.get("view.FAT_CUTS_FEMALE.2"),
    K.dials.get("view.FAT_CUTS_FEMALE.3"),
    K.dials.get("view.FAT_CUTS_FEMALE.4"),
}
K.view.FAT_WORDS = { "lean", "healthy", "high", "veryHigh" }
K.view.FAT_WORDS[0] = "veryLean"
K.view.FAT_BAND = K.dials.get("view.FAT_BAND")
K.view.NO_DATA = "UI_NR_Band_none" -- the band words' No data key, the row text when a mirror has no body

-- An empty or non-string word reads "none" (No data).
function K.view.bandKey(prefix, word)
    if type(word) ~= "string" or word == "" then
        return prefix .. "none"
    end
    return prefix .. word
end

-- last stays while v lies within band of its own range; a last out of range reads none.
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

-- nil with no body (a non-positive body_weight or a non-number body_fm).
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

-- Truncated to one decimal, never rounded up, so a 9.96 never reads 10.0 beside a native 9.
function K.view.levelRow(rows, m)
    local v = m.body_level
    if not K.finite(v) then
        K.view.push(rows, "body_level", "UI_NR_Row_body_level", K.view.NO_DATA, 2, true)
        return
    end
    local shown = K.max(0, math.floor((v + 1e-9) * 10) / 10) -- the epsilon of K.strength.shown; a negative level reads 0.0 (the perk is clamped at 0)
    K.view.push(rows, "body_level", "UI_NR_Row_body_level", K.view.fmt(shown, 1), 2, false)
end

-- fatBand is the index the client holds for the next build; fat is { female, last } or nil.
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
