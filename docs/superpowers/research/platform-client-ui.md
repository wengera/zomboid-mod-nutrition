# Client UI platform — desk read

Read 2026-09-27 against the 42.20.4 install (`D:\SteamLibrary\steamapps\common\ProjectZomboid`, jar `b0bbce05d5`), its `media/lua` tree, and the installed workshop corpus (182 items, dated sweep 2026-09-27). Nothing was booted. Every statement is a reading of code on disk or of the jar through `C:\Users\Angus\pz-b42\pz.sh`, and is graded C.

Cite forms: `install:` = a path under `D:\SteamLibrary\steamapps\common\ProjectZomboid\media\lua`; `jar:Class.method @off L<n>`; `ws:<item-id>/mods/<Mod>/<version>/…` for the workshop tree. Java access flags came from a scratch constant-pool parser rebuilt over `pz-b42/tools/cp.py` this session, per [jar-research](../../platform/jar-research.md)'s rule.

The moodle stack and `MoodleFramework` are the sibling report [moodleframework-desk-read.md](moodleframework-desk-read.md); this report does not repeat them and names the one new reading it adds (`MoodlesUI` as a geometry anchor).

## Summary for the design

All four surfaces the design wants are reachable without shadowing one vanilla Lua file, and three of the four need only a method wrap installed from the mod's own uniquely-named `media/lua/client/` file.

The panel is the easy part: `ISCollapsableWindow` (`ISPanel` → `ISUIElement`) already ships the title bar, the close button, the resize widgets, the drag handler and the pin/collapse pair, so "movable and collapsible" is inherited rather than written, and `ISUIElement:wrapInCollapsableWindow(title, resizable)` turns a bare content panel into one in a single call.

Position persistence has a vanilla route the design should prefer over player modData: `ISLayoutManager.RegisterWindow(name, funcs, target)` restores geometry immediately at registration and saves it into the user-dir `layout.ini`, sectioned by screen resolution — and `ISCollapsableWindow` already supplies the `RestoreLayout`/`SaveLayout` functions that route needs, including the collapsed state.

The cost of that route is its cadence: `layout.ini` is written only from `Events.OnPostSave`, and on a client both `OnPostSave` trigger sites sit in the exit path of `IngameState.updateInternal`, so geometry is persisted at quit or disconnect and a hard crash loses it — which is exactly why `simpleStatus` instead writes its position to player modData on every mouse-up, at the price of a `transmitModData()` per drag and therefore of the library's wipe-and-replace hazard (#1151).

The keybind has two vanilla surfaces and the design should use the second: inserting a `{value=…, key=…}` row into the global `keyBinding` table before `Events.OnMainMenuEnter` puts a rebindable entry on the main Keybinding page and persists it in `keysB42.ini`, while `PZAPI.ModOptions:create(id, name):addKeyBind(id, label, defaultKey, tooltip)` puts it on the Mods options page and persists it in `ModOptions.ini` — the latter is a shipped vanilla API at `install:client/PZAPI/ModOptions.lua`, has no Java half at all (the literal `ModOptions` is absent jar-wide), and carries the whole options widget set beside the key.

`PZAPI.ModOptions` has one trap the design must handle: vanilla calls `PZAPI.ModOptions:load()` only from `MainOptions:addModOptionsPanel()`, so a player who never opens the options screen in this session runs with the defaults; `CleanUI` works around it by calling `PZAPI.ModOptions:load()` itself, once, inside a `pcall`, and the nutrition mod should copy that.

The food tooltip is the constrained one: the entire tooltip body is built in Java by `InventoryItem.DoTooltipEmbedded`, and the only Lua seam is `ISToolTipInv:render`, which calls `self.item:DoTooltip(self.tooltip)` twice per frame — once with `setMeasureOnly(true)` to size the panel and once to draw — so a mod appends lines by wrapping that one method and drawing into the space it makes, not by extending a layout the engine hands it.

Wrapping it covers every tooltip in the game that shows an inventory item, because all ten construction sites funnel through the one class; the separate crafting item-slot route is `ISItemSlot.drawTooltip(_itemSlot, _tooltip)`, a plain Lua function and a second clean wrap point.

`CleanUI` does not interfere: it replaces 43 files at vanilla relative paths, including both of the tooltip's call sites (`ISInventoryPane.lua`, `ISInventoryPaneContextMenu.lua`), but it ships no `ISToolTipInv.lua` and no copy of any `ISUI` base class, and its own copies still construct `ISToolTipInv` — so a wrap of `ISToolTipInv.render` survives CleanUI, while a wrap of `ISInventoryPane:doTooltip` would not.

Two traps sit inside `ISToolTipInv:render` for the wrapper: the whole body is inside a "no visible context menu" guard, so a naive post-call draw paints text with no tooltip behind it while a context menu is up; and under CleanUI a multi-item stack is represented by one display item plus `tooltip:setWeightOfStack(w)`, so the wrap sees a representative item rather than the group.

The vanilla nutrition block the design will sit beside is gated three ways, not one: `Food.DoTooltip` shows it when `Core.debug` is on with the `tooltipInfo` debug option, or on an internal flag, or when the character holds `CharacterTrait.NUTRITIONIST` or `NUTRITIONIST2` — so on the harness client (which runs `-debug`) the block can appear without the trait, which is a real false-positive risk for any test that reads the tooltip.

The character-info tab is a wrap of three methods and AutoCook is a complete worked example that ships at a mod-unique path (`common/media/lua/client/ISCharacterInfoWindow_AddTab.lua`): wrap `createChildren` to `self.panel:addView(name, view)`, wrap `onTabTornOff` to register the torn-off window with `ISLayoutManager`, and wrap `SaveLayout` to append the tab name to `layout.tabs` — and AutoCook's one gap is instructive, because it deliberately leaves `RestoreLayout` alone and vanilla's `RestoreLayout` resolves `layout.current` through `xpSystemText[…]`, which is nil for a mod tab.

There is no registry anywhere on this surface: `ISCharacterInfoWindow` hard-codes its five tabs in three separate methods, `ISHealthPanel` and `ISCharacterScreen` expose no extension point at all, and `ISHealthPanel:checkItems(handlers)` is a locally-built handler list rather than a mod-facing one — so every one of these routes is a monkey-patch and needs the library's idempotence guard and a `pcall` at the boundary.

For a custom status-icon stack the sibling's verdict stands (no vanilla Lua draws moodles; `zombie.ui.MoodlesUI` offers no mutator), and the one thing this read adds is that `MoodlesUI` extends `zombie/ui/UIElement`, its `getInstance()` is `public static`, and its geometry getters and `clientW`/`clientH` fields are public — so a mod's own icon column can *read* the vanilla stack's box to anchor itself under it, if `MoodlesUI` clears the exposure test, which has not been confirmed.

On cadence, the shipped copy of `simpleStatus` on disk today is no longer the uncached viewer the library describes: the item now has five version folders and the resolved one is `42.20/`, whose `ISSSBar:prerender` recomputes bar values only on `self.timer % 10 == 0` and resizes only every 60 frames — a correction candidate against #1467, #1477 and #1114, which name `42.16/` as live and "no cache anywhere on the path".

## A — panel toolkit

Base for every `install:` row in this table: `client/ISUI/`.

