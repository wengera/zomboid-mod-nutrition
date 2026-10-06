-- NR_Client_Tooltip.lua -- the food-tooltip band (Plan 7 Task 6, ruling 8): one sentinel wrap of
-- ISToolTipInv.render that draws the mod's own framed strip BELOW the engine's box, its lines the food's
-- nutrient vector through the intake's own per-item source chain (K.vector.resolve, shared with
-- NR_Server_Intake.lua's IN.chainOne), laid out by K.view.tooltip at the client's visibility level. The band
-- shows the per-item vector the intake's own chain resolves for a whole item at script scale; for an evolved
-- dish or a craft output the intake uses its dish and craft sources instead (NR_Server_Intake.lua), which the
-- band does not run (a scope gap stated, Plan 8+).
--
-- Why a band below the box (docs/platform/client-ui.md#tooltip):
--  * The tooltip body is built in Java inside the one render method, which sizes the panel from its measure
--    pass and paints the background from that height before the draw pass (#2490, #2491), so a line drawn
--    after the original returns has no background: the band paints its own frame and sets its own height
--    (#2517). The wrap repeats the context-menu test before drawing, because the original draws nothing while
--    a context menu is flagged visible (#2496, #2516).
--  * No padBottom write: ObjectTooltip's padBottom is a public instance field (#2511) and the exposer gives a
--    release client no route to an instance field (#2735); the one route is reflective and debug-only (#2745).
--  * One wrap covers the item tooltip at every site the install constructs ISToolTipInv (#2494), and it
--    survives CleanUI, which still constructs the vanilla panel (#2499); under CleanUI a stack's tooltip
--    describes one representative item (#2500). The crafting-slot route (ISItemSlot.drawTooltip, #2495) is
--    not this plan.
--  * Tooltiplib is not installed on this machine (workshop 3694097672 absent on 2026-10-06; Plan 9 reads it):
--    the wrap is composable -- a sentinel, the original called exactly once per render, nothing replaced.
--  * The band sits beside the vanilla nutrition block, which shows under the debug tooltip option, on a
--    readable packaged label or for either Nutritionist trait (#2645); a harness client (-debug) may show both.
--
-- Two unknowns of the worked shape (docs/superpowers/research/platform-client-ui.md, Minimal shapes 2),
-- UNMEASURED UNTIL x183 (Task 11 cannot hover, so stats.draws on a live client is stated unmeasured there):
--  1. whether a draw below a top-level element's rect lands on screen: UIElement.render's early returns read
--     the parent, so a parentless panel is not culled by them (#2512), but no other scissor was traced;
--  2. whether the setHeight below fights the next frame's recompute: the original sets the height to the
--     measured tooltip on every render (ISToolTipInv.lua, `self:setHeight(th)`), so the band's setHeight is
--     re-done each frame from that base and does not accumulate -- read from the code, not booted.
--  3. (UNMEASURED UNTIL x183) the original clamps the box to the screen from the measured height alone, so
--     near the bottom edge the band may run off the screen.
--  With anchorBottomLeft the band runs below the anchor and may cover the slot it is anchored to (unmeasured).
--
-- What the band shows (the build block's rule, the reviewer's residual 8):
--  * PER WHOLE ITEM, at script scale. K.vector.resolve returns the whole-type vector (the table's seed, a
--    declared vector, or one inferred from the macros); the item's OWN four macros (the script's, re-based by
--    the item pass) are written over vector.calories/carbs/lipids/proteins before K.view.tooltip, so the band
--    shows the script's macros, never the table's seed macros.
--  * Never the instance's remaining fraction: a live macro shrinks with each partial eat in step with the raw
--    hunger (the leftover scaling, lessons #2843), so the four getters are re-scaled by
--    getBaseHunger / getHungChange (both non-zero, the ratio >= 1) back to the whole item; a never-eaten item
--    reads ratio 1. The inferred vector is built from those whole-item macros too.
--  * Never a thirst: a cooked food's thirst reads halved on a client (#1147); the band carries none.
--  * The cache key is fullType|declared|level|sex plus the four whole-item macros (after the rescale, each
--    %.3f): an evolved dish or a butchered instance with other macros takes its own entry, and the same-item
--    fast path keys on that same string.
--
-- Shape (the client-file discipline of NR_Client_Effects.lua):
--  * The sentinel NR_ClientTooltip_Installed = { class, original, wrapper } is a global of its own (#0943),
--    never a field of NutritionRevamp, which NR_Core re-creates on every load. It records the CLASS TABLE it
--    wrapped and re-wraps only when ISToolTipInv is a different table (the class re-created; lessons #2844,
--    #2845) -- never merely because render is no longer the wrapper -- and never overwrites a saved original
--    of the same class. The wrapper closes over its own original.
--  * The wrapper names nothing from this file's load: it looks NutritionRevamp.client.tooltip up per call, so
--    a reload swaps the logic under the one wrap. linesFor runs BEFORE the original under a pcall (a failure
--    never touches the vanilla draw); the original is called exactly once; the band draws under a pcall.
--  * Every engine member is reached through the index-first guard (NR.call) inside a pcall (#0935, #1072);
--    NR.call itself does not pcall. Every Java global is named only inside a function behind a nil check, so
--    the file loads with no engine (testing/tests/kernel/test_client_tooltip_shape.py).
--  * Task 5's NR.client.text, NR.client.options.tooltipLines() and NR.client.view.level are looked up per
--    call, never at file scope: client files load alphabetically by path, so this file loads after
--    NR_Client_ModOptions.lua and before NR_Client_View.lua. A missing text function reads the fallback; a
--    missing option accessor reads the option's default, on; a missing view reads level 1.
--  * The cache is cleared by NR.client.tooltip.invalidate, registered on NR.client.view.listeners (called on
--    every view rebuild: a mirror arrival or a level change) at file scope when the view exists, else lazily
--    on the first linesFor; the hook closure lives on the global NR_ClientTooltip_Hook (not on the sentinel) and is registered once per
--    listeners table.
-- Draw calls in the vanilla argument order: ISUIElement:drawRect(x, y, w, h, a, r, g, b) (ISUIElement.lua:1191),
-- drawRectBorder(x, y, w, h, a, r, g, b) (:1219), drawText(str, x, y, r, g, b, a, font) (:1293).
-- Cadence: the wrapper runs per rendered frame while a tooltip is up; per frame it reads the hovered item's
-- type, modData, base hunger, hunger and four macros (about nine guarded getters) to form the cache key and
-- hits the cache (a same-item fast path first); the vector is built once per type and whole-item macro tuple.
local NR = NutritionRevamp

NR.client.tooltip = {
    stats = { draws = 0, lines = 0, cacheHits = 0, errors = 0, installs = 0, builds = 0, invalidations = 0 },
    cache = {},
    R = {},
    last = nil,
    lastError = nil,
    LINE_SPACING = 14, -- the band's line step when the tooltip object's getLineSpacing cannot be read
    PAD = 6, -- the band's vertical padding, 3 above the first line and 3 below the last
    INSET = 8, -- the text's left inset inside the band
    BG = { r = 0, g = 0, b = 0, a = 0.8 }, -- the frame's fill when the panel carries no backgroundColor
    BORDER = { r = 0.4, g = 0.4, b = 0.4, a = 1 }, -- the frame's border when the panel carries no borderColor
}
local T = NR.client.tooltip

-- A Java member's value through the index-first guard inside a protected call, or nil.
local function read(obj, name, ...)
    if obj == nil then return nil end
    local ok, present, v = pcall(NutritionRevamp.call, obj, name, ...)
    if ok and present then return v end
    return nil
end

local function num(v)
    if type(v) == "number" and v == v and v ~= math.huge and v ~= -math.huge then return v end
    return 0
end

-- The readable word a translation key falls back to while its JSON is absent (Task 9 ships the keys).
function T.fallback(key)
    if type(key) ~= "string" then return "" end
    local src = string.match(key, "^UI_NR_Tip_Source_(.+)$")
    if src ~= nil then return "Per whole item (" .. src .. ")" end
    local row = string.match(key, "^UI_NR_Row_(.+)$")
    if row ~= nil then return row end
    if key == "UI_NR_Tip_Rich" then return "rich" end
    if key == "UI_NR_Tip_Low" then return "low" end
    return key
end

-- A key through Task 5's NR.client.text (looked up per call), else its fallback.
function T.text(key)
    local fb = T.fallback(key)
    local nr = NutritionRevamp
    local f = nil
    if nr ~= nil and nr.client ~= nil then f = nr.client.text end
    if type(f) == "function" then
        local ok, v = pcall(f, key, fb)
        if ok and type(v) == "string" then return v end
    end
    return fb
end

-- The tooltipLines option (Task 5's accessor, looked up per call); its default, on, when absent or raising.
function T.optionOn()
    local nr = NutritionRevamp
    local o = nil
    if nr ~= nil and nr.client ~= nil then o = nr.client.options end
    if o == nil or type(o.tooltipLines) ~= "function" then return true end
    local ok, v = pcall(o.tooltipLines)
    if not ok then return true end
    return v ~= false
end

-- The client's visibility level (Task 5's NR.client.view.level), 1 when there is no view yet.
function T.level()
    local nr = NutritionRevamp
    local v = nil
    if nr ~= nil and nr.client ~= nil then v = nr.client.view end
    if v == nil or type(v.level) ~= "number" then return 1 end
    return v.level
end

-- The local player's sex in the Plan 3 convention (1 male, 2 female); 1 when unreadable.
function T.sex()
    if getPlayer == nil then return 1 end
    local ok, p = pcall(getPlayer)
    if not ok or p == nil then return 1 end
    if read(p, "isFemale") == true then return 2 end
    return 1
end

-- The per-key daily requirement map for a sex, built once per sex (K.view.requirements over NR.data).
function T.requirements(sex)
    local r = T.R[sex]
    if r ~= nil then return r end
    local nr = NutritionRevamp
    local data = nr.data or {}
    r = nr.kernel.view.requirements(data.records, sex, data.UNITS)
    T.R[sex] = r
    return r
end

-- The cache's clearing hook: every built entry, the same-item fast path and the requirement maps go.
function T.invalidate()
    T.cache = {}
    T.last = nil
    T.R = {}
    T.stats.invalidations = T.stats.invalidations + 1
end

-- Register the invalidate hook on the view's listeners, once per listeners table. The closure lives on the
-- global NR_ClientTooltip_Hook and looks NutritionRevamp.client.tooltip up per call, so a reload of this file adds no second one.
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

-- The whole-item factor of a live Food: base hunger over the raw hunger left (lessons #2843); 1 when either is
-- 0 or unreadable, or when the ratio is below 1 (never shrink a never-eaten item).
function T.wholeScale(item)
    local base = num(read(item, "getBaseHunger"))
    local raw = num(read(item, "getHungChange"))
    if base == 0 or raw == 0 then return 1 end
    local s = base / raw
    if s < 1 then return 1 end
    return s
end

-- The item's NR_Nutrients default-modData string (the declared-nutrients contract, #2676), or nil.
function T.declaredOf(item)
    local md = read(item, "getModData")
    if type(md) ~= "table" then return nil end
    local v = md.NR_Nutrients
    if type(v) == "string" then return v end
    return nil
end

-- A row of K.view.tooltip as one band line: the label, then ": " and the text when the row has one.
function T.lineOf(row)
    local label = T.text(row.label)
    local txt = row.text
    if type(txt) ~= "string" or txt == "" then return label end
    if row.isKey then txt = T.text(txt) end
    return label .. ": " .. txt
end

-- The widest line in pixels (the band is drawn at least that wide); 0 when nothing measures.
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

-- The item's four whole-item macros at script scale (the live getters re-scaled by wholeScale).
function T.macrosOf(item)
    local s = T.wholeScale(item)
    return {
        calories = num(read(item, "getCalories")) * s,
        carbs = num(read(item, "getCarbohydrates")) * s,
        lipids = num(read(item, "getLipids")) * s,
        proteins = num(read(item, "getProteins")) * s,
    }
end

-- The cache key: fullType|declared|level|sex|cal|carb|lip|pro, each macro %.3f (never %d).
function T.keyOf(fullType, declared, level, sex, m)
    return fullType .. "|" .. tostring(declared) .. "|" .. tostring(level) .. "|" .. tostring(sex)
        .. string.format("|%.3f|%.3f|%.3f|%.3f", m.calories, m.carbs, m.lipids, m.proteins)
end

-- The band entry of one item: { lines, source } (lines.width the widest line in pixels, set beside the array
-- part), or nil for no item or a non-Food.
function T.entryFor(item)
    if item == nil then return nil end
    T.hook()
    local level = T.level()
    if read(item, "IsFood") ~= true then return nil end
    local fullType = read(item, "getFullType")
    if type(fullType) ~= "string" then return nil end
    local declared = T.declaredOf(item)
    local sex = T.sex()
    local macros = T.macrosOf(item)
    local key = T.keyOf(fullType, declared, level, sex, macros)
    local last = T.last
    if last ~= nil and last.item == item and last.key == key then
        T.stats.cacheHits = T.stats.cacheHits + 1
        return last.entry
    end
    local entry = T.cache[key]
    if entry ~= nil then
        T.stats.cacheHits = T.stats.cacheHits + 1
        T.last = { item = item, key = key, entry = entry }
        return entry
    end
    entry = T.build(item, fullType, declared, level, sex, macros)
    T.cache[key] = entry
    T.last = { item = item, key = key, entry = entry }
    return entry
end

-- Build one entry: the whole-item macros, the source chain, the item's own macros over the vector, the lines.
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
    local rows = K.view.tooltip(vec, source, level, nil, { R = T.requirements(sex), UNITS = units })
    local lines = {}
    for i = 1, #rows do
        lines[i] = T.lineOf(rows[i])
    end
    lines.width = T.widthOf(lines)
    T.stats.builds = T.stats.builds + 1
    return { lines = lines, source = source }
end

-- The band's lines for an item (the wrapper's per-frame call), or nil.
function T.linesFor(item)
    local entry = T.entryFor(item)
    if entry == nil then return nil end
    return entry.lines
end

-- The line step: the tooltip object's getLineSpacing, else LINE_SPACING.
function T.step(el)
    local s = read(el.tooltip, "getLineSpacing")
    if type(s) == "number" and s > 0 then return s end
    return T.LINE_SPACING
end

-- Draw the band below the engine's box, after the original returned: the option, the context-menu test again
-- (#2496), then the frame at the panel's colours, the lines, and the panel's height raised by the band (#2517).
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
    local bg = el.backgroundColor or T.BG
    local bd = el.borderColor or T.BORDER
    local font = nil
    if UIFont ~= nil then font = UIFont.Small end
    el:drawRect(0, y, w, band, bg.a, bg.r, bg.g, bg.b)
    el:drawRectBorder(0, y, w, band, bd.a, bd.r, bd.g, bd.b)
    for i = 1, n do
        el:drawText(lines[i], T.INSET, y + T.PAD / 2 + (i - 1) * step, 1, 1, 1, 1, font)
    end
    el:setHeight(y + band)
    T.stats.draws = T.stats.draws + 1
    T.stats.lines = T.stats.lines + n
    return true
end

-- The wrapper body after the original: the band under one pcall, a failure counted and kept.
function T.after(el, lines)
    local ok, err = pcall(T.band, el, lines)
    if not ok then
        T.stats.errors = T.stats.errors + 1
        T.lastError = tostring(err)
    end
end

-- TEST-ONLY, for the driver (`lua.call NutritionRevamp.client.tooltip.probe Base.Apple`, Task 11): the local
-- player's first inventory item of a full type, through ItemContainer.getFirstTypeRecurse(String) (jar 42.20.4
-- `ItemContainer.getFirstTypeRecurse(Ljava/lang/String;) @0 L1838`, a TypePredicate whose compareType matches a
-- dotted type against getFullType at `ItemContainer.compareType(String, InventoryItem) @23 L1419`), run through
-- the band's entry. Returns count, source (two scalars, so lua.call replies r1, r2); no item -> 0, "none".
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

-- The wrapper over one original: linesFor first under a pcall, the original exactly once, then the band.
local function makeWrapper(original)
    return function(self)
        local t = nil
        local nr = NutritionRevamp
        if nr ~= nil and nr.client ~= nil then t = nr.client.tooltip end
        local lines = nil
        if t ~= nil and t.linesFor ~= nil then
            local ok, l = pcall(t.linesFor, self.item)
            if ok then
                lines = l
            else
                t.stats.errors = t.stats.errors + 1
                t.lastError = tostring(l)
            end
        end
        original(self)
        if lines ~= nil and t.after ~= nil then t.after(self, lines) end
    end
end

-- The install (file scope): once per class table; a re-created ISToolTipInv is wrapped afresh.
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
