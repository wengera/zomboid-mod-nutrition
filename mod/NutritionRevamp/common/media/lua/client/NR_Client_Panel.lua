-- NR_Client_Panel.lua -- the collapsible nutrition panel (Plan 7 Task 5, ruling 6): NR_Client_Panel derives
-- ISCollapsableWindow (movable and collapsible for free, #2467-#2471), one instance per player number built on
-- OnCreatePlayer, hidden and OFF the UI manager until the key opens it (#2469: an element off the manager is
-- neither updated nor rendered); player 0's is registered with ISLayoutManager.RegisterWindow("NutritionRevamp.panel",
-- ISCollapsableWindow, p), so its geometry lives in layout.ini and never in modData (#2473-#2476, #2518).
-- Opening sends NR.client.requestMirror() -- the spec's one client request (§ 4.8) -- and the panel redraws its rows
-- from NR.client.view, which rebuilds only when NR.client.received or the level moved (#2692): prerender makes the
-- one compare, render walks the cached rows, and nothing here reads the mirror.
-- The vanilla shapes read (READ-ONLY, media/lua/client/ISUI on 42.20.4): ISCollapsableWindow:new(x, y, w, h) :366,
-- prerender :152, render :179 (it clears the stencil prerender set, so the rows are clipped to the panel's height by
-- view.draw's maxY), titleBarHeight :298, setResizable :326; ISLayoutManager.RegisterWindow :6 restores at
-- registration, and DefaultRestoreWindow :45-47 calls addToUIManager + setVisible(true) when layout.ini says
-- visible=true.
--
-- The research's minimal shape 1, read in x183:
--  risk 1: the restore re-adds the panel visible before the key was ever pressed -- the first registration
--          measured (#3215); a saved visible=true line's restore unmeasured. stats.restoredVisible records
--          p:getIsVisible() right after RegisterWindow. The panel is instantiated BEFORE the registration (the
--          close's D3): RegisterWindow restores at once, and a saved pin=false visible=false line's RestoreLayout
--          calls collapse(), which indexes collapseButton (ISCollapsableWindow.lua:343-346), a child instantiate
--          builds (#2470); NR_Client_Moodles.lua instantiates its column the same way;
--  risk 2: whether layout.ini is written on the harness client's exit path -- measured in x183 (#3216 the layout write at the quit; #3218 the load 1 / 0 failures);
--  risk 3: whether PZAPI.ModOptions:load() at OnGameStart finds ModOptions.ini -- measured in x183 (#3216 the layout write at the quit; #3218 the load 1 / 0 failures).
-- The default key is the semicolon (code 39): `;` is unbound in shared/keyBinding.lua and read by no media/lua/client
-- handler outside debug files; K is vanilla's Display FPS at keyBinding.lua:198 (NR_Client_ModOptions.lua's header).
-- The height follows the rows (ruling T5-2): at each rebuild the panel is titleBarHeight + 4 + rows * line + 4 tall,
-- capped at the screen below its top; past the cap the mouse wheel scrolls (a non-resizable window's width and
-- height are not restored from layout.ini, ISCollapsableWindow.RestoreLayout :337-340, so the height is the mod's).
--
-- Shape (NR_Client_Effects.lua's discipline): the class is derived only when ISCollapsableWindow exists (else
-- NR.client.panel.cls stays nil and toggle answers false); the sentinel NR_ClientPanel_Installed is a global of its
-- own holding the two listener closures (OnCreatePlayer, OnKeyPressed) and the instances, so a reload of this file or
-- of NR_Core adds no second listener and loses no window; the closures look NutritionRevamp.client.panel up per call;
-- every toolkit member is reached index-first inside a pcall; every handler body runs under one pcall; the file
-- loads with no engine (testing/tests/kernel/test_client_panel_shape.py).
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

local LAYOUT_NAME = "NutritionRevamp.panel" -- the layout.ini window name (ruling 6)
local WIDTH = 280 -- px, the panel's fixed size (plan Task 5 amendments)
local HEIGHT = 320 -- px, the first height before any rebuild sizes the panel to its rows
local SCREEN_DEFAULT = 600 -- px, the screen height when getPlayerScreenHeight is absent or raises
local WHEEL_LINES = 3 -- rows one wheel notch scrolls
local START_X = 60 -- px, the first-sight position before any layout.ini restore
local START_Y = 200 -- px
local PAD = 8 -- px, the row inset from the frame
local TITLE_GAP = 4 -- px below the title bar (plan Task 5)

-- One method of el, index-first inside a pcall: (ok, result).
local function call(el, name, ...)
    local ok, present, v = pcall(NR.call, el, name, ...)
    return ok and present, v
end

local function fail(err)
    local nr = NutritionRevamp
    local P = nr.client.panel
    P.stats.errors = P.stats.errors + 1
    P.lastError = err
    nr.log.say(2, "panel: " .. tostring(err))
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

        -- The frame, then the one compare (the view rebuilds only when the mirror's counter or the level moved).
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

        -- The wheel scrolls the rows when they overflow the capped height; true when it took the event.
        function cls:onMouseWheel(del)
            local ok, took = pcall(NutritionRevamp.client.panel.wheel, self, del)
            if not ok then fail(took) return false end
            return took
        end

        -- The title bar's X: the toggle's hide path, so the panel leaves the UI manager (#2469) and counts a close.
        function cls:close()
            local ok, err = pcall(NutritionRevamp.client.panel.hide, self)
            if not ok then fail(err) end
        end

        -- The frame, then the cached rows from below the title bar, unless collapsed.
        function cls:render()
            local ok, err = pcall(NutritionRevamp.client.panel.renderBody, self)
            if not ok then fail(err) end
        end
    end
end

-- The hide path: hidden and off the UI manager, one close counted; false when already hidden.
function PANEL.hide(p)
    local P = NutritionRevamp.client.panel
    local _, vis = call(p, "getIsVisible")
    if vis ~= true then return false end
    call(p, "setVisible", false)
    call(p, "removeFromUIManager")
    P.stats.closes = P.stats.closes + 1
    return true
end

-- The screen height for player pn, guarded; SCREEN_DEFAULT on any failure.
local function screenHeight(pn)
    if getPlayerScreenHeight == nil then return SCREEN_DEFAULT end
    local ok, h = pcall(getPlayerScreenHeight, pn)
    if ok and type(h) == "number" and h > 0 then return h end
    return SCREEN_DEFAULT
end

-- Sizes the panel to the view's rows once per rebuild (stamped on the view's rebuild count): the height is
-- titleBarHeight + TITLE_GAP + rows * line + TITLE_GAP, capped at the screen height below the panel's top; the rows
-- that do not fit count once in view.stats.overflowRows, and the scroll offset is re-clamped.
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
    local lh = V.lineHeight(V.smallFont())
    local n = #V.rows
    local want = th + TITLE_GAP + n * lh + TITLE_GAP
    local cap = screenHeight(self.playerNum) - y
    local h = want
    if h > cap then h = cap end
    call(self, "setHeight", h)
    local room = h - th - 2 * TITLE_GAP
    local fit = math.floor(room / lh)
    if fit < 0 then fit = 0 end
    local over = n - fit
    if over < 0 then over = 0 end
    V.stats.overflowRows = over
    self.overflowPx = n * lh - room
    if self.overflowPx < 0 then self.overflowPx = 0 end
    if self.scrollY > self.overflowPx then self.scrollY = self.overflowPx end
    nr.client.panel.stats.fits = nr.client.panel.stats.fits + 1
    return true
end

-- The wheel: scrollY moves by WHEEL_LINES * line * del, clamped to [0, overflowPx]; true (the event taken) only when
-- there is overflow to scroll.
function PANEL.wheel(self, del)
    if type(del) ~= "number" or (self.overflowPx or 0) <= 0 then return false end
    local V = NutritionRevamp.client.view
    local y = (self.scrollY or 0) + WHEEL_LINES * V.lineHeight(V.smallFont()) * del
    if y < 0 then y = 0 end
    if y > self.overflowPx then y = self.overflowPx end
    self.scrollY = y
    return true
end

-- The render body: the base render, the count, the rows from the scroll offset down to the panel's height.
function PANEL.renderBody(self)
    local nr = NutritionRevamp
    local P = nr.client.panel
    local base = ISCollapsableWindow
    if base ~= nil and base.render ~= nil then base.render(self) end
    P.stats.renders = P.stats.renders + 1
    if self.isCollapsed then return end
    local V = nr.client.view
    if V == nil or V.rows == nil or V.draw == nil then return end
    local _, th = call(self, "titleBarHeight")
    local _, w = call(self, "getWidth")
    local _, h = call(self, "getHeight")
    if type(th) ~= "number" then th = 16 end -- px, ISCollapsableWindow.TitleBarHeight's floor when unread
    if type(w) ~= "number" then w = WIDTH end
    if type(h) ~= "number" then h = HEIGHT end
    V.draw(self, V.rows, PAD, th + TITLE_GAP - (self.scrollY or 0), w - 2 * PAD, nil, h, th + TITLE_GAP)
end

-- OnCreatePlayer: one hidden instance per player number, off the UI manager; a second create for the same number (a
-- respawn) removes the old one first; player 0's registers with the layout manager, whose restore may re-add it.
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
    call(p, "instantiate") -- before RegisterWindow: its restore's collapse() needs collapseButton (D3)
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

-- Opens a hidden panel (onto the UI manager, visible, on top, one mirror request) or closes a visible one (hidden,
-- off the manager). A plain function the driver calls (lua.call NutritionRevamp.client.panel.toggle 0): true when
-- the panel is now open, false when it closed or there is none.
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

-- OnKeyPressed: the page's bind (NR.client.modOptions.key(), default semicolon) toggles player 0's panel; any other key does
-- nothing.
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
if S.key == nil and Events ~= nil and Events.OnKeyPressed ~= nil then
    S.key = function(key)
        local nr = NutritionRevamp
        if nr == nil or nr.client == nil or nr.client.panel == nil then return end
        local ok, err = pcall(nr.client.panel.onKey, key)
        if not ok then fail(err) end
    end
    Events.OnKeyPressed.Add(S.key)
end