| item | file:line | what it is / does | side |
|---|---|---|---|
| `ISUIElement` | `install:client/ISUI/ISUIElement.lua:9` | `ISBaseObject:derive("ISUIElement")` — the root of the Lua widget set, 2002 lines, ~200 methods | client |
| `ISUIElement:new(x,y,w,h)` | `install:…/ISUIElement.lua:1965-2002` | all four args default to 0; sets `anchorLeft/Top=true`, `dock=ISDock.None`, `wantMouseEvents=true`, `wantKeyEvents=false`, `forceCursorVisible=false`, and records a creation stack trace | client |
| `ISUIElement:initialise()` | `install:…/ISUIElement.lua:13-20` | allocates `children`/`childrenInOrder` and assigns a unique `self.ID`; an in-file FIXME warns that calling it twice changes the ID | client |
| `ISUIElement:instantiate()` | `install:…/ISUIElement.lua:993-1009` | creates `UIElement.new(self)` as `self.javaObject`, copies x/y/w/h, the four anchors and the key/mouse/cursor flags across, then calls `self:createChildren()` | client |
| `ISUIElement:createChildren()` | `install:…/ISUIElement.lua:1010` | empty — the override point for child widgets; runs inside `instantiate`, so it is reached by the first `addToUIManager`/`setVisible`/`getIsVisible` call | client |
| `ISUIElement:addToUIManager()` | `install:…/ISUIElement.lua:1365-1371` | instantiates if needed, then `UIManager.AddUI(self.javaObject)` | client |
| `ISUIElement:removeFromUIManager()` | `install:…/ISUIElement.lua:1373-1379` | `UIManager.RemoveElement`, sets `self.removed = true`; this is how vanilla stops `update()` running (`install:client/XpSystem/ISUI/ISCharacterInfoWindow.lua:176`) | client |
| `ISUIElement:setVisible(b)` | `install:…/ISUIElement.lua:657-670` | instantiates if needed, forwards to the Java object, fires `visibleFunction(visibleTarget, self)` if set, and calls `self:doLayout()` on a false→true edge | client |
| `update` / `prerender` / `render` | `install:…/ISUIElement.lua:1610` / `:1614` / `:1618` | three empty stubs; the engine calls them per frame only while the element is in `UIManager` | client |
| `ISUIElement:wrapInCollapsableWindow(title, resizable, subClass)` | `install:…/ISUIElement.lua:1754-1773` | builds an `ISCollapsableWindow` (or `subClass`) sized `height + titleBarHeight + resizeWidgetHeight`, removes the panel from `UIManager`, re-parents it at `y = titleBarHeight()`, sets `o.nested` | client |
| `ISUIElement:centerOnScreen(playerNum)` | `install:…/ISUIElement.lua:1904-1911` | centres via `getPlayerScreenLeft/Top/Width/Height(playerNum)` — split-screen aware | client |
| `ISUIElement:stayOnSplitScreen(playerNum)` | `install:…/ISUIElement.lua:1815-1826` | clamps into that player's viewport when `getNumActivePlayers() > 1` | client |
| `ISUIElement:setRenderThisPlayerOnly(playerNum)` | `install:…/ISUIElement.lua:630-636` | Java-side per-player render filter; the correct way to keep a per-player panel off the other viewport | client |
| `ISUIElement:setWantKeyEvents(want)` | `install:…/ISUIElement.lua:1828-1835` | buffers the flag before `instantiate`, forwards after; enables `onKeyPress`/`onKeyRepeat`/`onKeyRelease` dispatch | client |
| key dispatch names | `jar:UIElement` method list | `onKeyPress(I)V`, `onKeyRepeat(I)V`, `onKeyRelease(I)V`, plus `isKeyConsumed(I)Z`, `onConsumeKeyPress(I)Z`, `onConsumeKeyRelease(I)Z` — the Lua names the engine looks for | client |
| draw helpers | `install:…/ISUIElement.lua:1013-1363` | `drawRect`, `drawRectBorder`, `drawTexture*` (11 variants), `drawText`/`drawTextCentre`/`drawTextRight`/`drawTextZoomed`, `drawProgressBar`, `drawItemIcon`, `drawScriptItemIcon`; `…Static` variants skip the scroll offset | client |
| stencils | `install:…/ISUIElement.lua:443-511` | `suspendStencil`/`resumeStencil`/`setStencilRect`/`clearStencilRect`; opt-in — the only in-tree `suspendStencil` caller is `install:client/ISUI/ISInventoryPane.lua:2265`, escaping the scroll clip while dragging | client |
| `ISPanel` | `install:client/ISUI/ISPanel.lua:3` | `ISUIElement:derive("ISPanel")`, 116 lines — background, border and optional mouse drag | client |
| `ISPanel:new` | `install:…/ISPanel.lua:96-115` | `background=true`, `backgroundColor={0,0,0,a=0.5}`, `borderColor={0.4,0.4,0.4,a=1}`, **`moveWithMouse=false`** | client |
| `ISPanel:prerender` | `install:…/ISPanel.lua:18-23` | draws the background rect + border when `self.background`; a derive that overrides `prerender` must call `ISPanel.prerender(self)` to keep it | client |
| `ISPanel:onMouseDown` | `install:…/ISPanel.lua:49-62` | returns `self:isWantMouseEvents()` when `moveWithMouse` is false; otherwise records `downX/downY`, sets `moving=true`, `bringToTop()`, and guards against `setCapture(true)` deliveries with `isMouseOver()` | client |
| `ISPanel:onMouseMove` / `onMouseMoveOutside` | `install:…/ISPanel.lua:80-94` / `:64-78` | the drag: moves `self.parent` when there is one, else `self`, and re-tops | client |
| `ISPanel:close` | `install:…/ISPanel.lua:14-16` | only `setVisible(false)` — it does **not** leave `UIManager`, so `update`/`prerender` keep running | client |
| `ISPanelJoypad` | `install:client/ISUI/ISPanelJoypad.lua:113` | `ISUIElement:derive`, 894 lines — the same background fields plus a row/column joypad navigation model (`joypadButtons`, `joypadButtonsY`, `allJoypadButtons`, `joypadIndex`); `:new` at `:871` | client |
| `ISCollapsableWindow` | `install:client/ISUI/ISCollapsableWindow.lua:9` | `ISPanel:derive`, 403 lines — the movable, collapsible, resizable titled window | client |
| `ISCollapsableWindow:new` | `install:…/ISCollapsableWindow.lua:366-401` | `pin=true` (pinned open), `isCollapsed=false`, `resizable=true`, `drawFrame=true`, `clearStentil=true`, `titleFont=UIFont.Small`, `backgroundColor a=0.8`; loads 8 vanilla textures through `getTexture("media/ui/…")` at `:382-389` | client |
| `ISCollapsableWindow:createChildren` | `install:…/ISCollapsableWindow.lua:26-93` | two `ISResizeWidget`s, `closeButton`, `infoButton` (hidden until `setInfo`), `pinButton` (hidden), `collapseButton`; button offset scales with `getCore():getOptionFontSizeReal()` | client |
| drag is unconditional here | `install:…/ISCollapsableWindow.lua:206-217, 270-280` | its `onMouseDown`/`onMouseMove` overrides have no `moveWithMouse` guard, so a collapsable window is always draggable | client |
| auto-collapse | `install:…/ISCollapsableWindow.lua:228-247` | while unpinned and the mouse is outside, `collapseCounter += getGameTime():getMultiplier()/getTrueMultiplier()/0.8` per frame; above 20 it sets `isCollapsed=true` and `setMaxDrawHeight(titleBarHeight())` | client |
| uncollapse | `install:…/ISCollapsableWindow.lua:219-226` | on a mouse move with `getMouseY() < titleBarHeight()` | client |
| `collapse()` / `pin()` | `install:…/ISCollapsableWindow.lua:138-150` | swap which of the two title-bar buttons is visible and flip `self.pin` | client |
| `TitleBarHeight()` vs `:titleBarHeight()` | `install:…/ISCollapsableWindow.lua:294-300` | the static form uses a file-scope `FONT_HGT_SMALL` measured at load (`:11-12`); the instance form uses `self.titleFontHgt` measured in `:new` — a font-size option change moves only the second | client |
| `ISCollapsableWindow:RestoreLayout` / `SaveLayout` | `install:…/ISCollapsableWindow.lua:336-354` | default geometry through `ISLayoutManager.DefaultRestoreWindow/DefaultSaveWindow` plus a `pin` key; a collapsable window therefore needs no layout functions of its own | client |
| `ISLayoutManager.RegisterWindow(name, funcs, target)` | `install:client/ISUI/ISLayoutManager.lua:6-13` | stores `{funcs, target}` under `name` and immediately `TryRestore(name)`; returns nothing; no unregister exists | client |
| `DefaultRestoreWindow` / `DefaultSaveWindow` | `install:…/ISLayoutManager.lua:15-60` | x, y, width, height, visible; resizes through the child `ISResizeWidget` when one is found; sets x/y twice "in case the keep-on-screen code moved the window"; `visible=='true'` re-adds to `UIManager` | client |
| `ReadIni` / `WriteIni` | `install:…/ISLayoutManager.lua:125-186` | `getFileReader("layout.ini", true)` / `getFileWriter("layout.ini", true, false)`; sections are `[WxH]` per resolution, rows are `name k=v k=v` | client |
| the only writer | `install:…/ISLayoutManager.lua:191-232` | `ISLayoutManager.OnPostSave` walks every registered window and rewrites the file; hooked with `Events.OnPostSave.Add` at `:232` | client |
| `OnPostSave` on a client | `jar:IngameState.updateInternal @207 L1370` and `@1557 L1575` | both trigger sites are in the exit path — one after `GameWindow.save(true)` on the clean `Core.exiting` route, one on the `serverDisconnected` route before `doDisconnect("crash")` | client |
| `GameWindow.save` on a client | `jar:GameWindow.save(Z)V @50-@74 L1174-L1179` | when `GameClient.clientSave` is set it saves the world map and visited map, triggers `'OnSave'` and returns — it never reaches the later `'OnSave'` at `@302 L1203` | client |
| every vanilla `RegisterWindow` name | `install:client/Chat/ISChat.lua:1172`, `client/ISUI/PlayerData/ISPlayerDataObject.lua:151-155`, `client/XpSystem/ISUI/ISCharacterInfoWindow.lua:154,185-197`, `client/Foraging/ISSearchWindow.lua:217`, `client/XpSystem/ISUI/ISCharacterScreen.lua:462`, four `TimedActions/IS*InfoAction.lua`, `client/RadioCom/ISRadioWindow.lua:30` | 19 call sites; names are flat strings, so a mod uses a vendor prefix | client |
| the `keyBinding` global | `install:shared/keyBinding.lua:6` | a flat list; a row whose `value` starts with `[` is a section header and gets no key (`install:client/OptionScreens/MainOptions.lua:3493`) | shared |
| `MainOptions.loadKeys` | `install:client/OptionScreens/MainOptions.lua:3473-3518` | `getCore():reinitKeyMaps()`, then per row `getCore():addKeyBinding(value, key, altCode, shift, ctrl, alt)` and `knownKeys[value] = bind` | client |
| `keysB42.ini` | `install:…/MainOptions.lua:3521-3590` (read), `:417`, `:3709` (write) | lines are applied only for names present in `knownKeys`, so a removed mod's stale line is ignored; the writer at `:420` skips rows flagged `isModBind` | client |
| the vanilla mod-style precedent | `install:client/Foraging/ISSearchManager.lua:1472-1475`, `:1481` | `ISSearchManager.initBinds` does two `table.insert(keyBinding, {…})` and is registered on `Events.OnGameBoot` | client |
| the registration deadline | `install:client/OptionScreens/MainScreen.lua:694`, `:2178` | `MainScreen:create()` calls `self.mainOptions:create()`, and `MainScreen` is built from `Events.OnMainMenuEnter` — a `keyBinding` insert or a `ModOptions` page must exist by then | client |
| reading a bound key | `install:server/XpSystem/XpUpdate.lua:147,151,156,160` | `getCore():isKey("Toggle Skill Panel", key)` inside an `OnKeyPressed`-style handler — preferred over `key == getCore():getKey(name)` because it also matches the alt code | client |
| `Core`'s key API | `jar:Core` method list | `getKey(String)I`, `getAltKey(String)I`, `isKey(String,Integer)Z`, `getKeyBinding(String)`, `getKeyBinding(I)`, `addKeyBinding(String,I,I,Z,Z,Z)V`, `reinitKeyMaps()V` | both |
| `PZAPI.ModOptions` | `install:client/PZAPI/ModOptions.lua:1-7` | the shipped mod-options API, 333 lines, entirely Lua; `Data` is the ordered page list, `Dict` the id map | client |
| `PZAPI.ModOptions:create(id, name)` | `install:…/ModOptions.lua:247-253` | returns an `Options` object and appends it to `Data`; `name` defaults to `id` | client |
| `Options:addKeyBind(id, name, key, tooltip)` | `install:…/ModOptions.lua:182-204` | a rebindable key row; keeps `defaultkey`; `getValue()` returns the current key code, `setValue(k)` also updates the live button | client |
| the rest of the widget set | `install:…/ModOptions.lua:28-245` | `addTitle`, `addDescription`, `addSeparator`, `addTextEntry`, `addTickBox`, `addMultipleTickBox`, `addComboBox`, `addColorPicker`, `addSlider`, `addButton` — each returns the option table with `getValue`/`setValue`/`setEnabled` and optional `onChange`/`onChangeApply` | client |
| `ModOptions.ini` | `install:…/ModOptions.lua:259-290` (save), `:292-333` (load) | one `type|pageId|optionId|value` line per option; lines whose page or id is unknown are preserved verbatim in `OtherOptions`, so an absent mod's settings survive | client |
| the only vanilla `load()` caller | `install:…/MainOptions.lua:2795-2796` | `MainOptions:addModOptionsPanel()`; and that panel is only added when `#PZAPI.ModOptions.Data ~= 0` (`:409`) | client |
| how a keybind row is drawn | `install:…/MainOptions.lua:2987-3023` | an `ISLabel` plus an `ISButton` with `isModBind = true`, appended to `MainOptions.keyText`; `isModBind` rows are excluded from `centerKeybindings` (`:3926`) and from the `keysB42.ini` write | client |
| apply order | `install:…/MainOptions.lua:3761-3766` | `gameOptions:apply()`, then `options:apply()` per page, then `getCore():saveOptions()`, then `PZAPI.ModOptions:save()` | client |
| the load-it-yourself pattern | `ws:3437629766/mods/CleanUI/42.19/media/lua/client/ISUI/CleanUI_ModOptions.lua:31-43` | a guarded, once-only `PZAPI.ModOptions:load()` inside a `pcall`, with the comment "ModOptions.ini is only loaded by vanilla after opening the options menu" | client |
| defensive access | `ws:…/CleanUI_ModOptions.lua:37, 49, 149, 220` | every touch is `PZAPI and PZAPI.ModOptions and …`, and `save()` is called through a `pcall` | client |
| `getTexture(name)` | `jar:LuaManager$GlobalObject.getTexture @0 L7189` | one call: `Texture.getSharedTexture(name)`; the name is a path relative to the merged `media/` root, so a mod's `<mod>/<ver>/media/ui/x.png` is `getTexture("media/ui/x.png")` | client |
| `getTexture` returns nil | `jar:Texture.getSharedTexture(Ljava/lang/String;I) @12 L425`, `@37 L432` | null when `GameServer.server` is set and `ServerGUI.isCreated()` is false, and null with a logged `DebugType.FileIO` error on any exception | server |
| `tryGetTexture(name)` | `jar:LuaManager$GlobalObject.tryGetTexture @0 L7194` | `Texture.trygetTexture` — the probing variant | client |
| the mod-PNG convention, worked | `ws:2867431511/mods/SimpleStatus/42.20/media/lua/client/ISSSBar.lua:417-419` + `…/42.20/media/ui/ss-*.png` | `getTexture(bar.icon)` → `getTexture("media/ui/ss-"..name..".png")` → `getTexture("media/ui/ss-unknow.png")`, each guarded by `if not tex` | client |
| fonts | `jar:UIFont` fields | 29 public static final constants: `Small`, `Medium`, `Large`, `Massive`, `NewSmall/NewMedium/NewLarge`, `MediumNew`, `Code*`, `AutoNorm*`, `Dialogue`, `Intro`, `Handwritten`, `DebugConsole`, `Title`, `Sdf*` | client |
| text metrics | `install:client/ISUI/ISCollapsableWindow.lua:11-12`; `install:client/XpSystem/ISUI/ISCharacterInfoWindow.lua:107-113` | `getTextManager():getFontHeight(UIFont.Small)` and `:MeasureStringX(font, str)`; both vanilla files measure at file scope, which caches a pre-option value | client |
| `MoodlesUI` as an anchor | `jar:MoodlesUI` class + flag parse | `public final class MoodlesUI extends zombie/ui/UIElement`; `getInstance()` is `public static`; `clientW`/`clientH` are public fields; `UIElement`'s `getX/getY/getWidth/getHeight` are public — so its box is readable even though it has no mutator (sibling report, rows 23-24) | client |

