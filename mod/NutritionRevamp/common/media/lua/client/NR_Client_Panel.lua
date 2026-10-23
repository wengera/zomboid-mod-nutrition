-- NR_Client_Panel.lua -- the collapsible nutrition panel, an ISCollapsableWindow per player number, hidden and OFF the
-- UI manager until the key opens it (#2469: an element off the manager is neither updated nor rendered). Player 0's
-- geometry lives in layout.ini via ISLayoutManager.RegisterWindow, never in modData (#2473). Opening sends the one
-- client request; the rows redraw from NR.client.view, which rebuilds only when the mirror or the level moved (#2692).
-- The panel is instantiated BEFORE RegisterWindow: its restore can call collapse(), which needs collapseButton (#2470).
-- A non-resizable window's size is not restored from layout.ini, so the height is the mod's: it follows the rows,
-- capped at the screen, and the wheel scrolls past the cap. The shapes and their risks: docs/platform/client-ui.md.
-- The sentinel NR_ClientPanel_Installed holds the three listener closures and the instances, so a reload adds no
-- second listener and loses no window; every handler body runs under one pcall.
local NR = NutritionRevamp

NR_ClientPanel_Installed = NR_ClientPanel_Installed or {}
NR_ClientPanel_Installed.instances = NR_ClientPanel_Installed.instances or {}

NR.client.panel = {
    cls = nil,
    instances = NR_ClientPanel_Installed.instances,
    stats = { opens = 0, closes = 0, fits = 0, renders = 0, requests = 0, requestFailures = 0, creates = 0, registers = 0,
              keyPresses = 0, errors = 0, restoredVisible = nil },
    lastError = nil,
}
local PANEL = NR.client.panel

local LAYOUT_NAME = "NutritionRevamp.panel" -- the layout.ini window name
local WIDTH = 280 -- px, the panel's fixed size
local HEIGHT = 320 -- px, the first height before any rebuild sizes the panel to its rows
local SCREEN_DEFAULT = 600 -- px, the screen height when getPlayerScreenHeight is absent or raises

local START_X = 60 -- px, the first-sight position before any layout.ini restore
local START_Y = 200 -- px
local PAD = 8 -- px, the row inset from the frame
local TITLE_GAP = 4 -- px below the title bar

local call = NR.try

local function fail(err)
    NR.fail(NutritionRevamp.client.panel, "panel", err)
end

if ISCollapsableWindow ~= nil and type(ISCollapsableWindow.derive) == "function" then
    local okD, cls = pcall(ISCollapsableWindow.derive, ISCollapsableWindow, "NR_Client_Panel")
    if okD and cls ~= nil then
        NR_Client_Panel = cls
        PANEL.cls = cls

        function cls:new(x, y, w, h, playerNum)
            local o = ISCollapsableWindow.new(self, x, y, w, h)
            o.playerNum = playerNum
            local tx = NutritionRevamp.client.text
            if tx ~= nil then o.title = tx("UI_NR_PanelTitle", "Nutrition") else o.title = "Nutrition" end
            o.scrollY = 0
            o.overflowPx = 0
            o.resizable = false
            return o
        end

        -- The one compare: the view rebuilds only when the mirror's counter or the level moved.
        function cls:prerender()
            local base = ISCollapsableWindow
            if base ~= nil and base.prerender ~= nil then
                local ok, err = pcall(base.prerender, self)
                if not ok then fail(err) end
            end
            local nr = NutritionRevamp
            if nr.client.view ~= nil and nr.client.view.refresh ~= nil then
                pcall(nr.client.view.refresh, false)
            end
            local okF, errF = pcall(nr.client.panel.fit, self)
            if not okF then fail(errF) end
        end

        -- true when it took the event.
        function cls:onMouseWheel(del)
            local ok, took = pcall(NutritionRevamp.client.panel.wheel, self, del)
            if not ok then fail(took) return false end
            return took
        end

        -- A drag ends on release: the height is refit at the new top.
        function cls:onMouseUp(x, y)
            return NutritionRevamp.client.panel.release(self, ISCollapsableWindow.onMouseUp, x, y)
        end

        function cls:onMouseUpOutside(x, y)
            return NutritionRevamp.client.panel.release(self, ISCollapsableWindow.onMouseUpOutside, x, y)
        end

        -- The title bar's X takes the hide path, so the panel leaves the UI manager (#2469).
        function cls:close()
            local ok, err = pcall(NutritionRevamp.client.panel.hide, self)
            if not ok then fail(err) end
        end

        function cls:render()
            local ok, err = pcall(NutritionRevamp.client.panel.renderBody, self)
            if not ok then fail(err) end
        end
    end
end

function PANEL.hide(p)
    local P = NutritionRevamp.client.panel
    local _, vis = call(p, "getIsVisible")
    if vis ~= true then return false end
    call(p, "setVisible", false)
    call(p, "removeFromUIManager")
    P.stats.closes = P.stats.closes + 1
    return true
end

local function screenHeight(pn)
    if getPlayerScreenHeight == nil then return SCREEN_DEFAULT end
    local ok, h = pcall(getPlayerScreenHeight, pn)
    if ok and type(h) == "number" and h > 0 then return h end
    return SCREEN_DEFAULT
end

-- Once per rebuild and again after a drag or a resolution change; the rows that do not fit count once in
-- view.stats.overflowRows.
function PANEL.fit(self)
    local nr = NutritionRevamp
    local V = nr.client.view
    if V == nil or V.rows == nil or V.stats == nil then return false end
    if self.fitStamp == V.stats.rebuilds then return false end
    self.fitStamp = V.stats.rebuilds
    local _, th = call(self, "titleBarHeight")
    if type(th) ~= "number" then th = 16 end -- px, the title bar's floor when unread
    local _, y = call(self, "getY")
    if type(y) ~= "number" then y = 0 end
    local _, lh = V.metrics()
    local n = #V.rows
    local want = th + TITLE_GAP + n * lh + TITLE_GAP
    local cap = screenHeight(self.playerNum) - y
    local h = want
    if h > cap then h = cap end
    if h < th then h = th end
    call(self, "setHeight", h)
    local room = h - th - 2 * TITLE_GAP
    local fit = math.floor(room / lh)
    if fit < 0 then fit = 0 end
    local over = n - fit
    if over < 0 then over = 0 end
    V.stats.overflowRows = over
    self.titleH = th -- the render's title bar height, read here once per fit
    self.overflowPx = V.overflow(n, lh, room)
    self.scrollY = V.clampScroll(self.scrollY, self.overflowPx)
    nr.client.panel.stats.fits = nr.client.panel.stats.fits + 1
    return true
end

-- After a drag, the fit stamp is dropped so the next prerender refits under the cap at the new top.
function PANEL.release(self, base, x, y)
    local moved = self.moving == true
    local answer = nil
    if base ~= nil then
        local ok, v = pcall(base, self, x, y)
        if ok then answer = v else fail(v) end
    end
    if moved then self.fitStamp = nil end
    return answer
end

function PANEL.onResolutionChange()
    local P = NutritionRevamp.client.panel
    local V = NutritionRevamp.client.view
    if V ~= nil and V.onResolutionChange ~= nil then V.onResolutionChange() end
    for _, p in pairs(P.instances) do
        p.fitStamp = nil
    end
end

function PANEL.wheel(self, del)
    return NutritionRevamp.client.view.scrollBy(self, del, self.overflowPx or 0)
end

function PANEL.renderBody(self)
    local nr = NutritionRevamp
    local P = nr.client.panel
    local base = ISCollapsableWindow
    if base ~= nil and base.render ~= nil then base.render(self) end
    P.stats.renders = P.stats.renders + 1
    if self.isCollapsed then return end
    local V = nr.client.view
    if V == nil or V.rows == nil or V.draw == nil then return end
    local th, w, h = self.titleH, self.width, self.height -- ISUIElement's fields; the title bar's is kept by fit
    if type(th) ~= "number" then th = 16 end -- px, ISCollapsableWindow.TitleBarHeight's floor when unread
    if type(w) ~= "number" then w = WIDTH end
    if type(h) ~= "number" then h = HEIGHT end
    V.draw(self, V.rows, PAD, th + TITLE_GAP - (self.scrollY or 0), w - 2 * PAD, nil, h, th + TITLE_GAP)
end

-- A respawn's second create removes the old instance first; player 0's restore may re-add it.
function PANEL.onCreatePlayer(playerNum, player)
    local nr = NutritionRevamp
    local P = nr.client.panel
    if not nr.isClient() then return end
    local cls = P.cls
    if cls == nil then return end
    local pn = playerNum
    if type(pn) ~= "number" then pn = 0 end
    local old = P.instances[pn]
    if old ~= nil then
        call(old, "setVisible", false)
        call(old, "removeFromUIManager")
        P.instances[pn] = nil
    end
    local p = cls:new(START_X, START_Y, WIDTH, HEIGHT, pn)
    call(p, "initialise")
    call(p, "instantiate") -- before RegisterWindow: its restore's collapse() needs collapseButton
    call(p, "setResizable", false)
    call(p, "setRenderThisPlayerOnly", pn)
    call(p, "setVisible", false)
    P.instances[pn] = p
    P.stats.creates = P.stats.creates + 1
    if pn ~= 0 then return end
    if ISLayoutManager == nil or type(ISLayoutManager.RegisterWindow) ~= "function" then return end
    local okR, err = pcall(ISLayoutManager.RegisterWindow, LAYOUT_NAME, ISCollapsableWindow, p)
    if not okR then
        fail(err)
        return
    end
    P.stats.registers = P.stats.registers + 1
    local okV, vis = call(p, "getIsVisible")
    if okV then P.stats.restoredVisible = vis == true end
end

local function toggleBody(pn)
    local nr = NutritionRevamp
    local P = nr.client.panel
    local p = P.instances[pn]
    if p == nil then return false end
    local _, vis = call(p, "getIsVisible")
    if vis == true then
        PANEL.hide(p)
        return false
    end
    call(p, "addToUIManager")
    call(p, "setVisible", true)
    call(p, "bringToTop")
    P.stats.opens = P.stats.opens + 1
    local sent = false
    if nr.client.requestMirror ~= nil then
        local okS, s = pcall(nr.client.requestMirror)
        sent = okS and s == true
    end
    if sent then
        P.stats.requests = P.stats.requests + 1
    else
        P.stats.requestFailures = P.stats.requestFailures + 1
    end
    return true
end

-- A plain function the driver calls: true when the panel is now open.
function PANEL.toggle(playerNum)
    local pn = playerNum
    if type(pn) ~= "number" then pn = tonumber(pn) or 0 end
    local ok, open = pcall(toggleBody, pn)
    if not ok then
        fail(open)
        return false
    end
    return open
end

function PANEL.onKey(key)
    local nr = NutritionRevamp
    local P = nr.client.panel
    if not nr.isClient() then return end
    local want = nil
    local m = nr.client.modOptions
    if m ~= nil and m.key ~= nil then
        local okK, k = pcall(m.key)
        if okK and type(k) == "number" then want = k end
    end
    if want == nil then return end
    if key ~= want then return end
    P.stats.keyPresses = P.stats.keyPresses + 1
    P.toggle(0)
end

local S = NR_ClientPanel_Installed
if S.create == nil and Events ~= nil and Events.OnCreatePlayer ~= nil then
    S.create = function(playerNum, player)
        local nr = NutritionRevamp
        if nr == nil or nr.client == nil or nr.client.panel == nil then return end
        local ok, err = pcall(nr.client.panel.onCreatePlayer, playerNum, player)
        if not ok then fail(err) end
    end
    Events.OnCreatePlayer.Add(S.create)
end
if S.resolution == nil and Events ~= nil and Events.OnResolutionChange ~= nil then
    S.resolution = function()
        local nr = NutritionRevamp
        if nr == nil or nr.client == nil or nr.client.panel == nil then return end
        local ok, err = pcall(nr.client.panel.onResolutionChange)
        if not ok then fail(err) end
    end
    Events.OnResolutionChange.Add(S.resolution)
end
if S.key == nil and Events ~= nil and Events.OnKeyPressed ~= nil then
    S.key = function(key)
        local nr = NutritionRevamp
        if nr == nil or nr.client == nil or nr.client.panel == nil then return end
        local ok, err = pcall(nr.client.panel.onKey, key)
        if not ok then fail(err) end
    end
    Events.OnKeyPressed.Add(S.key)
end
