-- TKX_SSRead (X44) -- copies simpleStatus macro bar text into a global the harness reads.
-- Client only. The second require of an already-loaded file returns the first load value.
-- The four macro bars ship hidden, so file scope sets shown = true before OnCreatePlayer builds
-- the bar. prepareBarInfo is wrapped once (sentinel in the global TKX_SSRead_Installed) and the
-- original is called first, then each macro bar text is read from self.barInfo, whose rows are
-- { title, text, color, percent, type, name, ruler }.
TKX_SS = { calls = 0, calories = "", carbs = "", lipids = "", proteins = "" }

local okS, stats = pcall(require, "ss.stats")
local okB, SSBar = pcall(require, "ISSSBar")

local function install()
    if not okS or type(stats) ~= "table" then return end
    if not okB or type(SSBar) ~= "table" then return end
    if TKX_SSRead_Installed ~= nil then return end
    TKX_SSRead_Installed = true
    local names = { "calories", "carbohydrates", "lipids", "proteins" }
    local i = 1
    while i <= 4 do
        local bar = stats[names[i]]
        if type(bar) == "table" then bar.shown = true end
        i = i + 1
    end
    local original = SSBar.prepareBarInfo
    if original == nil then return end
    SSBar.prepareBarInfo = function(self, ...)
        local r = original(self, ...)
        TKX_SS.calls = TKX_SS.calls + 1
        local info = self.barInfo
        if type(info) == "table" then
            local j = 1
            while info[j] ~= nil do
                local row = info[j]
                local n = row[6]
                local t = row[2]
                if n == "calories" then TKX_SS.calories = tostring(t)
                elseif n == "carbohydrates" then TKX_SS.carbs = tostring(t)
                elseif n == "lipids" then TKX_SS.lipids = tostring(t)
                elseif n == "proteins" then TKX_SS.proteins = tostring(t) end
                j = j + 1
            end
        end
        return r
    end
end

install()