## B — food tooltip

| item | file:line | what it is / does | side |
|---|---|---|---|
| `ISToolTipInv` | `install:client/ISUI/ISToolTipInv.lua:3` | `ISPanel:derive`, 210 lines — the only Lua class that renders an inventory-item tooltip | client |
| the Java tooltip object | `install:…/ISToolTipInv.lua:186` | `o.tooltip = ObjectTooltip.new()` in `:new(item)`; proof `ObjectTooltip` is Lua-reachable, since vanilla Lua constructs it | client |
| **the wrap point** | `install:…/ISToolTipInv.lua:43-107` | `ISToolTipInv:render()` — the whole tooltip in one method; there is no `doTooltip` Lua method anywhere | client |
| its outer guard | `install:…/ISToolTipInv.lua:45` | the entire body is inside `if not ISContextMenu.instance or not ISContextMenu.instance.visibleCheck then` — nothing draws while a context menu is flagged visible | client |
| the measure pass | `install:…/ISToolTipInv.lua:63-66` | `tooltip:setWidth(50)`, `setMeasureOnly(true)`, `self.item:DoTooltip(self.tooltip)`, `setMeasureOnly(false)` — this is where the tooltip's height for the frame is decided | client |
| the panel geometry | `install:…/ISToolTipInv.lua:73-97` | reads `tooltip:getWidth()/getHeight()`, clamps x/y to the screen, then `self:setX/setY/setWidth/setHeight` from the tooltip | client |
| the background | `install:…/ISToolTipInv.lua:103-104` | `self:drawRect(0,0,self.width,self.height,…)` + `drawRectBorder` — drawn from the measured height, **before** the content | client |
| the draw pass | `install:…/ISToolTipInv.lua:105` | `self.item:DoTooltip(self.tooltip)` a second time, unmeasured | client |
| what the wrap has access to | `install:…/ISToolTipInv.lua:9, 169-179, 186` | `self.item` (the `InventoryItem`), `self.tooltip` (the Java `ObjectTooltip`), `self.owner`, `self.contextMenu`, `self.followMouse`, `self.anchorBottomLeft`, and the whole `ISPanel` draw surface | client |
| the character the gate reads | `install:…/ISToolTipInv.lua:173-175` | `setCharacter(chr)` forwards to `tooltip:setCharacter(chr)`; `DoTooltipEmbedded` pulls it back with `getCharacter()` and casts to `IsoPlayer` (`jar:… @28-@41 L745`) | client |
| `InventoryItem.DoTooltip(ObjectTooltip)` | `jar:InventoryItem.DoTooltip @0 L735` | four instructions: `DoTooltipEmbedded(tooltip, null, 0)` | both |
| `InventoryItem.DoTooltipEmbedded` | `jar:InventoryItem.DoTooltipEmbedded @0 L739 … @4264 L1170` | `tooltip.render()` first, then the name line and `adjustWidth`, the `Contains` block, `tooltip.beginLayout()` at `@578`, delegated blocks (`AttributeContainer.DoTooltip @3597`, `FluidContainer.DoTooltip @3614/@3644`, `Durability.DoTooltip @3661`), `Layout.render @4216`, `endLayout @4224` | both |
| the height is Java's | `jar:InventoryItem.DoTooltipEmbedded @4236-@4240 L1164` | `tooltip.setHeight(y + tooltip.padBottom)`; then `@4243-@4261 L1166-L1167` forces a minimum width of 150 | both |
| the embedded/standalone split | `jar:… @4203 L1159` | `aload_2 ifnonnull 4264` — when a `Layout` is passed in, the render/`endLayout`/`setHeight` tail is skipped and the caller owns it | both |
| `Food.DoTooltip` | `jar:Food.DoTooltip(Lzombie/ui/ObjectTooltip;Lzombie/ui/ObjectTooltip$Layout;)V` | the food block, called with the parent's `Layout`, so it only adds rows | both |
| **the nutrition-block gate** | `jar:Food.DoTooltip @1241-@1288 L1521` | three arms to `@1291 L1522`: `Core.debug && DebugOptions.instance.tooltipInfo.getValue()`; an internal boolean local; `hasTrait(CharacterTrait.NUTRITIONIST)` or `hasTrait(CharacterTrait.NUTRITIONIST2)`. The block itself starts `Tooltip_food_Nutrition` at `@1297` and `Tooltip_food_Calories` at `@1327` | both |
| `ObjectTooltip` | `jar:zombie/ui/ObjectTooltip` (flag parse) | `public final … extends zombie/ui/UIElement` | client |
| its drawing surface | `jar:ObjectTooltip` method list | public: `DrawText/DrawTextCentre/DrawTextRight(UIFont,String,d,d,d,d,d,d)`, `DrawValueRight(IIIZ)`, `DrawValueRightNoPlus(III)`/`(FII)`, `DrawTextureScaled`, `DrawTextureScaledAspect`, `DrawProgressBar(IIIIFdddd)`, `adjustWidth(I,String)`, `beginLayout()`, `endLayout(Layout)`, `getLineSpacing()I`, `getFont()`, `setMeasureOnly(Z)`/`isMeasureOnly()`, `setCharacter`/`getCharacter`, `get/setWeightOfStack` | client |
| its public fields | `jar:ObjectTooltip` (flag parse) | `padLeft`, `padTop`, `padRight`, `padBottom` (all `public int`), `isItem`, `item`, `object`; `alpha`, `texture` are package-private, `measureOnly`/`character` private | client |
| `ObjectTooltip$Layout` | `jar` method list | `addItem() -> LayoutItem`, `setMinLabelWidth(I)`, `setMinValueWidth(I)`, `render(I,I,ObjectTooltip)->I`, `free()` | client |
| `ObjectTooltip$LayoutItem` | `jar` method list | `setLabel(String,f,f,f,f)`, `setValue(String,f,f,f,f)`, `setValueRight(I,Z)`, `setValueRightNoPlus(F)`/`(I)`, `setProgress(f,f,f,f,f)`, `calcSizes()`, `render(I,I,I,I,ObjectTooltip)` | client |
| the ten `ISToolTipInv` construction sites | `install:client/ISUI/ISInventoryPane.lua:854`; `client/ISUI/ISInventoryPaneContextMenu.lua:3767`; `client/ISUI/ISEquippedItem.lua:586`; `client/Hotbar/ISHotbar.lua:270`; `client/ISUI/ISTradingUI.lua:565`; `client/ISUI/ISWorldObjectContextMenu.lua:2624`; `client/Fluids/ISFluidBar.lua:220`; `client/Entity/ISUI/Controls/ISEnergyBar.lua:90`; `client/Entity/ISUI/CraftRecipe/ISCraftInventoryPanel.lua:48`; `client/ISUI/ISXuiSkin.lua:236` | one wrap of the class covers all of them | client |
| the "Information" context-menu tooltip | `install:client/ISUI/ISInventoryPaneContextMenu.lua:3765-3778` | `information(item)` builds its own `ISToolTipInv` and adds it to `UIManager`; `removeToolTip()` tears it down | client |
| the second tooltip route | `install:client/Entity/ISUI/Controls/ISItemSlot.lua:545-550` | `ISItemSlot.drawTooltip(_itemSlot, _tooltip)` is a plain Lua function that calls `resource:DoTooltip(_tooltip)` or `storedItem:DoTooltip(_tooltip)` — a clean second wrap point for crafting slots | client |
| its panel | `install:client/Entity/ISUI/Components/Crafting/ISToolTipItemSlot.lua:3, :152` | `ISPanel:derive`, with its own `ObjectTooltip.new()`; separate class from `ISToolTipInv` | client |
| **CleanUI ships no `ISToolTipInv.lua`** | `find` over all of `ws:3437629766/mods/CleanUI` (7 version folders + `common/`) | 0 matches; the 43 vanilla-path files it does ship are listed in E | — |
| CleanUI's copies still use the class | `ws:3437629766/mods/CleanUI/42.19/media/lua/client/ISUI/ISInventoryPane.lua:3552`; `…/ISInventoryPaneContextMenu.lua:4249` | so `ISToolTipInv.render` is still reached under CleanUI | client |
| CleanUI's stack representation | `ws:…/42.19/…/ISInventoryPane.lua:3526-3533, 3563` | for a multi-item group it passes `CleanUI_getStackDisplayItem(group)` as the item and `tooltip:setWeightOfStack(w)`; a wrap sees one representative item | client |
| CleanUI's tooltip reuse test | `ws:…/42.19/…/ISInventoryPane.lua:3537-3544` | it early-returns when the item **and** `tooltip:getWeightOfStack()` are unchanged and the tooltip is visible — so `setItem` is not called every frame | client |
| clipping is parent-based | `jar:UIElement.render @19-@125 L1679-L1686` | the clip arms test `parent.maxDrawHeight` and `parent.renderClippedChildren`; a top-level element (`parent == null`) skips both, so a `UIManager`-level tooltip's own draws are not clipped to its rect by this method | client |

