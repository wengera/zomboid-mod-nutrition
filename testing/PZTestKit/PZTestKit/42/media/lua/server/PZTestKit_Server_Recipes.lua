-- PZTestKit server side, recipe half (slice 06).
--
-- Separate file from PZTestKit_Server.lua for the reason slice 03 split
-- `PZTestKit_Client_Body.lua` off the client file: two slices editing one file collide, and
-- nothing here needs to be near the bus. Lua files in one folder load alphabetically and
-- `.` sorts before `_`, so `PZTestKit_Server.lua` -- and with it the whole `TK` table, the
-- `OnTick`/`EveryOneMinute` poll and `TK.call` -- is already loaded when this file runs. It
-- registers into that same table and adds no hook of its own.
--
-- What lives here is the LIVE cross-check for `tools/recipe_scan.py`. The scanner parses
-- `media/scripts/**/*.txt` as text; `ScriptManager` holds what the game's own loader made of
-- those same files, and script data is loaded identically on both sides and never synced, so
-- the server's copy is the whole answer (the slice-05 `items.count` rule).
--
-- Kahlua rules, as everywhere in this harness: every Java member goes through `TK.call`
-- (which probes by indexing first -- "tried to call nil" is NOT catchable by pcall in PZ, see
-- the note above `TK.call` in the core), no `goto`, and `%d` on a float is fatal, so counts
-- are formatted with `%.0f`.
if not isServer() then return end

-- `getScriptManager` is checked for nil BEFORE it is called: a nil global raises the same
-- uncatchable "tried to call nil" and would take the poll handler with it rather than answer
-- the bus with an error. Same helper as `PZTestKit_Server.lua`'s; duplicated rather than
-- shared so this file stays self-contained and a parallel edit to the other one cannot
-- change what these commands do.
local function scriptManager()
    if getScriptManager == nil then return nil end
    return getScriptManager()
end

-- nil-safe `TK.call` that keeps a `false` result (`isCookable` legitimately answers false).
local function get(o, g, ...)
    if o == nil then return nil end
    local ok, v = TK.call(o, g, ...)
    if ok then return v end
    return nil
end

-- (list, size) for a list accessor, `(nil, 0)` when this build does not expose it -- the
-- slice-05 `listOf`. `size` is type-checked because `n - 1` on a nil would be an arithmetic
-- error inside the loop that follows every call.
local function listOf(o, method)
    local ok, all = TK.call(o, method)
    if not ok or all == nil then return nil, 0 end
    local _, n = TK.call(all, "size")
    return all, (type(n) == "number") and n or 0
end

-- What one list element answers to. MEASURED off the jar (42.20.4): a craft output's
-- `getPossibleResultItems()` yields `zombie.scripting.objects.Item`, which has
-- `getFullName()` (the `moduleDotType` field -- "Base.Toast"); an evolved recipe's
-- `getPossibleItems()` yields `zombie.scripting.objects.ItemRecipe`, which has **no**
-- `getFullName` and answers `getName()` / `getModule()` / `getFullType()` instead. So the
-- ladder below resolves to a full type on the craft side and to whatever `ItemRecipe.getName`
-- holds on the evolved side, and `collect` records the full type SEPARATELY rather than
-- leaving the reader to guess which rung answered.
local function label(o)
    local v = get(o, "getFullName") or get(o, "getName") or get(o, "getFullType")
    if v == nil then return tostring(o) end
    return tostring(v)
end

-- Written into `itemFullTypes` for an element that answered a label but no full type, so the
-- two lists stay index-for-index. A string no full type can be (`.` separates module from
-- type, and no module is empty), so a consumer that reads it as a type gets an obvious miss
-- rather than a plausible one.
local NO_FULL_TYPE = "?no-full-type"

