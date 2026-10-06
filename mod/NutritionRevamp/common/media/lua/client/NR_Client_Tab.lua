-- NR_Client_Tab.lua -- the character-info tab (Plan 7 Task 7, ruling 9): one more tab on the vanilla
-- ISCharacterInfoWindow, built by wrapping three of its methods, drawing the view cache's rows.
-- UNMEASURED until x183: the shape follows AutoCook's worked tab (docs/superpowers/research/platform-client-ui.md
-- section C, verbatim, never run by this repo); a stand-in test proves the wiring and the guards, never the engine.
--
-- The three wraps, under ONE sentinel (#0935, #1067, #2844, #2845):
--  * createChildren: the original first, then the tab is built and added under pcall. The window is built on
--    Events.OnCreatePlayer, so the wrap is installed at file scope, before that event (#2521).
--  * onTabTornOff(view, window): the registration of the torn-off window comes first, the original LAST (as
--    AutoCook does); player 0 only, like vanilla's own five.
--  * SaveLayout(name, layout): the original first (it rebuilds layout.tabs and layout.current from its five
--    views), then the mod appends its name to layout.tabs when its view is a tab of the panel.
--
-- The restore gap, closed (ruling 9; #2502, #2521): vanilla's RestoreLayout reads
--   if layout.current and not floating[layout.current] then self.panel:activateView(xpSystemText[layout.current])
-- (install:client/XpSystem/ISUI/ISCharacterInfoWindow.lua:287), and xpSystemText has no entry for a mod tab, so
-- a saved layout.current of the mod's name would reach activateView(nil). SaveLayout therefore sets
-- layout.current to nil when the mod tab is the active one, and never to the mod's name. The cost: a window
-- saved on the mod tab reopens on its default tab.
--
-- Shape: the sentinel NR_ClientTab_Installed is a global of its own, never a field of NutritionRevamp, which
-- NR_Core re-creates on every load (#0943). It records the class table it wrapped and the three originals;
-- the file wraps again only when ISCharacterInfoWindow is not that class table (a re-created class), never
-- merely because the method is no longer the wrapper (lessons, the re-wrap rule). The wrappers name nothing
-- from this file's load: they look NutritionRevamp.client.tab up per call, so a reload swaps the logic under the
-- wraps that stay installed. Every Java and vanilla global is named only behind a nil check, so the file loads
-- with no engine. The load order is alphabetical (_Tab sorts after _Panel and before _Tooltip and _View): NR.client.view
-- and NR.client.text are looked up per call, never captured at file scope; with no view the tab draws nothing.
-- The tab's name is the translated string (#2503); nothing else names it. No keybind, and no request to the
-- server: the panel's open does that and this tab reads the stored mirror through the view cache.
-- Cadence: the render reads the view cache's refresh(false), which re-reads on its own cadence; no @fastpath.
-- The clip and the scroll (the close's D1): ISTabPanel does not clip its active view (ISTabPanel.lua:106 draws the
-- frame only), so the rows are drawn the panel's way (NR_Client_Panel.lua's renderBody and wheel): view.draw stops
-- before a line would pass the tab's height (maxY) and skips a row above the top inset (minY); the wheel moves
-- scrollY by WHEEL_LINES lines, clamped to the overflow (rows x line height - (height - 2 x PAD)). The base render
-- runs inside the render's one pcall.
local NR = NutritionRevamp
NR.client.tab = {
    stats = { added = 0, tornOff = 0, saves = 0, renders = 0, errors = 0, noView = 0 },
    cls = nil,
    lastError = nil,
}
local T = NR.client.tab

local TAB_ID = "NutritionRevamp"
local PAD = 8 -- px, the rows' inset from the tab's edges
local WHEEL_LINES = 3 -- rows one wheel notch scrolls (NR_Client_Panel.lua's step)

if ISPanelJoypad ~= nil then
    NR_Client_TabPanel = ISPanelJoypad:derive("NR_Client_TabPanel")
    T.cls = NR_Client_TabPanel

    function NR_Client_TabPanel:new(x, y, width, height, playerNum)
        local o = ISPanelJoypad.new(self, x, y, width, height)
        o.playerNum = playerNum
        o.scrollY = 0
        if o.noBackground ~= nil then o:noBackground() end
        return o
    end

    -- The base render and the rows, under one pcall (T.renderBody, looked up per call).
    function NR_Client_TabPanel:render()
        local tab = NutritionRevamp.client.tab
        tab.stats.renders = tab.stats.renders + 1
        local ok, err = pcall(tab.renderBody, self)
        if not ok then
            tab.stats.errors = tab.stats.errors + 1
            tab.lastError = tostring(err)
        end
    end

    -- The wheel scrolls the rows when they overflow the tab; true when it took the event.
    function NR_Client_TabPanel:onMouseWheel(del)
        local tab = NutritionRevamp.client.tab
        local ok, took = pcall(tab.wheel, self, del)
        if not ok then
            tab.stats.errors = tab.stats.errors + 1
            tab.lastError = tostring(took)
            return false
        end
        return took
    end
end

-- The rows' overflow in px: rows x line height - (height - 2 x PAD), never below 0.
function T.overflow(el, view, lh)
    local n = 0
    if view ~= nil and view.rows ~= nil then n = #view.rows end
    local h = el.height
    if type(h) ~= "number" then h = 0 end
    local over = n * lh - (h - 2 * PAD)
    if over < 0 then over = 0 end
    return over
end

-- The render body: the base render, the count, the scroll offset re-clamped, the rows clipped to the tab.
function T.renderBody(el)
    ISPanelJoypad.render(el)
    local tab = NutritionRevamp.client.tab
    local view = NutritionRevamp.client.view
    if view == nil then
        tab.stats.noView = tab.stats.noView + 1
        return
    end
    view.refresh(false)
    local font = nil
    if UIFont ~= nil then font = UIFont.Small end
    local over = T.overflow(el, view, view.lineHeight(font))
    local sy = el.scrollY or 0
    if sy > over then sy = over end
    if sy < 0 then sy = 0 end
    el.scrollY = sy
    view.draw(el, view.rows, PAD, PAD - sy, el.width - 2 * PAD, font, el.height, PAD)
end

-- The wheel: scrollY moves by WHEEL_LINES x line x del, clamped to [0, overflow]; true (the event taken) only when
-- there is overflow to scroll.
function T.wheel(el, del)
    local view = NutritionRevamp.client.view
    if type(del) ~= "number" or view == nil then return false end
    local font = nil
    if UIFont ~= nil then font = UIFont.Small end
    local lh = view.lineHeight(font)
    local over = T.overflow(el, view, lh)
    if over <= 0 then return false end
    local y = (el.scrollY or 0) + WHEEL_LINES * lh * del
    if y < 0 then y = 0 end
    if y > over then y = over end
    el.scrollY = y
    return true
end

local function failed(tab, err)
    tab.stats.errors = tab.stats.errors + 1
    tab.lastError = tostring(err)
end

-- The mod's part of each wrap: plain functions on NR.client.tab, read per call by the wrappers.
function T.afterCreate(win)
    local tab = NutritionRevamp.client.tab
    local ok, err = pcall(function()
        if tab.cls == nil then error("no panel class (ISPanelJoypad absent)") end
        win.nrView = NR_Client_TabPanel:new(0, 8, win.width, win.height - 8, win.playerNum)
        win.nrView:initialise()
        local text = NutritionRevamp.client.text
        local name = "Nutrition"
        if text ~= nil then name = text("UI_NR_Tab", "Nutrition") end
        win.panel:addView(name, win.nrView)
        tab.stats.added = tab.stats.added + 1
    end)
    if not ok then failed(tab, err) end
end

function T.beforeTornOff(win, view, window)
    local tab = NutritionRevamp.client.tab
    local ok, err = pcall(function()
        if win.playerNum == 0 and win.nrView ~= nil and view == win.nrView then
            if ISLayoutManager ~= nil and ISLayoutManager.RegisterWindow ~= nil and ISCollapsableWindow ~= nil then
                ISLayoutManager.RegisterWindow("charinfowindow." .. TAB_ID, ISCollapsableWindow, window)
            end
            tab.stats.tornOff = tab.stats.tornOff + 1
        end
    end)
    if not ok then failed(tab, err) end
end

function T.afterSave(win, layout)
    local tab = NutritionRevamp.client.tab
    local ok, err = pcall(function()
        if win.nrView ~= nil and win.panel ~= nil and win.nrView.parent == win.panel then
            if layout.tabs ~= nil and layout.tabs ~= "" then
                layout.tabs = layout.tabs .. "," .. TAB_ID
            else
                layout.tabs = TAB_ID
            end
            if win.panel.getActiveView ~= nil and win.panel:getActiveView() == win.nrView then
                layout.current = nil
            end
            tab.stats.saves = tab.stats.saves + 1
        end
    end)
    if not ok then failed(tab, err) end
end

-- The one install: once per class table.
if ISCharacterInfoWindow ~= nil and (NR_ClientTab_Installed == nil or NR_ClientTab_Installed.class ~= ISCharacterInfoWindow) then
    local inst = {
        class = ISCharacterInfoWindow,
        createChildren = ISCharacterInfoWindow.createChildren,
        onTabTornOff = ISCharacterInfoWindow.onTabTornOff,
        SaveLayout = ISCharacterInfoWindow.SaveLayout,
    }
    NR_ClientTab_Installed = inst

    function ISCharacterInfoWindow:createChildren()
        local r = inst.createChildren(self)
        NutritionRevamp.client.tab.afterCreate(self)
        return r
    end

    function ISCharacterInfoWindow:onTabTornOff(view, window)
        NutritionRevamp.client.tab.beforeTornOff(self, view, window)
        return inst.onTabTornOff(self, view, window)
    end

    function ISCharacterInfoWindow:SaveLayout(name, layout)
        local r = inst.SaveLayout(self, name, layout)
        NutritionRevamp.client.tab.afterSave(self, layout)
        return r
    end
end