## C — character info window

| item | file:line | what it is / does | side |
|---|---|---|---|
| `ISCharacterInfoWindow` | `install:client/XpSystem/ISUI/ISCharacterInfoWindow.lua:4` | `ISCollapsableWindow:derive`, 351 lines, one instance per player; `:new(x,y,w,h,playerNum)` at `:331` sets `resizable=false`, `backgroundColor.a=0.9` | client |
| the tab container | `install:…/ISCharacterInfoWindow.lua:117-123` | `ISTabPanel:new(0, titleBarHeight, max(width, tabTotalWidth), height-th-rh)`, `tabPadX = 10`, `equalTabWidth = false`, `setOnTabTornOff(self, onTabTornOff)` | client |
| the five hard-coded tabs | `install:…/ISCharacterInfoWindow.lua:127-148` | `charScreen`(`ISCharacterScreen`), `characterView`(`ISCharacterInfo`), `healthView`(`ISHealthPanel`), `protectionView`(`ISCharacterProtection`), `clothingView`(`ISClothingInsPanel`) — each `:new` then `:initialise()` then `self.panel:addView(name, view)` | client |
| tab width is pre-measured | `install:…/ISCharacterInfoWindow.lua:106-113` | the window sums `MeasureStringX` over the five names plus `10*5+6`, with an in-file comment calling it "a nasty way to do this"; a mod tab widens the panel only through `ISTabPanel`'s own `maxLength` | client |
| tab names are translated strings | `install:server/XpSystem/XpSystem_text.lua:1-10` | `xpSystemText.info/skills/health/protection/clothingIns = getText("IGUI_XP_*")`; `getView`/`activateView`/`toggleView` are all keyed on that display string | shared (in a `server/` dir) |
| `ISTabPanel:addView(name, view)` | `install:client/ISUI/ISTabPanel.lua:484-507` | builds `{name, id, view, tabWidth, fade}`, appends to `viewList`, sets `view:setY(self.tabHeight)`, `addChild(view)`, `view.parent = self`; the first view becomes visible and active, later ones invisible | client |
| `ISTabPanel` view API | `install:…/ISTabPanel.lua:401, 411, 438, 465, 472, 509, 523, 609` | `getView(name)`, `activateViewById(id)`, `activateView(name)`, `getActiveView()`, `getActiveViewIndex()`, `removeView(view)`, `replaceView(view, panel)`, `setOnTabTornOff(target, method)` | client |
| `toggleView(viewName)` | `install:…/ISCharacterInfoWindow.lua:39-78` | the show/hide entry point: sets the info text from `view.infoText`, activates or closes, falls back to the torn-off window list | client |
| `RestoreLayout` hard-codes the five | `install:…/ISCharacterInfoWindow.lua:202-289` | builds a `floating` table with exactly `info/skills/health/protection/clothingIns`, rebuilds torn-off windows, then `if layout.current and not floating[layout.current] then self.panel:activateView(xpSystemText[layout.current])` — `xpSystemText[<mod tab>]` is nil | client |
| `SaveLayout` hard-codes them again | `install:…/ISCharacterInfoWindow.lua:291-329` | nils out width/height, then tests each of the five `view.parent == self.panel` to build `layout.tabs` and `layout.current` | client |
| `onTabTornOff` | `install:…/ISCharacterInfoWindow.lua:182-200` | per view, `ISLayoutManager.RegisterWindow('charinfowindow.<id>', ISCollapsableWindow, window)` when `playerNum == 0`, then `window:setResizable(false)` | client |
| the window's own layout row | `install:…/ISCharacterInfoWindow.lua:153-155` | `ISLayoutManager.RegisterWindow('charinfowindow', ISCharacterInfoWindow, self)` for player 0 only | client |
| instance access | `install:client/ISUI/PlayerData/ISPlayerData.lua:111-115` | `getPlayerInfoPanel(id)` → `getPlayerData(id).characterInfo` | client |
| creation timing | `install:client/ISUI/PlayerData/ISPlayerDataObject.lua:93-96`; `install:client/ISUI/PlayerData/ISPlayerData.lua:158-168, 203` | built inside `createPlayerData`, which is on `Events.OnCreatePlayer` — so a `createChildren` wrap must be installed at file scope, before that event | client |
| vanilla's own toggles | `install:server/XpSystem/XpUpdate.lua:147-163` | `getCore():isKey("Toggle Skill Panel"/"Toggle Health Panel"/"Toggle Info Panel"/"Toggle Clothing Protection Panel", key)` → `getPlayerInfoPanel(n):toggleView(xpSystemText.<id>)` | client |
| **AutoCook's worked tab, quoted below** | `ws:3388721641/mods/AutoCook/common/media/lua/client/ISCharacterInfoWindow_AddTab.lua:1-49` | one global function `addCharacterPageTab(tabName, pageType)`, at a mod-unique relative path under `common/` | client |
| its call site | `ws:3388721641/mods/AutoCook/common/media/lua/client/ISCharacterCook.lua:398` | `addCharacterPageTab("Cook", ISCharacterCook)` at file scope, after the class body | client |
| its panel class | `ws:…/ISCharacterCook.lua:1-5, 175-189` | `require "ISUI/ISPanelJoypad"` + `require "ISCharacterInfoWindow_AddTab"`, `ISCharacterCook = ISPanelJoypad:derive(...)`, `:new(x,y,width,height,playerNum)` storing `playerNum` and `char = getSpecificPlayer(playerNum)`, `noBackground()` | client |
| what AutoCook leaves unwrapped | `ws:…/ISCharacterInfoWindow_AddTab.lua:25-27` | `RestoreLayout` is commented out with "I do not understand this… I guess this is no big deal" — so its tab is saved into `layout.tabs` but never restored as a torn-off window, and a saved `layout.current = "Cook"` reaches `activateView(nil)` | client |
| `ISHealthPanel` | `install:client/XpSystem/ISUI/ISHealthPanel.lua:4` | `ISPanelJoypad:derive`, 1987 lines; `:new(player,x,y,w,h)` at `:962`, `createChildren` at `:118`, `prerender` at `:421`, `render` at `:431-504` | client |
| no extension point on it | `install:…/ISHealthPanel.lua` read in full | no registry, no hook table, no `addX`; `render` hard-codes its lines and drives `self.listbox` geometry from a locally computed `y` | client |
| the nearest thing to one | `install:…/ISHealthPanel.lua:1762-1794`, `:1796+` | `checkItems(handlers)` / `checkContainerItems(container, childContainers, handlers)` walk the doctor's containers and call `handler:checkItem(item)` — but the `handlers` list is built locally in `doBodyPartContextMenu` (`:1799`), not exposed | client |
| a second health widget | `install:…/ISHealthPanel.lua:10-12` | `ISNewHealthPanel = ISUIElement:derive("ISNewHealthPanel")` with its own `instantiate` — the Java-backed body diagram the panel embeds | client |
| `ISCharacterScreen` | `install:client/XpSystem/ISUI/ISCharacterScreen.lua:45-729` | the Info tab; `prerender` `:58`, `render` `:74-247`, `create` `:253`; trait display via `setDisplayedTraits`/`loadTraits` (`:575`, `:599`); no registry either | client |

### AutoCook's `ISCharacterInfoWindow_AddTab.lua`, verbatim

```lua

function addCharacterPageTab(tabName,pageType)

    local viewName = tabName.."View"

    local upperLayer_ISCharacterInfoWindow_createChildren = ISCharacterInfoWindow.createChildren
    function ISCharacterInfoWindow:createChildren()
        upperLayer_ISCharacterInfoWindow_createChildren(self)
        
        self[viewName] = pageType:new(0, 8, self.width, self.height-8, self.playerNum)
        self[viewName]:initialise()
        self[viewName].infoText = getText("UI_"..tabName.."Panel");--UI_<tabName>Panel is full text of tooltip
        self.panel:addView(getText("UI_"..tabName), self[viewName])--UI_<tabName> is short text of tab
    end

    local upperLayer_ISCharacterInfoWindow_onTabTornOff = ISCharacterInfoWindow.onTabTornOff
    function ISCharacterInfoWindow:onTabTornOff(view, window)
        if self.playerNum == 0 and view == self[viewName] then
            ISLayoutManager.RegisterWindow('charinfowindow.'..tabName, ISCollapsableWindow, window)
        end
        upperLayer_ISCharacterInfoWindow_onTabTornOff(self, view, window)

    end

    --I do not understand this. but as it does not work for porotection, I guess this is no big deal. let's test without.
    --function ISCharacterInfoWindow:RestoreLayout(name, layout)
    --end

    local upperLayer_ISCharacterInfoWindow_SaveLayout = ISCharacterInfoWindow.SaveLayout
    function ISCharacterInfoWindow:SaveLayout(name, layout)
        upperLayer_ISCharacterInfoWindow_SaveLayout(self,name,layout)
        
        local addTabName = false
        local subSelf = self[viewName]
        if subSelf and subSelf.parent == self.panel then
            addTabName = true
            if subSelf == self.panel:getActiveView() then
                layout.current = tabName
            end
        end
        if addTabName then
            if not layout.tabs then
                layout.tabs = tabName 
            else
                layout.tabs = layout.tabs .. ',' .. tabName
            end
        end
    end
end
```

Three things about it are the reusable part and one is a defect. Reusable: it wraps rather than replaces, it keys everything off one `tabName` so the same function serves any number of tabs, and it guards `playerNum == 0` on the layout registration exactly as vanilla does. Not reusable: it is not idempotent — a second `require` of the file would wrap the already-wrapped methods again — and it lacks the `RestoreLayout` wrap, which is what makes its own `layout.current = tabName` unsafe.

## D — events and cadence

