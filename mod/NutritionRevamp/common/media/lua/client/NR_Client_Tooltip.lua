-- NR_Client_Tooltip.lua -- the food-tooltip band: one sentinel wrap of ISToolTipInv.render that draws the mod's own
-- framed strip below the engine's box, its lines the food's vector through the intake's own source chain
-- (K.vector.resolve). An evolved dish or a craft output uses the intake's dish and craft sources, which the band does
-- not run (a scope gap). Why a band and how it is wrapped: docs/platform/client-ui.md#tooltip.
-- Pitfalls:
--  * The body is sized and painted in Java before the draw pass (#2490), so a line drawn after the original has no
--    background: the band paints its own frame and sets its own height (#2517). The original draws nothing while a
--    context menu is visible, so the wrap repeats that test (#2496).
--  * No padBottom write: the exposer gives a release client no route to an instance field (#2735).
--  * One wrap covers every site that constructs ISToolTipInv (#2494), CleanUI included (#2499).
--  * The original clamps the box to the screen from its own height, so the band goes ABOVE the box under
--    anchorBottomLeft or near the screen's bottom. Both on-screen draws are UNMEASURED (the harness cannot hover).
--  * PER WHOLE ITEM at script scale: a live macro shrinks with each partial eat (#2843), so the getters are re-scaled
--    by getBaseHunger / getHungChange; the item's own macros overwrite the table seed's. Never a thirst: a cooked
--    food's thirst reads halved on a client (#1147).
--  * The fill line stands in for vanilla's hunger line only while the item's whole-item kcal is the fill table's
--    within FILL_TOL, and never for an evolved recipe's result.
--  * The sentinel NR_ClientTooltip_Installed, a global (#0943), records the CLASS TABLE it wrapped and re-wraps only a re-created class
--    (#2844), never overwriting a saved original. The wrapper looks NutritionRevamp.client.tooltip up per call;
--    linesFor runs BEFORE the original under a pcall, the original exactly once, the band under a pcall.
--  * Client files load by path, so NR.client.text, the options and the view are looked up per call.
-- Vanilla's argument order: drawRect and drawRectBorder take alpha first (x, y, w, h, a, r, g, b), drawText last (str, x, y, r, g, b, a, font).
-- Cadence: per rendered frame while a tooltip is up, about nine guarded getters form the cache key; the vector is
-- built once per type and whole-item macro tuple.
local NR = NutritionRevamp
local K = NR.kernel

NR.client.tooltip = {
    stats = { draws = 0, lines = 0, cacheHits = 0, errors = 0, installs = 0, builds = 0, invalidations = 0, above = 0, reentries = 0, breaks = 0, stale = 0, hidden = 0, shown = 0 },
    cache = {},
    R = {},
    last = nil,
    lastError = nil,
    BREAK_AT = K.dials.get("tooltip.BREAK_AT"),
    REENTRY_MS = K.dials.get("tooltip.REENTRY_MS"),
    fails = 0, -- consecutive failures; a clean render resets it
    broken = false, -- true once BREAK_AT failures ran in a row: the saved original only until a reload
    depth = 0, -- 0 outside a render, 1 while linesFor runs, 2 while the original draws
    depthAt = 0, -- T.now() when the depth was last set
    LINE_SPACING = 14, -- the band's line step when the tooltip object's getLineSpacing cannot be read
    PAD = 6, -- the band's vertical padding, 3 above the first line and 3 below the last
    INSET = 8, -- the text's left inset inside the band
    BG = { r = 0, g = 0, b = 0, a = 0.8 }, -- the frame's fill when the panel carries no backgroundColor
    BORDER = { r = 0.4, g = 0.4, b = 0.4, a = 1 }, -- the frame's border when the panel carries no borderColor
    FILL_TOL = K.dials.get("tooltip.FILL_TOL"),
    pending = nil, -- the tag set T.hide added the hide tag to, until T.unhide takes it off
}
local T = NR.client.tooltip

local function read(obj, name, ...)
    if obj == nil then return nil end
    local ok, v = NR.try(obj, name, ...)
    if ok then return v end
    return nil
end

local function num(v)
    if NR.finite(v) then return v end
    return 0
end

-- The readable word a translation key falls back to while its JSON is absent.
function T.fallback(key)
    if type(key) ~= "string" then return "" end
    local src = string.match(key, "^UI_NR_Tip_Source_(.+)$")
    if src ~= nil then return "Per whole item (" .. src .. ")" end
    local row = string.match(key, "^UI_NR_Row_(.+)$")
    if row ~= nil then return row end
    if key == "UI_NR_Tip_Rich" then return "rich" end
    if key == "UI_NR_Tip_Low" then return "low" end
    if key == "UI_NR_Tip_Fills" then return "A whole one fills you for about" end
    if key == "UI_NR_Tip_FillsUnder" then return "A whole one fills you for under half an hour" end
    if key == "UI_NR_Tip_FillsOver" then return "A whole one fills you for more than" end
    return key
end

function T.text(key)
    local fb = T.fallback(key)
    local ok, v = pcall(NR.text, key, fb)
    if ok and type(v) == "string" then return v end
    return fb
end

-- Its default, on, when absent or raising.
function T.optionOn()
    local nr = NutritionRevamp
    local o = nil
    if nr ~= nil and nr.client ~= nil then o = nr.client.options end
    if o == nil or type(o.tooltipLines) ~= "function" then return true end
    local ok, v = pcall(o.tooltipLines)
    if not ok then return true end
    return v ~= false
end

-- 1 when there is no view yet.
function T.level()
    local nr = NutritionRevamp
    local v = nil
    if nr ~= nil and nr.client ~= nil then v = nr.client.view end
    if v == nil or type(v.level) ~= "number" then return 1 end
    return v.level
end

-- 1 male, 2 female; 1 when there is no view or it holds none.
function T.sex()
    local nr = NutritionRevamp
    local v = nil
    if nr ~= nil and nr.client ~= nil then v = nr.client.view end
    if v ~= nil and v.female == true then return 2 end
    return 1
end

-- Built once per sex.
function T.requirements(sex)
    local r = T.R[sex]
    if r ~= nil then return r end
    local nr = NutritionRevamp
    local data = nr.data or {}
    r = nr.kernel.view.requirements(data.records, sex, data.UNITS)
    T.R[sex] = r
    return r
end

function T.invalidate()
    T.cache = {}
    T.last = nil
    T.R = {}
    T.stats.invalidations = T.stats.invalidations + 1
end

-- Once per listeners table; the closure lives on the global NR_ClientTooltip_Hook and looks the tooltip up per call.
function T.hook()
    local nr = NutritionRevamp
    local v = nil
    if nr ~= nil and nr.client ~= nil then v = nr.client.view end
    if v == nil or type(v.listeners) ~= "table" then return false end
    NR_ClientTooltip_Hook = NR_ClientTooltip_Hook or {}
    local h = NR_ClientTooltip_Hook
    if h.fn == nil then
        h.fn = function()
            local t = NutritionRevamp.client.tooltip
            if t ~= nil and t.invalidate ~= nil then t.invalidate() end
        end
    end
    if h.listeners == v.listeners then return false end
    local l = v.listeners
    for i = 1, #l do
        if l[i] == h.fn then
            h.listeners = l
            return false
        end
    end
    l[#l + 1] = h.fn
    h.listeners = l
    return true
end

-- 1 when either is 0 or unreadable, or below 1 (never shrink a never-eaten item).
function T.wholeScale(item)
    local base = num(read(item, "getBaseHunger"))
    local raw = num(read(item, "getHungChange"))
    if base == 0 or raw == 0 then return 1 end
    local s = base / raw
    if s < 1 then return 1 end
    return s
end

-- The declared-nutrients contract (#2676), or nil.
function T.declaredOf(item)
    local md = read(item, "getModData")
    if type(md) ~= "table" then return nil end
    local v = md.NR_Nutrients
    if type(v) == "string" then return v end
    return nil
end

-- The row's sep defaults to ": ".
function T.lineOf(row)
    local label = T.text(row.label)
    local txt = row.text
    if type(txt) ~= "string" or txt == "" then return label end
    if row.isKey then txt = T.text(txt) end
    local sep = row.sep
    if type(sep) ~= "string" then sep = ": " end
    return label .. sep .. txt
end

-- false when either is not a finite number.
function T.sameKcal(kcal, tableKcal)
    if not NR.finite(kcal) or not NR.finite(tableKcal) then return false end
    return math.abs(kcal - tableKcal) <= T.FILL_TOL * tableKcal + 1
end

-- nil unless the item's whole-item kcal is the table's (T.sameKcal).
function T.fillOf(fullType, kcal)
    local nr = NutritionRevamp
    local fills = nr.data and nr.data.fills
    if fills == nil or type(fills.get) ~= "function" then return nil end
    local h, tk = fills.get(fullType)
    if not T.sameKcal(kcal, tk) then return nil end
    return h
end

-- Vanilla's hunger line: Food.DoTooltip skips it for an item whose script tags hold HIDE_HUNGER_CHANGE, and no Lua reads
-- the tag. T.hide adds the tag just before the original draws, only when absent, and T.unhide takes it off right
-- after (or at the next render if the original raised), so vanilla's own tagged foods are never touched and
-- NutritionMakesSense's same overlay composes. UNMEASURED: the harness cannot hover. At most four Java calls a frame.

function T.hideTag()
    if ItemTag == nil then return nil end
    local ok, tag = pcall(function() return ItemTag.HIDE_HUNGER_CHANGE end)
    if ok then return tag end
    return nil
end

-- The set is kept on T.pending for T.unhide. true when it added.
function T.hide(item)
    local tag = T.hideTag()
    if tag == nil then return false end
    local tags = read(item, "getTags")
    if tags == nil or read(tags, "contains", tag) ~= false then return false end
    local ok, present = pcall(NR.call, tags, "add", tag)
    if not (ok and present) then return false end
    T.pending = tags
    T.stats.hidden = T.stats.hidden + 1
    return true
end

-- Only the remove's Java call is guarded.
function T.unhide()
    local tags = T.pending
    T.pending = nil
    if tags == nil then return end
    local ok, present = pcall(NR.call, tags, "remove", T.hideTag())
    if ok and present then T.stats.shown = T.stats.shown + 1 end
end

-- 0 when nothing measures.
function T.widthOf(lines)
    if getTextManager == nil or UIFont == nil or UIFont.Small == nil then return 0 end
    local ok, tm = pcall(getTextManager)
    if not ok or tm == nil then return 0 end
    local w = 0
    for i = 1, #lines do
        local x = num(read(tm, "MeasureStringX", UIFont.Small, lines[i]))
        if x > w then w = x end
    end
    return w
end

function T.macrosOf(item)
    local s = T.wholeScale(item)
    return {
        calories = num(read(item, "getCalories")) * s,
        carbs = num(read(item, "getCarbohydrates")) * s,
        lipids = num(read(item, "getLipids")) * s,
        proteins = num(read(item, "getProteins")) * s,
    }
end

-- Each macro %.3f (never %d).
function T.keyOf(fullType, declared, level, sex, m)
    return fullType .. "|" .. tostring(declared) .. "|" .. tostring(level) .. "|" .. tostring(sex)
        .. string.format("|%.3f|%.3f|%.3f|%.3f", m.calories, m.carbs, m.lipids, m.proteins)
end

-- nil for no item or a non-Food. The same item again answers from T.last after two Java reads (the hunger left, which
-- every eat moves, and the calories); the key is built on a miss only.
function T.entryFor(item)
    if item == nil then return nil end
    T.hook()
    local level = T.level()
    local sex = T.sex()
    local last = T.last
    if last ~= nil and last.item == item and last.level == level and last.sex == sex
        and last.hung == read(item, "getHungChange") and last.cal == read(item, "getCalories") then
        T.stats.cacheHits = T.stats.cacheHits + 1
        return last.entry
    end
    if read(item, "IsFood") ~= true then return nil end
    local fullType = read(item, "getFullType")
    if type(fullType) ~= "string" then return nil end
    local declared = T.declaredOf(item)
    local macros = T.macrosOf(item)
    local key = T.keyOf(fullType, declared, level, sex, macros)
    local entry = T.cache[key]
    if entry ~= nil then
        T.stats.cacheHits = T.stats.cacheHits + 1
    else
        entry = T.build(item, fullType, declared, level, sex, macros)
        T.cache[key] = entry
    end
    T.last = { item = item, level = level, sex = sex, hung = read(item, "getHungChange"), cal = read(item, "getCalories"),
               entry = entry }
    return entry
end

function T.build(item, fullType, declared, level, sex, macros)
    local nr = NutritionRevamp
    local K = nr.kernel
    macros = macros or T.macrosOf(item)
    local foodType = read(item, "getFoodType")
    if type(foodType) ~= "string" or foodType == "" then foodType = nil end
    local vector, source = K.vector.resolve(declared, macros, foodType, fullType, nr.data)
    local vec = nil
    if vector ~= nil then
        vec = K.vector.add(K.vector.new(), vector, 1)
        vec.calories = macros.calories
        vec.carbs = macros.carbs
        vec.lipids = macros.lipids
        vec.proteins = macros.proteins
    end
    local units = nil
    if nr.data ~= nil then units = nr.data.UNITS end
    local rows = K.view.tooltip(vec, source, level, nil, { R = T.requirements(sex), UNITS = units, fillH = T.fillOf(fullType, macros.calories) })
    local lines = {}
    for i = 1, #rows do
        lines[i] = T.lineOf(rows[i])
    end
    lines.width = T.widthOf(lines)
    lines.fill = rows[1] ~= nil and rows[1].key == "fill" -- the fill row leads when there is one (K.view.tooltip)
    T.stats.builds = T.stats.builds + 1
    return { lines = lines, source = source }
end

function T.linesFor(item)
    local entry = T.entryFor(item)
    if entry == nil then return nil end
    return entry.lines
end

function T.step(el)
    local s = read(el.tooltip, "getLineSpacing")
    if type(s) == "number" and s > 0 then return s end
    return T.LINE_SPACING
end

T.SCREEN_H = 720 -- px, the screen height when getPlayerScreenHeight is absent or raises

-- ABOVE under anchorBottomLeft (a band below would cover the slot) or when the box's bottom plus the band passes the
-- screen, because the original clamps the box from its measured height alone.
function T.above(el, band)
    if el.anchorBottomLeft then return true end
    local top = num(read(el, "getAbsoluteY"))
    local bottom = top + num(read(el, "getHeight"))
    local sh = T.SCREEN_H
    if getPlayerScreenHeight ~= nil then
        local ok, h = pcall(getPlayerScreenHeight, 0)
        if ok and type(h) == "number" and h > 0 then sh = h end
    end
    return bottom + band > sh
end

-- The context-menu test again (#2496); both on-screen draws are UNMEASURED.
function T.band(el, lines)
    if lines == nil or #lines == 0 then return false end
    if not T.optionOn() then return false end
    if ISContextMenu ~= nil and ISContextMenu.instance ~= nil and ISContextMenu.instance.visibleCheck then
        return false
    end
    local n = #lines
    local step = T.step(el)
    local y = num(read(el, "getHeight"))
    local w = num(read(el, "getWidth"))
    local tw = num(lines.width)
    if tw + 2 * T.INSET > w then w = tw + 2 * T.INSET end
    local band = step * n + T.PAD
    local up = T.above(el, band)
    if up then y = -band end
    local bg = el.backgroundColor or T.BG
    local bd = el.borderColor or T.BORDER
    local font = nil
    if UIFont ~= nil then font = UIFont.Small end
    el:drawRect(0, y, w, band, bg.a, bg.r, bg.g, bg.b)
    el:drawRectBorder(0, y, w, band, bd.a, bd.r, bd.g, bd.b)
    for i = 1, n do
        el:drawText(lines[i], T.INSET, y + T.PAD / 2 + (i - 1) * step, 1, 1, 1, 1, font)
    end
    if up then
        T.stats.above = T.stats.above + 1
    else
        el:setHeight(y + band)
    end
    T.stats.draws = T.stats.draws + 1
    T.stats.lines = T.stats.lines + n
    return true
end

function T.after(el, lines)
    local ok, err = pcall(T.band, el, lines)
    if ok then
        T.fails = 0
    else
        T.failed(err)
    end
end

-- TEST-ONLY (`lua.call NutritionRevamp.client.tooltip.probe Base.Apple`): the local player's first item of a full
-- type through getFirstTypeRecurse, run through the band's entry. Returns count, source; no item -> 0, "none".
function T.probe(fullType)
    if getPlayer == nil or type(fullType) ~= "string" then return 0, "none" end
    local ok, p = pcall(getPlayer)
    if not ok or p == nil then return 0, "none" end
    local inv = read(p, "getInventory")
    local item = read(inv, "getFirstTypeRecurse", fullType)
    if item == nil then return 0, "none" end
    local okE, entry = pcall(T.entryFor, item)
    if not okE then
        T.stats.errors = T.stats.errors + 1
        T.lastError = tostring(entry)
        return 0, "error"
    end
    if entry == nil then return 0, "none" end
    return #entry.lines, entry.source
end

-- 0 where there is none (only a test host has none).
function T.now()
    if getTimestampMs == nil then return 0 end
    local ok, v = pcall(getTimestampMs)
    if ok and type(v) == "number" then return v end
    return 0
end

-- A failure (linesFor or the band raised): counted; at BREAK_AT in a row the breaker opens until the next reload.
function T.failed(err)
    T.stats.errors = T.stats.errors + 1
    T.lastError = tostring(err)
    T.fails = T.fails + 1
    if T.fails >= T.BREAK_AT and not T.broken then
        T.broken = true
        T.stats.breaks = T.stats.breaks + 1
        print("[NutritionRevamp] tooltip: " .. tostring(T.fails) .. " failures in a row; the band is off until a reload: " .. T.lastError)
    end
end

-- The wrapper over one original: linesFor first under a pcall, the original exactly once (outside any pcall),
-- then the band. The depth says where the render is: 1 while linesFor runs (pcall'd, so a raise never leaves 1
-- behind), 2 while the original draws; a 2 left by a raising original is honoured as a re-entry only within
-- REENTRY_MS, and is reset at once when older or when there is no clock.
local function makeWrapper(original)
    return function(self)
        local t = nil
        local nr = NutritionRevamp
        if nr ~= nil and nr.client ~= nil then t = nr.client.tooltip end
        if t == nil or t.broken then
            return original(self) -- an open breaker, or no table: the saved original only
        end
        local now = t.now()
        if t.depth == 1 then
            t.stats.reentries = t.stats.reentries + 1
            return original(self) -- re-entered from our own linesFor
        end
        if t.depth == 2 then
            if now > 0 and now - t.depthAt <= t.REENTRY_MS then
                t.stats.reentries = t.stats.reentries + 1
                return original(self) -- re-entered while the original draws
            end
            t.depth = 0
            t.stats.stale = t.stats.stale + 1
            t.unhide() -- a raising original left its tag: taken off before this draw
        end
        t.depth = 1
        t.depthAt = now
        local lines = nil
        if t.linesFor ~= nil then
            local ok, l = pcall(t.linesFor, self.item)
            if ok then
                lines = l
                if l == nil then t.fails = 0 end
            else
                t.failed(l)
            end
        end
        t.depth = 2
        t.depthAt = t.now()
        if lines ~= nil and lines.fill == true and t.optionOn() then
            pcall(t.hide, self.item) -- vanilla's hunger line off for this draw only (the fill line stands in)
        end
        original(self)
        t.unhide()
        if lines ~= nil and t.after ~= nil then t.after(self, lines) end
        t.depth = 0
    end
end

function T.install()
    if ISToolTipInv == nil or type(ISToolTipInv.render) ~= "function" then return false end
    local s = NR_ClientTooltip_Installed
    if s ~= nil and s.class == ISToolTipInv then return false end
    local original = ISToolTipInv.render
    local wrapper = makeWrapper(original)
    NR_ClientTooltip_Installed = { class = ISToolTipInv, original = original, wrapper = wrapper }
    ISToolTipInv.render = wrapper
    T.stats.installs = T.stats.installs + 1
    return true
end

T.install()
T.hook()