-- java List -> (labels, size, fullTypes, err, aligned). The owner and the METHOD NAME rather
-- than the list, because a build that does not expose the getter and a getter that answered
-- an empty list both leave `labels` empty and they are different findings -- the slice-05
-- `fluidDefsError` rule. `err` is non-nil for exactly the first case; an empty list with a nil
-- `err` is a genuinely empty list.
--
-- Both lists are returned because the two element types spell a full type through different
-- members (see `label`): a Task-3 comparison against a scanned `Base.X` needs `fullTypes`, and
-- the brief's expectations are written against `labels`. They are kept INDEX-ALIGNED -- an
-- element that answers a label but no full type takes `NO_FULL_TYPE` in `fullTypes` rather
-- than being dropped, which would silently shift every pair after it -- and `aligned` is false
-- when that happened, so a caller can refuse the pairing instead of trusting it. An element
-- the list yielded as nil is skipped on BOTH sides (the two stay aligned with each other) and
-- is still counted in `size`, so a short list is visible against it rather than silently equal.
local function collect(owner, method)
    local labels, full = {}, {}
    if owner == nil then return labels, 0, full, "no object to ask " .. method .. "()", true end
    local ok, l = TK.call(owner, method)
    if not ok then return labels, 0, full, "no " .. method .. "() on this build", true end
    if l == nil then return labels, 0, full, method .. "() answered nil", true end
    local n = get(l, "size") or 0
    if type(n) ~= "number" then n = 0 end
    local aligned = true
    for i = 0, n - 1 do
        local v = get(l, "get", i)
        if v ~= nil then
            labels[#labels + 1] = label(v)
            local ft = get(v, "getFullType") or get(v, "getFullName")
            if ft ~= nil then
                full[#full + 1] = tostring(ft)
            else
                full[#full + 1] = NO_FULL_TYPE
                aligned = false
            end
        end
    end
    return labels, n, full, nil, aligned
end

-- Run each getter and report what happened to it, the slice-05 `missingGetters` pattern with
-- one addition. Three outcomes, and they are three different findings:
--   * absent    -> `missingGetters`: this build does not expose the member at all;
--   * raised    -> `getterErrors`:   the member is there and the CALL failed. This is why the
--                  pcall is here: `CraftRecipe.getTime` is overloaded (`()I` and
--                  `(IsoGameCharacter)I`) and Kahlua's dispatch could pick the arity we did
--                  not ask for. `TK.call` has already ruled out the uncatchable "tried to call
--                  nil", so what is left is exactly the catchable argument/overload mismatch --
--                  and a raise must cost that one key, never the whole reply;
--   * null      -> `nullGetters`:    the member answered, with nothing. Distinct from absent:
--                  a recipe with no `category` line is not a build without `getCategory`.
local function fields(o, getters)
    local t, missing, errs, nulls = {}, {}, {}, {}
    for i = 1, #getters do
        local g = getters[i]
        local ran, present, v = pcall(TK.call, o, g)
        if not ran then
            errs[#errs + 1] = g .. ": " .. tostring(present)
        elseif not present then
            missing[#missing + 1] = g
        elseif v == nil then
            nulls[#nulls + 1] = g
        else
            t[g] = v
        end
    end
    if #missing > 0 then t.missingGetters = missing end
    if #errs > 0 then t.getterErrors = errs end
    if #nulls > 0 then t.nullGetters = nulls end
    return t
end

-- Slice 05 measured that `ScriptManager.getFluidDefinitionScript` answers to both `Cola` and
-- `Base.Cola`. Whether the recipe accessors do the same is an open question of this slice, so
-- BOTH spellings are asked on every lookup and the answer travels in the reply as `lookup`
-- rather than being inferred from which call the command happened to make first. The recipe
-- used is the plain one when it answers, so a build where both work behaves exactly as the
-- brief's sketch does.
local function lookupRecipe(sm, method, want)
    local alternate
    if string.find(want, "%.") then
        alternate = string.gsub(want, "^[^%.]*%.", "")      -- Base.Salad -> Salad
    else
        alternate = "Base." .. want                          -- Salad -> Base.Salad
    end
    local plain = get(sm, method, want)
    local other = get(sm, method, alternate)
    local info = { accessor = method, asked = want, alternate = alternate,
                   askedAnswered = plain ~= nil, alternateAnswered = other ~= nil }
    if plain ~= nil then
        info.route = "as given"
        return plain, info
    end
    if other ~= nil then
        info.route = "module prefix toggled"
        return other, info
    end
    info.route = "none"
    return nil, info
end

-- ---- recipes.count -----------------------------------------------------------
-- The four script-inventory sizes `ScriptManager` exposes, read off the loaded game. The
-- dataset's `meta.counts.craftRecipes` / `legacyRecipeBlocks` come from `tools/recipe_scan.py`
-- reading the same files as text; these are the independent route to the same numbers.
--
-- An accessor this build does not expose and a genuinely empty list BOTH read 0, and they are
-- different findings -- the slice-05 `fluidDefsError` rule -- so a miss is named in
-- `missingAccessors` rather than left to look like a zero.
local COUNT_ACCESSORS = { { "craft", "getAllCraftRecipes" },
                          { "evolved", "getAllEvolvedRecipesList" },
                          { "legacy", "getAllRecipes" },
                          { "unique", "getAllUniqueRecipes" } }

TK.register("recipes.count", function()
    local sm = scriptManager()
    if sm == nil then return "no getScriptManager()" end
    local out, missing = {}, {}
    for i = 1, #COUNT_ACCESSORS do
        local key, method = COUNT_ACCESSORS[i][1], COUNT_ACCESSORS[i][2]
        local all, n = listOf(sm, method)
        out[key] = n
        if all == nil then missing[#missing + 1] = "ScriptManager:" .. method .. "()" end
    end
    if #missing > 0 then out.missingAccessors = missing end
    return out
end)

-- ---- recipes.evolved <name> --------------------------------------------------
-- One `EvolvedRecipe` read whole: its five scalar properties and the full list of items that
-- may be added to it. `getPossibleItems()` is the values of the recipe's own `itemsList` map,
-- so the list is the ingredient set and its size is the ingredient count.
--
-- That map is filled by `Item.OnScriptsLoaded` through BOTH of its arms, not just the obvious
-- one: the exact-name lookup `getEvolvedRecipe(key)` (`@43-@59 L3033-L3035`, case-SENSITIVE)
-- **and** a pass over every recipe whose `Template` `equalsIgnoreCase` the key
-- (`@122-@140 L3039`, case-INSENSITIVE). An item writing `EvolvedRecipe = Salad:10` therefore
-- registers against `Salad` by name *and* against every recipe templated `Salad`. `SaladClay`
-- is the case that proves it matters: no item writes a `SaladClay` key at all, so its whole
-- list arrives through the Template arm -- a reader who expects only the name arm would
-- predict an empty list and read 189.
local EVOLVED_GETTERS = { "getBaseItem", "getResultItem", "getMaxItems", "isCookable",
                          "getMinimumWater" }

TK.register("recipes.evolved", function(argv)
    local want = tostring(argv[1] or "")
    if want == "" then return "usage: recipes.evolved <name>" end
    local sm = scriptManager()
    if sm == nil then return "no getScriptManager()" end
    local r, lookup = lookupRecipe(sm, "getEvolvedRecipe", want)
    if r == nil then return "no evolved recipe " .. want end
    local out = fields(r, EVOLVED_GETTERS)
    out.name, out.lookup = want, lookup
    local items, n, full, ierr, aligned = collect(r, "getPossibleItems")
    out.items, out.ingredientCount, out.itemFullTypes = items, n, full
    -- absent getter vs empty list, and the pairing of the two lists: both are findings, so
    -- both are named rather than left to look like a short list (see `collect`).
    if ierr ~= nil then out.itemsError = ierr end
    if not aligned then out.itemFullTypesAligned = false end
    return out
end)

-- ---- recipes.craft <name> ----------------------------------------------------
-- One `CraftRecipe`: the four scalars the dataset can be compared against field for field,
-- plus every output line with its integer amount and the items it can resolve to.
--
-- `getPossibleResultItems()` goes through the output's `OutputMapper`. A plain `item 1
-- Base.Toast` line still has one -- `OutputScript.Load @310-@334` builds an `OutputMapper` and
-- calls `setDefaultOutputEntree` with the type -- so the list is populated for mapped and
-- unmapped outputs alike; it is only an output with a NULL mapper that answers empty (and
-- logs its own warning). `getOriginalLine()` is the recipe file's own text for that line,
-- which is the dataset's `outputs[].raw`: a direct string cross-check that does not depend on
-- the scanner and the game agreeing about how to parse it.
--
-- `getInputCount()` is NOT the number of input lines, and a comparison that assumes it is will
-- disagree with a flat scan on every recipe that uses a sub-line. `CraftRecipe.LoadIO` attaches
-- a `-` prefixed line inside an `inputs` block to the PRECEDING input as its
-- `consumeFromItemScript` (`@218-@317 L589-L604`) and a `+` one as `createToItemScript`
-- (`@122-@215 L574-L588` -- a separate, earlier arm, not part of the same span); both go into
-- `ioLines` and NEITHER into `inputs`, and `getInputCount()` is `inputs.size()`
-- (`@0-@7 L257`). 55 shipped lines are sub-lines.
local CRAFT_GETTERS = { "getCategory", "getTime", "getInputCount", "getOutputCount" }

TK.register("recipes.craft", function(argv)
    local want = tostring(argv[1] or "")
    if want == "" then return "usage: recipes.craft <name>" end
    local sm = scriptManager()
    if sm == nil then return "no getScriptManager()" end
    local r, lookup = lookupRecipe(sm, "getCraftRecipe", want)
    if r == nil then return "no craft recipe " .. want end
    local out = fields(r, CRAFT_GETTERS)
    out.name, out.lookup, out.outputs = want, lookup, {}
    local outs, n = listOf(r, "getOutputs")
    -- `getOutputs()` absent and an empty output block both leave `outputs` empty, and 26 of the
    -- 969 recipes genuinely have an empty block, so say which this is.
    if outs == nil then out.outputsError = "no CraftRecipe:getOutputs()" end
    out.outputListSize = n
    for i = 0, n - 1 do
        local o = get(outs, "get", i)
        if o ~= nil then
            local items, cnt, full, ierr, aligned = collect(o, "getPossibleResultItems")
            local rt = get(o, "getResourceType")
            local orow = {
                index = i,
                amount = get(o, "getIntAmount"),
                resourceType = (rt ~= nil) and tostring(rt) or nil,
                originalLine = get(o, "getOriginalLine"),
                items = items, itemCount = cnt, itemFullTypes = full }
            -- same two findings as the evolved half: an absent getter is not an empty mapper,
            -- and a short `itemFullTypes` must never be read as a re-ordered one.
            if ierr ~= nil then orow.itemsError = ierr end
            if not aligned then orow.itemFullTypesAligned = false end
            out.outputs[#out.outputs + 1] = orow
        end
    end
    return out
end)

TK.log("recipe commands loaded")