| item | file:line | what it is / does | side |
|---|---|---|---|
| `OnPreUIDraw` | `jar:UIManager.render @161-@173 L330-L331` | fired before the UI element pass, gated on `LuaManager.thread` | client |
| `OnPostUIDraw` | `jar:UIManager.render @659-@668 L404-L405` | fired once per UI render after the element pass, gated on `LuaManager.thread == UIManager.defaultthread`; not per player | client |
| `OnRenderTick` | `jar:GameWindow.onRender @0 L876` | the entire method body is `triggerEvent('OnRenderTick')` — the per-rendered-frame hook | client |
| a panel's own per-frame callbacks | `install:client/ISUI/ISUIElement.lua:1610-1620` | `update`, `prerender`, `render` are driven by the Java `UIElement` and run only while the element is in `UIManager` | client |
| leaving `UIManager` stops them | `install:client/XpSystem/ISUI/ISCharacterInfoWindow.lua:174-180` | `close()` does `setVisible(false)` **and** `removeFromUIManager()` "so update() isn't called" — the cheapest possible early-out for a hidden panel | client |
| `OnPostSave` | `jar:IngameState.updateInternal @207 L1370`, `@1557 L1575` | exit-path only (see A); the layout writer hangs off it | client |
| the library's tier rule | `docs/platform/lessons.md:14` | slow simulation on `EveryOneMinute`/`EveryTenMinutes`; `OnPlayerUpdate` only for per-frame needs behind a cheap early-out; avoid `OnTick` — 38 corpus mods already share `OnPlayerUpdate` and `OnTick` is the expensive tier [#1071/C/snapshot] | both |
| the library's cost caveat | `docs/platform/lessons.md:189`; `docs/areas/ui-and-moodles.md` walls | the tier counts are static counts over one dated sweep and no mod was run to produce them; and no shipped command measures frame time or Lua call counts, so the read-cadence rule bounds a *count of avoided reads*, not a measured cost [#1477/C/C-only, #1114/M/n=1] | — |
| `simpleStatus` panel lifecycle | `ws:2867431511/mods/SimpleStatus/42.20/media/lua/client/ss.main.lua:56-87` | `Events.OnCreatePlayer` tears down any existing panel, loads config from player modData, `SSBar:new(player,cfg)`, `initialise()`, `addToUIManager()`; `Events.OnKeyPressed` forwards every key to every panel's `handleKey` | client |
| `simpleStatus` draw cadence, installed copy | `ws:…/SimpleStatus/42.20/media/lua/client/ISSSBar.lua:452-476` | `prerender` calls `ISPanel.prerender(self)`, then recomputes values only when `self.timer % 10 == 0`, resizes the window when `self.timer == 60`, and draws the bars every frame | client |
| the 42.16 copy the library read | `ws:…/SimpleStatus/42.16/media/lua/client/ISSSBar.lua:452-465` | the same method with an unconditional `self:prepareBarInfo()` and no modulo — the uncached shape behind #1477 | client |
| `simpleStatus` key handling | `ws:…/SimpleStatus/42.20/media/lua/client/ISSSBar.lua:533-548` | `key == ssOptions.toggleKey:getValue()` toggles `setVisible` + `addToUIManager`/`removeFromUIManager`; a second key toggles `config.locked` and `self.moveWithMouse` | client |
| `simpleStatus` persistence | `ws:…/SimpleStatus/42.20/media/lua/client/ISSSBar.lua:18-36`, `:478-483` | `savePlayerData` writes a flat table into `player:getModData()["SimpleStatusConfig"]` and calls `player:transmitModData()`; `onMouseUp` calls it on every drag release | client → server |
| `simpleStatus` extension API | `ws:…/SimpleStatus/42.20/media/lua/client/SimpleStatus.lua:37-105` | `SimpleStatus:addStat(name, stat, reverse_stat)` (needs `stat.valueFn(player)`; optional `type`, `shown`, `ruler`, `title`, `icon`, `percentFn`/`textFn`/`colorFn`) and `SimpleStatus:addCharacterStat(name, key, opts)` reading `CharacterStat.REGISTRY:get(key)`; both refuse duplicates and print | client |
| `CleanUI`'s event budget | `ws:3437629766/mods/CleanUI/42.19` (grep over all Lua) | 5 × `OnGameBoot`, 5 × `OnGameStart`, 5 × `OnTick`, 1 × `OnKeyPressed`, 1 × `OnCreatePlayer`, 1 × `OnContainerUpdate` | client |
| every CleanUI `OnTick` is a one-shot | `ws:…/42.19/…/CleanUI/CleanUI_InventoryUIModeSwitcher.lua:413, 416, 445, 449`; `…/ISUI/ISInventoryPane.lua:249-251` | each handler calls `Events.OnTick.Remove(tickFn)` once its bootstrap or its deferred action queue is done | client |
| `CleanUI`'s own render caching | `ws:…/42.19/…/ISUI/ISInventoryPane.lua:1030, 1125` | comments: "Cache by direct inputs so steady rendering does not allocate a key string" and "The steady-state path returns before allocating or normalizing geometry" | client |
| `NeatUI_Framework` | `ws:3508537032/mods/NeatUI_Framework` | CleanUI's hard `require`; 11 client Lua files, one `NeatTool` global with 3-patch/9-patch/percentage/text draw helpers plus `NIScrollView`/`NIGridVirtualScrollView` `ISUIElement` derives, and an `ISUIElement` compatibility shim that defines `getCentreX`/`getSelfCenterX` only when absent | client |

## E — absences

Each row states the exact search, per [jar-research](../../platform/jar-research.md)'s absence rule.

| absence | how it was proved | what it means |
|---|---|---|
| no `getOptionModsKey` on `Core` or anywhere in the jar | `pz.sh grep getOptionModsKey` → `no class contains that literal`; and `pz.sh methods zombie/core/Core \| grep -i key` lists only `getKey`, `getAltKey`, `isKey`, `getKeyBinding` ×2, `addKeyBinding`, `reinitKeyMaps`, `isFunctionKey` | there is no engine option slot for a mod key; a mod key is a `keyBinding` row or a `PZAPI.ModOptions` keybind |
| no `ModOptions` identifier anywhere in the jar | `pz.sh grep ModOptions` → `no class contains that literal` | `PZAPI.ModOptions`, its keybind widget, and `ModOptions.ini` are entirely Lua; there is no Java half to break |
| no `registerKeyBind` anywhere in the jar | `pz.sh grep registerKeyBind` → `no class contains that literal` | the only engine entry is `Core.addKeyBinding(String,I,I,Z,Z,Z)`, and vanilla Lua calls it only from `MainOptions.loadKeys` |
| no Lua `doTooltip` method and no tooltip hook registry | `grep -rn "DoTooltip\|ObjectTooltip" media/lua` → exactly 6 hits: `ISToolTipInv.lua:65,105,186`, `Entity/ISUI/Controls/ISItemSlot.lua:546,548`, `Entity/ISUI/Components/Crafting/ISToolTipItemSlot.lua:152` | the Lua seams are `ISToolTipInv:render` and `ISItemSlot.drawTooltip`, and nothing else |
| CleanUI ships no copy of any route this design uses | `find` over all 7 version folders + `common/` of `ws:3437629766/mods/CleanUI`, then a per-file existence test against the install: 43 collisions, all listed below | `ISToolTipInv.lua`, `ISUIElement.lua`, `ISPanel.lua`, `ISPanelJoypad.lua`, `ISCollapsableWindow.lua`, `ISTabPanel.lua`, `ISLayoutManager.lua`, `ISCharacterInfoWindow.lua`, `ISHealthPanel.lua`, `ISCharacterScreen.lua` are all CleanUI-free |
| the 43 CleanUI vanilla-path files, 42.19 | see the list below | the only ones that matter here are `client/ISUI/ISInventoryPane.lua` and `client/ISUI/ISInventoryPaneContextMenu.lua` (the tooltip call sites) and `client/ISUI/ISInventoryPage.lua` |
| no tab registry on `ISCharacterInfoWindow` | the whole 351-line file read; tabs appear hard-coded in `createChildren` (`:127-148`), in `RestoreLayout`'s `floating` table (`:211-231`) and in `SaveLayout`'s five `parent == self.panel` tests (`:298-327`) | a tab costs three method wraps, not a registration call |
| no extension point on `ISHealthPanel` or `ISCharacterScreen` | both files' method lists read in full (1987 and 762 lines); no `addX`, no registry table, no event | wrapping `render`/`createChildren` is the only route |
| no `ModOptions` workshop mod installed | `find . -maxdepth 3 -type d -iname "*modoption*"` over all 182 installed items → 0 | `PZAPI.ModOptions` is the only mod-options API present on this machine's corpus |
| no vanilla Lua reads a Java *instance* field | `grep -rn "\.isCookable\b\|square\.x\b\|\.padBottom\|\.padTop\|\.padLeft\|\.padRight" media/lua` → the only `padBottom` hits are local Lua variables in UI files; static enum fields (`MoodleType.*`, `CharacterStat.*`, `Joypad.*`, `Keyboard.KEY_*`) are read freely | whether Kahlua exposes a public instance field like `ObjectTooltip.padBottom` for read or write is **unread** — the padding trick in Minimal shapes is a hypothesis |
| no vanilla Lua draws the moodle stack | sibling report rows 23-24: all 29 moodle-named files under `media/lua` are `Translate/*/Moodles.json`, and `zombie.ui.MoodlesUI`'s 15 members contain no add/insert/register | cross-referenced, not re-done here |

CleanUI 42.19's 43 vanilla relative paths: `client/ISUI/ISInventoryPage.lua`, `ISInventoryPane.lua`, `ISInventoryPaneContextMenu.lua`; `client/ISUI/InventoryWindow/ISInventoryWindowContainerControls.lua`, `ISInventoryWindowControlHandler.lua`, `Handlers/TransferAll.lua`, `Handlers/TransferSameType.lua`; `client/ISUI/LootWindow/ISLootWindowContainerControls.lua`, `ISLootWindowFloorControlHandler.lua`, `ISLootWindowObjectControlHandler.lua` and 19 `LootWindow/Handlers/*.lua`; `shared/TimedActions/ISFixAction.lua`, `ISFixVehiclePartAction.lua`; and `shared/Translate/{CN,DE,EN,ES,FR,KO,PL,PTBR,RU,TH}/UI.json`.

## Minimal shapes

Everything in this section is **derived from the read and untested** — nothing was booted. Each shape is the smallest form that the files above say should work; the risk column names what a run has to check.

### 1. A movable, collapsible, keybound panel with persisted geometry

One file, `media/lua/client/NutriPanel.lua`, plus one option file. Nothing at a vanilla relative path.

