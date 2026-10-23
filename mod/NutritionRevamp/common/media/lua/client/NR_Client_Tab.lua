-- NR_Client_Tab.lua -- the character-info tab: one more tab on ISCharacterInfoWindow, built by wrapping three of its
-- methods under ONE sentinel (#0935), drawing the view cache's rows (docs/platform/client-ui.md). Its on-screen draw is
-- unmeasured (no click reaches the tab in the harness): a stand-in test proves the wiring, never the engine.
-- createChildren is wrapped at file scope, before Events.OnCreatePlayer builds the window (#2521).
-- The restore gap (#2502): vanilla's RestoreLayout looks layout.current up in xpSystemText, which has no entry for a
-- mod tab, so SaveLayout never saves the mod's name as current; a window saved on the mod tab reopens on its default.
-- The sentinel NR_ClientTab_Installed, a global (NR_Core re-creates NutritionRevamp, #0943), records the class table: it wraps again only for a re-created
-- class, never because the method is no longer the wrapper. The wrappers look NutritionRevamp.client.tab up per call.
-- ISTabPanel does not clip its active view, so the rows are drawn the panel's way, clipped by view.draw's minY and maxY.
local NR = NutritionRevamp
NR.client.tab = {
    stats = { added = 0, tornOff = 0, saves = 0, renders = 0, errors = 0, noView = 0 },
    cls = nil,
    lastError = nil,
}
local T = NR.client.tab

local TAB_ID = "NutritionRevamp"
local PAD = 8 -- px, the rows' inset from the tab's edges

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

    -- One pcall (T.renderBody, looked up per call).
    function NR_Client_TabPanel:render()
        local tab = NutritionRevamp.client.tab
        tab.stats.renders = tab.stats.renders + 1
        local ok, err = pcall(tab.renderBody, self)
        if not ok then
            tab.stats.errors = tab.stats.errors + 1
            tab.lastError = tostring(err)
        end
    end

    -- true when it took the event.
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

-- Never below 0.
function T.overflow(el, view, lh)
    local n = 0
    if view.rows ~= nil then n = #view.rows end
    local h = el.height
    if type(h) ~= "number" then h = 0 end
    return view.overflow(n, lh, h - 2 * PAD)
end

function T.renderBody(el)
    ISPanelJoypad.render(el)
    local tab = NutritionRevamp.client.tab
    local view = NutritionRevamp.client.view
    if view == nil then
        tab.stats.noView = tab.stats.noView + 1
        return
    end
    view.refresh(false)
    local font, lh = view.metrics()
    local sy = view.clampScroll(el.scrollY or 0, T.overflow(el, view, lh))
    el.scrollY = sy
    -- The window keeps the height the last vanilla view set, so the tab re-asserts its own each render, or its rows
    -- would paint past a window a shorter view left.
    if el.setHeightAndParentHeight ~= nil then el:setHeightAndParentHeight(el.height) end
    view.draw(el, view.rows, PAD, PAD - sy, el.width - 2 * PAD, font, el.height, PAD)
end

-- true (the event taken) only when there is overflow.
function T.wheel(el, del)
    local view = NutritionRevamp.client.view
    if type(del) ~= "number" or view == nil then return false end
    local _, lh = view.metrics()
    return view.scrollBy(el, del, T.overflow(el, view, lh))
end

local function failed(tab, err)
    tab.stats.errors = tab.stats.errors + 1
    tab.lastError = tostring(err)
end

-- Plain functions on NR.client.tab, read per call by the wrappers.
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