```lua
-- media/lua/client/NutriPanel_Options.lua  (file scope, so it exists before OnMainMenuEnter)
NutriOpts = NutriOpts or {}
if PZAPI and PZAPI.ModOptions and not NutriOpts.page then
    NutriOpts.page      = PZAPI.ModOptions:create("NutritionMod", getText("UI_NutriMod_Name"))
    NutriOpts.toggleKey = NutriOpts.page:addKeyBind("togglePanel",
                            getText("UI_NutriMod_TogglePanel"), Keyboard.KEY_N, nil)
end
-- vanilla loads ModOptions.ini only when the options screen is built; load it ourselves once
function NutriOpts.loadOnce()
    if NutriOpts.loaded then return end
    NutriOpts.loaded = true
    if PZAPI and PZAPI.ModOptions and type(PZAPI.ModOptions.load) == "function" then
        pcall(function() PZAPI.ModOptions:load() end)
    end
end
```

```lua
-- media/lua/client/NutriPanel.lua
require "ISUI/ISCollapsableWindow"
require "ISUI/ISLayoutManager"
require "NutriPanel_Options"

NutriPanel = ISCollapsableWindow:derive("NutriPanel")   -- movable + collapsible for free
NutriPanel.instances = NutriPanel.instances or {}

function NutriPanel:new(x, y, w, h, playerNum)
    local o = ISCollapsableWindow:new(x, y, w, h)
    setmetatable(o, self); self.__index = self
    o.playerNum = playerNum
    o.title     = getText("UI_NutriMod_PanelTitle")
    o:setResizable(false)
    o.cache     = nil          -- the push-cadence cache, rule #1114
    o.cacheAt   = -1
    return o
end

function NutriPanel:initialise() ISCollapsableWindow.initialise(self) end

function NutriPanel:refresh()                    -- once a second, not once a frame
    local now = getTimestampMs()
    if self.cacheAt > 0 and now - self.cacheAt < 1000 then return end
    self.cacheAt = now
    self.cache   = NutriMod.readMirror(getSpecificPlayer(self.playerNum))
end

function NutriPanel:prerender()
    ISCollapsableWindow.prerender(self)          -- keeps frame, title and background
    self:refresh()
end

function NutriPanel:render()
    ISCollapsableWindow.render(self)
    if self.isCollapsed or not self.cache then return end
    local y = self:titleBarHeight() + 4
    for _, row in ipairs(self.cache) do
        self:drawText(row.label, 8, y, 1, 1, 1, 1, UIFont.Small)
        self:drawTextRight(row.value, self:getWidth() - 8, y, 1, 1, 1, 1, UIFont.Small)
        y = y + getTextManager():getFontHeight(UIFont.Small)
    end
end

-- geometry persistence: ISCollapsableWindow already supplies RestoreLayout/SaveLayout
local function onCreatePlayer(playerNum, playerObj)
    NutriOpts.loadOnce()
    local old = NutriPanel.instances[playerNum]
    if old then old:setVisible(false); old:removeFromUIManager() end
    local p = NutriPanel:new(60, 200, 260, 180, playerNum)
    p:initialise()
    p:addToUIManager()
    p:setVisible(false)
    p:setRenderThisPlayerOnly(playerNum)
    NutriPanel.instances[playerNum] = p
    if playerNum == 0 then
        ISLayoutManager.RegisterWindow("NutritionMod.panel", ISCollapsableWindow, p)
    end
end

local function onKeyPressed(key)
    if not (NutriOpts.toggleKey and key == NutriOpts.toggleKey:getValue()) then return end
    local p = NutriPanel.instances[0]
    if not p then return end
    if p:getIsVisible() then
        p:setVisible(false); p:removeFromUIManager()      -- stops update/prerender/render
    else
        p:setVisible(true);  p:addToUIManager(); p:bringToTop()
    end
end

Events.OnCreatePlayer.Add(onCreatePlayer)
Events.OnKeyPressed.Add(onKeyPressed)
```

Risks a run must check: whether `RegisterWindow` restoring `visible=true` re-adds the panel before the keybind has ever been pressed (`DefaultRestoreWindow` does `addToUIManager()` at `install:client/ISUI/ISLayoutManager.lua:45-47`); whether `layout.ini` is written at all on the harness client's exit path; and whether `PZAPI.ModOptions:load()` called this early finds the file.

### 2. Appending lines to the food tooltip

```lua
-- media/lua/client/NutriTooltip.lua
require "ISUI/ISToolTipInv"

if not NutriTooltip_wrapped then                      -- idempotence guard
    NutriTooltip_wrapped = true
    local origRender = ISToolTipInv.render

    function ISToolTipInv:render()
        local lines
        local ok, err = pcall(function() lines = NutriMod.tooltipLines(self.item) end)
        if not ok then lines = nil end                 -- never take the vanilla tooltip down

        origRender(self)

        if not lines or #lines == 0 then return end
        -- replicate the vanilla guard at ISToolTipInv.lua:45, or we draw over a context menu
        if ISContextMenu.instance and ISContextMenu.instance.visibleCheck then return end

        local tt   = self.tooltip
        local step = tt:getLineSpacing()
        local y    = self:getHeight()                  -- just under the Java block
        local band = step * #lines + 4
        self:drawRect(0, y, self:getWidth(), band,
                      self.backgroundColor.a, self.backgroundColor.r,
                      self.backgroundColor.g, self.backgroundColor.b)
        self:drawRectBorder(0, y, self:getWidth(), band,
                      self.borderColor.a, self.borderColor.r,
                      self.borderColor.g, self.borderColor.b)
        for _, line in ipairs(lines) do
            self:drawText(line, 8, y + 2, 1, 1, 1, 1, UIFont.Small)
            y = y + step
        end
        self:setHeight(self:getHeight() + band)        -- keep the box honest for next frame
    end
end
```

This draws the mod's band *below* the Java tooltip in its own framed strip rather than inside it, because the tooltip's height is fixed by `InventoryItem.DoTooltipEmbedded @4240 L1164` before any Lua runs and the background rect at `ISToolTipInv.lua:103` is already painted by the time the wrap regains control. Two unknowns: whether draws below a top-level element's rect are visible (the parent-based clip at `jar:UIElement.render @19-@125 L1679-L1686` says a parentless element skips the clip, but no other scissor was traced), and whether `self:setHeight` here fights the next frame's recompute at `:97`.

The tidier variant, if a probe confirms Kahlua allows a write to a public Java instance field, is to reserve the band inside the tooltip instead — set `self.tooltip.padBottom = base + band` **before** `origRender(self)`, so the measure pass at `:63-66` produces the taller height, the background at `:103` covers the band, and the wrap then draws inside it. That relies on `ObjectTooltip.padBottom` being `public int` (confirmed by the flag parse) *and* on Lua being able to write it (not confirmed — no vanilla Lua touches a Java instance field). For a crafting slot, wrap `ISItemSlot.drawTooltip` the same way.

### 3. A character-info tab

```lua
-- media/lua/client/NutriInfoTab.lua        (file scope: before Events.OnCreatePlayer)
require "ISUI/ISPanelJoypad"
require "ISUI/ISLayoutManager"

NutriInfoPanel = ISPanelJoypad:derive("NutriInfoPanel")
function NutriInfoPanel:new(x, y, w, h, playerNum)
    local o = ISPanelJoypad:new(x, y, w, h)
    setmetatable(o, self); self.__index = self
    o.playerNum = playerNum
    o.char      = getSpecificPlayer(playerNum)
    o:noBackground()
    return o
end
function NutriInfoPanel:initialise() ISPanelJoypad.initialise(self) end
function NutriInfoPanel:render()     ISPanelJoypad.render(self) --[[ draw rows ]] end

if not NutriInfoTab_wrapped then
    NutriInfoTab_wrapped = true
    local TAB, VIEW = "NutriMod", "nutriModView"

    local origCreate = ISCharacterInfoWindow.createChildren
    function ISCharacterInfoWindow:createChildren()
        origCreate(self)
        self[VIEW] = NutriInfoPanel:new(0, 8, self.width, self.height - 8, self.playerNum)
        self[VIEW]:initialise()
        self[VIEW].infoText = getTextOrNull("UI_NutriMod_TabTooltip")
        self.panel:addView(getText("UI_NutriMod_Tab"), self[VIEW])
    end

    local origTorn = ISCharacterInfoWindow.onTabTornOff
    function ISCharacterInfoWindow:onTabTornOff(view, window)
        if self.playerNum == 0 and view == self[VIEW] then
            ISLayoutManager.RegisterWindow("charinfowindow.NutriMod", ISCollapsableWindow, window)
        end
        origTorn(self, view, window)
    end

    local origSave = ISCharacterInfoWindow.SaveLayout
    function ISCharacterInfoWindow:SaveLayout(name, layout)
        origSave(self, name, layout)
        local v = self[VIEW]
        if v and v.parent == self.panel then
            layout.tabs = layout.tabs and (layout.tabs .. "," .. TAB) or TAB
            -- deliberately NOT setting layout.current = TAB: vanilla RestoreLayout
            -- resolves it through xpSystemText[...], which is nil for a mod tab
            if v == self.panel:getActiveView() then layout.current = nil end
        end
    end

    local origRestore = ISCharacterInfoWindow.RestoreLayout
    function ISCharacterInfoWindow:RestoreLayout(name, layout)
        origRestore(self, name, layout)   -- vanilla ignores an unknown name in layout.tabs
    end
end
```

The one correction over AutoCook is the `layout.current` handling: vanilla's `RestoreLayout` at `install:client/XpSystem/ISUI/ISCharacterInfoWindow.lua:286-288` does `self.panel:activateView(xpSystemText[layout.current])`, and `xpSystemText["NutriMod"]` is nil, so writing the mod tab into `layout.current` hands `activateView(nil)` to `ISTabPanel`.

### 4. A status-icon column

No vanilla route exists (sibling rows 23-24). The shape is an ordinary `ISUIElement:derive` added to `UIManager`, anchored either at a fixed inset from `getPlayerScreenLeft/Top/Width/Height(playerNum)` or, if `MoodlesUI` clears the exposure test, under the vanilla stack by reading `MoodlesUI.getInstance():getX()` / `:getY()` / `:getHeight()`. Icons load through `getTexture("media/ui/<vendor>/<Name>.png")` behind an `if not tex` fallback, exactly as `ws:2867431511/…/ISSSBar.lua:417-419` does. Stacking is the framework's only real advantage here, per the sibling.

### 5. The alternative that writes no panel at all

`SimpleStatus` on this machine exposes `SimpleStatus:addStat(name, {valueFn = f, type = …, title = …, icon = …, ruler = {…}}, reverse)` at `ws:2867431511/mods/SimpleStatus/42.20/media/lua/client/SimpleStatus.lua:37-65`, and `SimpleStatus:addCharacterStat` beside it. A client file that tests `type(SimpleStatus) == "table" and type(SimpleStatus.addStat) == "function"` and registers each mod nutrient gets a bar, an icon slot, a per-stat visibility tick and a place in that mod's saved config for a handful of lines — at the cost of a soft dependency on a workshop mod whose API is undocumented and whose 42.20 folder is three weeks old. Worth costing as a *supplement* to the mod's own panel, never as the only surface.

## Claims candidates

Each line is one fact, its cite, grade C, and its bound. Corpus rows are dated snapshots of 2026-09-27.

1. A mod panel that must be movable and collapsible derives `ISCollapsableWindow`, which is `ISPanel:derive` and supplies the title bar, close/collapse/pin buttons, two resize widgets and an unconditional drag. — `install:client/ISUI/ISCollapsableWindow.lua:9,26-93,206-217,270-280`; bound: C-only; install read 2026-09-27.
2. `ISPanel` does not drag unless `moveWithMouse` is set: its `:new` leaves the flag false and `onMouseDown` returns `isWantMouseEvents()` instead of starting a drag. — `install:client/ISUI/ISPanel.lua:113,49-62`; bound: C-only.
3. An `ISUIElement`'s `update`, `prerender` and `render` are empty stubs driven by the Java object and run only while the element is in `UIManager`, so `removeFromUIManager()` is the complete early-out for a hidden panel. — `install:client/ISUI/ISUIElement.lua:1610-1620`; `install:client/XpSystem/ISUI/ISCharacterInfoWindow.lua:174-180`; bound: C-only.
4. `createChildren` is called from inside `instantiate`, so a derive's children are built on the first `addToUIManager`, `setVisible` or `getIsVisible` call rather than at construction. — `install:client/ISUI/ISUIElement.lua:993-1010`; bound: C-only.
5. `ISUIElement:wrapInCollapsableWindow(title, resizable, subClass)` converts a content panel into a titled collapsable window in one call, removing it from `UIManager` and re-parenting it below the title bar. — `install:client/ISUI/ISUIElement.lua:1754-1773`; bound: C-only.
6. Vanilla window geometry is persisted through `ISLayoutManager.RegisterWindow(name, funcs, target)`, which restores immediately at registration and is the only route into `layout.ini`. — `install:client/ISUI/ISLayoutManager.lua:6-13,125-186`; bound: C-only.
7. `ISCollapsableWindow` already implements the `RestoreLayout`/`SaveLayout` pair that `ISLayoutManager` needs, including the collapsed state, so a collapsable window can be registered with `ISCollapsableWindow` as its `funcs`. — `install:client/ISUI/ISCollapsableWindow.lua:336-354`; bound: C-only.
8. `layout.ini` is sectioned by screen resolution, so a window's saved geometry does not carry across a resolution change. — `install:client/ISUI/ISLayoutManager.lua:82-96,169-186`; bound: C-only.
9. `layout.ini` is written only from `Events.OnPostSave`, and on a client both `OnPostSave` trigger sites are in the exit path of `IngameState.updateInternal` — the clean-exit route and the `serverDisconnected` route — so panel geometry persisted this way is written at quit and lost on a hard crash. — `install:client/ISUI/ISLayoutManager.lua:191-232`; `jar:IngameState.updateInternal @207 L1370`, `@1557 L1575`; bound: C-only; the cadence claim is a read of the trigger sites and not a run.
10. `GameWindow.save` on a client triggers only `'OnSave'` and returns before the single-player save body. — `jar:GameWindow.save(Z)V @50-@74 L1174-L1179`; bound: C-only.
11. A mod adds a rebindable key to the main Keybinding page by inserting a `{value, key}` row into the global `keyBinding` table, which `MainOptions.loadKeys` walks into `getCore():addKeyBinding`. — `install:shared/keyBinding.lua:6`; `install:client/OptionScreens/MainOptions.lua:3473-3518`; `install:client/Foraging/ISSearchManager.lua:1472-1481`; bound: C-only.
12. The deadline for that insertion is `Events.OnMainMenuEnter`, because `MainScreen:create()` calls `mainOptions:create()` which calls `loadKeys()`. — `install:client/OptionScreens/MainScreen.lua:694,2178`; `install:client/OptionScreens/MainOptions.lua:403`; bound: C-only.
13. A stale `keysB42.ini` line for a removed mod is ignored, because the reader applies a line only when the name is in `knownKeys`, which is built from the live `keyBinding` table. — `install:client/OptionScreens/MainOptions.lua:3543,3563,3483-3514`; bound: C-only.
14. `PZAPI.ModOptions` is a vanilla shipped Lua API with a `keybind` option type, and it has no Java half at all. — `install:client/PZAPI/ModOptions.lua:182-204,247-253`; `jar:jar-wide grep ModOptions` → no class contains that literal; bound: C-only.
15. `PZAPI.ModOptions:load()` is called by vanilla only from `MainOptions:addModOptionsPanel()`, so a session in which the player never opens the options screen runs on defaults unless the mod calls `load()` itself. — `install:client/OptionScreens/MainOptions.lua:2795-2796`; `ws:3437629766/mods/CleanUI/42.19/media/lua/client/ISUI/CleanUI_ModOptions.lua:31-43`; bound: snapshot, corpus read 2026-09-27.
16. `ModOptions.ini` preserves the lines of pages and ids it does not recognise, so an absent mod's settings survive a session without it. — `install:client/PZAPI/ModOptions.lua:286-289,329-331`; bound: C-only.
17. A `PZAPI.ModOptions` keybind is excluded from `keysB42.ini` and from the keybinding-page column layout, because its row carries `isModBind = true`. — `install:client/OptionScreens/MainOptions.lua:2998,3019,420,3926`; bound: C-only.
18. `getCore():isKey(name, key)` is the vanilla idiom for testing a bound key in a handler, and it also matches the alternate code, which `key == getCore():getKey(name)` does not. — `install:server/XpSystem/XpUpdate.lua:147-163`; `jar:Core` method list (`isKey(String,Integer)Z`, `getAltKey(String)I`); bound: C-only.
19. `getTexture(name)` is one call to `Texture.getSharedTexture` and resolves `name` against the merged `media/` root, so a mod's own PNG is reached as `getTexture("media/ui/<file>.png")`. — `jar:LuaManager$GlobalObject.getTexture @0 L7189`; `ws:2867431511/mods/SimpleStatus/42.20/media/lua/client/ISSSBar.lua:417-419`; bound: C-only for the jar arm, snapshot for the corpus arm.
20. `getTexture` returns nil rather than raising on a dedicated server with no GUI and on any load exception, so a texture load belongs in a `client/` file behind a nil check. — `jar:Texture.getSharedTexture(Ljava/lang/String;I) @12 L425, @37 L432`; bound: C-only.
21. The whole inventory-item tooltip is built in Java: `ISToolTipInv:render` calls `self.item:DoTooltip(self.tooltip)` twice — once under `setMeasureOnly(true)` to size the panel and once to draw — and there is no other Lua method in the path. — `install:client/ISUI/ISToolTipInv.lua:43-107`; `jar:InventoryItem.DoTooltip @0 L735`; bound: C-only.
22. The tooltip's height is set by Java from its own content plus `padBottom`, before any Lua sees it, and a width under 150 is forced up to 150. — `jar:InventoryItem.DoTooltipEmbedded @4236-@4240 L1164`, `@4243-@4261 L1166-L1167`; bound: C-only.
23. `InventoryItem.DoTooltipEmbedded` skips its render/`endLayout`/`setHeight` tail when a `Layout` is passed in, which is how the engine composes sub-item tooltips inside one box. — `jar:InventoryItem.DoTooltipEmbedded @4203 L1159`; bound: C-only.
24. The vanilla food tooltip's nutrition block has three gates, not one: the debug arm (`Core.debug` with `DebugOptions.tooltipInfo`), an internal flag, and `hasTrait(CharacterTrait.NUTRITIONIST)` or `NUTRITIONIST2`. — `jar:Food.DoTooltip @1241-@1288 L1521`, block start `@1291 L1522`; bound: C-only. This refines the library's single-gate statement (#0546, #0547) and means a `-debug` client can show the block without the trait.
25. One wrap of `ISToolTipInv.render` covers every inventory-item tooltip in the game, because all ten construction sites funnel through that class. — `install:client/ISUI/ISInventoryPane.lua:854`, `ISInventoryPaneContextMenu.lua:3767`, `ISEquippedItem.lua:586`, `client/Hotbar/ISHotbar.lua:270`, `ISTradingUI.lua:565`, `ISWorldObjectContextMenu.lua:2624`, `client/Fluids/ISFluidBar.lua:220`, `client/Entity/ISUI/Controls/ISEnergyBar.lua:90`, `client/Entity/ISUI/CraftRecipe/ISCraftInventoryPanel.lua:48`, `ISXuiSkin.lua:236`; bound: C-only.
26. The crafting item-slot tooltip is a second, separate route with its own Lua wrap point, `ISItemSlot.drawTooltip(_itemSlot, _tooltip)`. — `install:client/Entity/ISUI/Controls/ISItemSlot.lua:545-550`; `install:client/Entity/ISUI/Components/Crafting/ISToolTipItemSlot.lua:3,152`; bound: C-only.
27. `ISToolTipInv:render` does nothing at all while a context menu is flagged visible, so a wrap that draws after the original must replicate that guard. — `install:client/ISUI/ISToolTipInv.lua:45`; bound: C-only.
28. `CleanUI` ships no `ISToolTipInv.lua` and no copy of any `ISUI` base class, `ISTabPanel`, `ISLayoutManager`, `ISCharacterInfoWindow` or `ISHealthPanel`; its 42.19 tree occupies 43 vanilla relative paths, all inventory, loot, fixing or `UI.json`. — `find` + per-file existence test over `ws:3437629766/mods/CleanUI`; bound: snapshot, corpus read 2026-09-27.
29. `CleanUI`'s own `ISInventoryPane.lua` and `ISInventoryPaneContextMenu.lua` still construct `ISToolTipInv`, so a wrap of `ISToolTipInv.render` survives `CleanUI` while a wrap of `ISInventoryPane` would be replaced. — `ws:3437629766/mods/CleanUI/42.19/media/lua/client/ISUI/ISInventoryPane.lua:3552`, `ISInventoryPaneContextMenu.lua:4249`; bound: snapshot, corpus read 2026-09-27.
30. Under `CleanUI` a multi-item stack's tooltip is built from one representative item plus `tooltip:setWeightOfStack(w)`, so a tooltip wrap sees a display item and not the group. — `ws:…/42.19/…/ISInventoryPane.lua:3526-3533,3563`; bound: snapshot, corpus read 2026-09-27.
31. A `UIElement`'s render-time clip is parent-based (`parent.maxDrawHeight`, `parent.renderClippedChildren`), so a top-level element added to `UIManager` is not clipped to its own rect by that method. — `jar:UIElement.render @19-@125 L1679-L1686`; bound: C-only; whether another scissor is set elsewhere in the frame was not traced.
32. `ISCharacterInfoWindow` has no tab registry: its five tabs are hard-coded in `createChildren`, again in `RestoreLayout`'s `floating` table and again in `SaveLayout`'s five parent tests. — `install:client/XpSystem/ISUI/ISCharacterInfoWindow.lua:127-148,211-231,298-327`; bound: C-only.
33. A mod tab is added by wrapping `createChildren` to call `self.panel:addView(getText(...), view)`, and the wrap must be installed at file scope because the window is built on `Events.OnCreatePlayer`. — `ws:3388721641/mods/AutoCook/common/media/lua/client/ISCharacterInfoWindow_AddTab.lua:6-14`; `install:client/ISUI/PlayerData/ISPlayerDataObject.lua:93-96`; `install:client/ISUI/PlayerData/ISPlayerData.lua:203`; bound: C-only for the install arm, snapshot for the mod arm.
34. A mod tab must not write its own name into `layout.current`, because vanilla's `RestoreLayout` resolves that key through `xpSystemText[...]`, which is nil for any name vanilla does not own. — `install:client/XpSystem/ISUI/ISCharacterInfoWindow.lua:286-288`; `install:server/XpSystem/XpSystem_text.lua:1-10`; `ws:3388721641/.../ISCharacterInfoWindow_AddTab.lua:37-39`; bound: C-only; the failure was derived from the two files and not observed.
35. `ISTabPanel` keys `getView`, `activateView` and `toggleView` on the tab's displayed name, so a mod tab's name is a translated string and the same string is the toggle argument. — `install:client/ISUI/ISTabPanel.lua:401,438,484-489`; `install:client/XpSystem/ISUI/ISCharacterInfoWindow.lua:53`; bound: C-only.
36. `ISHealthPanel` and `ISCharacterScreen` expose no extension point: `ISHealthPanel`'s only handler-list API, `checkItems(handlers)`, takes a list built locally by `doBodyPartContextMenu`. — `install:client/XpSystem/ISUI/ISHealthPanel.lua:1762-1794,1796-1799`; `install:client/XpSystem/ISUI/ISCharacterScreen.lua` method list; bound: C-only.
37. `OnPostUIDraw` fires once per UI render, after every element has rendered, gated on the Lua thread being the UI default thread. — `jar:UIManager.render @659-@668 L404-L405`; bound: C-only.
38. `OnRenderTick` is the per-rendered-frame hook and `GameWindow.onRender`'s entire body is its trigger. — `jar:GameWindow.onRender @0 L876`; bound: C-only.
39. `zombie.ui.MoodlesUI` extends `zombie/ui/UIElement`, its `getInstance()` is public static, and `clientW`/`clientH` are public fields — so the vanilla moodle stack's box is readable as an anchor for a mod's own icon column even though the class offers no mutator. — `jar:MoodlesUI` class + scratch flag parse; `jar:UIElement` method list; bound: C-only; exposure was not confirmed by the strict membership test (#0963), and this only adds an anchor read to the sibling report's rows 23-24.
40. Kahlua's handling of a public Java *instance* field is unread here: no vanilla Lua file reads or writes one, and every Java field read from Lua in the tree is a static enum constant. — `grep -rn "\.isCookable\b|square\.x\b|\.padBottom" install:media/lua` → no Java-field hit; `install:client/DebugUIs/DebugMenu/General/ISStatsAndBody.lua:35` etc. for the static form; bound: C-only. This is what blocks the `ObjectTooltip.padBottom` route for the tooltip.
41. `ObjectTooltip` is `public final … extends zombie/ui/UIElement`, its `padLeft/padTop/padRight/padBottom` are `public int`, and its drawing surface is `DrawText`/`DrawTextCentre`/`DrawTextRight`/`DrawValueRight*`/`DrawTextureScaled*`/`DrawProgressBar`/`adjustWidth`/`beginLayout`/`endLayout`/`getLineSpacing`/`getFont`. — `jar:ObjectTooltip` method list + scratch flag parse; bound: C-only.
42. The installed `SimpleStatus` item has five version folders and 360 files as of 2026-09-27, and the tree `42.20.4` resolves to is `42.20/`, not `42.16/`. — `ws:2867431511/mods/SimpleStatus/` directory listing; `ws:…/42.20/mod.info`; bound: snapshot, corpus read 2026-09-27. **Correction candidate against #1467**, which records four version folders, 298 files and one download mtime.
43. The resolved `42.20/` copy of `SSBar:prerender` caches: it recomputes bar values only when `self.timer % 10 == 0` and resizes only when `self.timer == 60`, where the `42.16/` copy called `prepareBarInfo()` unconditionally every frame. — `ws:2867431511/mods/SimpleStatus/42.20/media/lua/client/ISSSBar.lua:452-476` vs `…/42.16/media/lua/client/ISSSBar.lua:452-465`; bound: snapshot, corpus read 2026-09-27. **Correction candidate against #1477 and #1114**, whose "no cache anywhere on the path" and per-frame read counts are readings of the `42.16` copy.
44. The resolved `42.20/` copy of `SimpleStatus` exposes a documented registration API a consumer mod can use instead of writing a panel: `SimpleStatus:addStat(name, stat, reverse_stat)` requiring `stat.valueFn(player)`, and `SimpleStatus:addCharacterStat(name, key, opts)` reading `CharacterStat.REGISTRY`. — `ws:2867431511/mods/SimpleStatus/42.20/media/lua/client/SimpleStatus.lua:37-105`; bound: snapshot, corpus read 2026-09-27. The `42.16` copy of that file is 34 lines and has no `addCharacterStat`.
45. `SimpleStatus` persists its panel position by writing player modData and calling `player:transmitModData()` on every drag release, which is the wipe-and-replace hazard (#1151) once per drag. — `ws:2867431511/mods/SimpleStatus/42.20/media/lua/client/ISSSBar.lua:18-36,478-483`; bound: snapshot, corpus read 2026-09-27.
46. `CleanUI` uses `OnTick` only as a self-removing one-shot or a deferred action queue, never as a steady loop, and its 42.19 tree registers 5 `OnGameBoot`, 5 `OnGameStart`, 5 `OnTick`, 1 `OnKeyPressed`, 1 `OnCreatePlayer` and 1 `OnContainerUpdate` handler. — `ws:3437629766/mods/CleanUI/42.19` grep; `…/CleanUI/CleanUI_InventoryUIModeSwitcher.lua:413,445`; bound: snapshot, corpus read 2026-09-27.
47. No third-party `ModOptions` framework mod is installed in the 182-item corpus, so `PZAPI.ModOptions` is the only options API a mod can rely on here. — `find . -maxdepth 3 -type d -iname "*modoption*"` over `D:\SteamLibrary\steamapps\workshop\content\108600` → 0; bound: snapshot, corpus read 2026-09-27.
48. `CleanUI` hard-`require`s `NeatUI_Framework`, a second client-only UI toolkit resident on this machine: 11 Lua files, a `NeatTool` global of 3-patch/9-patch/percentage/text draw helpers, two `ISUIElement` scroll-view derives, and an `ISUIElement` compatibility shim that defines `getCentreX`/`getSelfCenterX` only when absent. — `ws:3437629766/mods/CleanUI/42.19/mod.info` (`require=\NeatUI_Framework`); `ws:3508537032/mods/NeatUI_Framework/42/media/lua/client/neatui_framework/`; bound: snapshot, corpus read 2026-09-27.
49. There is no engine-side keybind registration or mod-key option: `getOptionModsKey` and `registerKeyBind` are absent jar-wide, and `Core`'s key surface is `getKey`/`getAltKey`/`isKey`/`getKeyBinding`×2/`addKeyBinding`/`reinitKeyMaps`. — `jar:jar-wide grep getOptionModsKey`, `jar:jar-wide grep registerKeyBind` → no class contains that literal; `jar:Core` method list; bound: C-only.
50. A mod panel that wants raw key events on the element itself sets `setWantKeyEvents(true)` and implements `onKeyPress`/`onKeyRepeat`/`onKeyRelease`, which are the names the Java `UIElement` dispatches. — `install:client/ISUI/ISUIElement.lua:1828-1835`; `jar:UIElement` method list; bound: C-only; no vanilla top-level panel uses this route — every vanilla toggle key goes through `Events.OnKeyPressed`.

## Not read

- No process was booted: nothing here is a run. The tooltip-append shape, the panel shape and the tab shape are all untested, and the two most load-bearing unknowns are whether an out-of-bounds draw from a top-level element is visible and whether Kahlua permits a write to `ObjectTooltip.padBottom`.
- The strict exposure test (the `LuaManager$Exposer` class-set dump, #0963) was not re-run for `ObjectTooltip`, `MoodlesUI`, `CharacterStat` or `UIElement`. `ObjectTooltip` is proven reachable indirectly, because vanilla Lua calls `ObjectTooltip.new()`; the other three are grep hits in the exposer's constant pool only.
- The joypad half of every surface was skipped: `ISPanelJoypad`'s navigation model, `setJoypadFocus`, `JoypadState`, `ISCharacterInfoWindow:onJoypadDown`'s bumper tab cycling, and the controller path through `ISToolTipInv` (`self.contextMenu.joyfocus`) were read only far enough to name them.
- `ISXuiSkin` and the `Xui` layer that wraps `ISToolTipInv` at `install:client/ISUI/ISXuiSkin.lua:236` were not read; whether an Xui skin changes the tooltip route is unknown.
- `ISInventoryPane:doTooltip`'s own body, vanilla and CleanUI, was read only around the `ISToolTipInv` construction; the rest of both 2869- and 5972-line files was not.
- `MainOptions`'s keybinding page beyond `loadKeys`, the mod-options panel and `centerKeybindings`: the duplicate-bind dialog, `ISSetKeybindDialog`, `upgradeKeysIni` and the `keys.ini`→`keysB42.ini` migration were not followed.
- The `Registries.MOODLE_TYPE` / `CharacterStat.REGISTRY` registries were noticed (via `SimpleStatus:addCharacterStat`) and not investigated; whether a mod can register a `CharacterStat` is a separate question this report does not touch.
- Font scaling: `getCore():getOptionFontSizeReal()` and `getOptionMoodleSize()` were read only where `ISCollapsableWindow` and `MoodleFramework` use them; whether a live font-size change re-lays-out a mod panel was not established.
- Split screen, controller input and the `getNumActivePlayers() > 1` paths were named but not traced.
- `mod.info` load-order declarations for the resident stack, the join checksum consequences of a wrapped vanilla class, and the packaging lint are `mod-anatomy`/`packaging` questions and were not re-read here.
- No measurement of frame time, draw cost or Lua call counts exists in this repository's harness, so every cadence statement here is a count or a code shape and never a cost.
