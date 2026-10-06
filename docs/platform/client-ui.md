# Client UI
Verified against 42.20.4 (b0bbce05d5) · 2026-10-06 · scope: the client-side interface a mod builds on this build — the `ISUI` panel toolkit, window geometry and `layout.ini`, keybinds and `PZAPI.ModOptions`, textures, the inventory-item tooltip, the character-info window, the UI events and their cadence, and the Java UI classes a mod can read; the moodle routes and what a panel may believe are handed off to `ui-and-moodles.md`, and the push behind any number a panel draws to `mp-model.md`.

## Rules

- Wrap `ISToolTipInv.render` once and repeat the context-menu test before drawing after the original: the tooltip body is built in Java inside one render method and that method draws nothing while a context menu is flagged visible [#2516/C/inference] [#2490/C/C-only] [#2496/C/C-only].
- Set the height of the band you add and paint its frame before you draw below Java's box: the panel's height is set from Java's measured tooltip and its background is painted from that height before the draw pass, so a line drawn below it after the original returns has no background [#2517/C/inference] [#2490/C/C-only] [#2491/C/C-only].
- Register a mod window through `ISLayoutManager.RegisterWindow` with `ISCollapsableWindow` as its funcs: the layout manager restores the window at registration and saves it into `layout.ini`, and the collapsable window already supplies the restore and save pair [#2518/C/inference] [#2473/C/C-only] [#2474/C/C-only].
- Call `PZAPI.ModOptions:load()` yourself, once and after creating your page, before you read an option: vanilla loads `ModOptions.ini` only as the main screen is built and a load applies a saved value only to a page that already exists, so a value read earlier is the default [#2519/C/inference] [#2482/C/C-only] [#2528/C/snapshot/unverified].
- Insert a keybind row at file scope or on `OnGameBoot`, before `OnMainMenuEnter`: `loadKeys` reads the `keyBinding` table when the main screen is built, and a row added after that build is not a known key until the next one [#2520/C/inference] [#2478/C/C-only] [#2479/C/C-only].
- Add a character-info tab by wrapping `createChildren` at file scope, and never write the tab's name into `layout.current`: the window is built on player creation, and vanilla's restore resolves `layout.current` through a table that has no entry for a mod tab [#2521/C/inference] [#2501/C/C-only] [#2502/C/C-only].
- Load a texture in a client file behind a nil check: `getTexture` returns nil on a dedicated server with no server GUI and on any load failure [#2522/C/inference] [#2489/C/C-only].

## How it works

Everything on this page runs on a client.
A dedicated server builds no panel, draws no tooltip and loads no texture for a mod, so the whole surface lives in `media/lua/client/` files, and nothing here needs a side branch beyond that folder.
The surface is reached in two ways: by deriving a vanilla widget class and adding the result to the UI manager, or by wrapping a vanilla method in place.
The first touches nothing anyone else owns; the second is a monkey-patch, and the wrapper rules on [lua-platform.md](lua-platform.md#dev-loop) apply to it in full.
No vanilla file needs shadowing for any shape below, and a file at a vanilla relative path is the one thing a UI mod should never ship, because a resident interface mod already ships dozens of them.
The sections below run from the widget a mod derives, through where its state is kept and how a player reaches it, to the two vanilla surfaces a mod wraps rather than derives, and end on the Java classes underneath.

<a id="panel-toolkit"></a>
### The panel toolkit

The Lua widget set is a tree of derives rooted at `ISUIElement`, and a mod's panel is one more derive added to the UI manager.
`ISPanel` adds a background and a border, `ISPanelJoypad` adds a controller navigation model, and `ISCollapsableWindow` adds everything a floating window needs.

`ISCollapsableWindow` is an `ISPanel` derive that supplies a title bar, a close button, an info button, a pin and collapse pair and two resize widgets, and its mouse-down and mouse-move overrides drag it with no `moveWithMouse` test, so a panel derived from it is movable and collapsible without code of its own [#2467/C/C-only].
That makes "movable and collapsible" something a mod inherits rather than writes.

`ISPanel` does not drag unless `moveWithMouse` is set: its constructor sets the flag false, and its mouse-down handler then returns the element's want-mouse-events flag instead of starting a drag [#2468/C/C-only].
A bare panel that should move therefore sets the flag itself, and a panel that should stay put leaves it alone.
A lockable panel toggles the same flag, which is all a lock amounts to.
A panel derived from the collapsable window has no such flag to set, so a lock on it means overriding the window's own mouse handlers.

An `ISUIElement`'s `update`, `prerender` and `render` are empty Lua stubs that the Java element calls through its Lua table when the UI manager renders it, and the UI manager renders only the elements on its list, so `removeFromUIManager` is the complete early-out for a hidden panel, which is how the character-info window closes so that `update` is not called [#2469/C/C-only].
A panel that is off for most of a session should leave the list on close and rejoin it on open.

`createChildren` runs inside `instantiate`, and `instantiate` is first reached from `addToUIManager`, `setVisible` or `getIsVisible` on an element that has no Java object yet, so a derive's children are built at that first call rather than at construction [#2470/C/C-only].
A constructor that reads a child widget therefore reads nil, and a field the children need must be set before the first of those three calls.
The same rule is why a wrapped `createChildren` runs when the window is first shown or added, not when its class is loaded.

`ISUIElement:wrapInCollapsableWindow(title, resizable, subClass)` builds a collapsable window sized for the content plus the title bar and the resize widget, removes the content panel from the UI manager and re-parents it below the title bar, so a content panel becomes a titled collapsable window in one call [#2471/C/C-only].
It is the shortest route from a content panel to a window, and it hands back the window, which is the object to register for geometry and to add to the UI manager.
Either route ends in the same object: a window on the UI manager's list whose callbacks the engine drives every frame it is shown.
A mod that needs one panel per local player builds one per player number and keeps each on its own viewport through the element's per-player render filter.

A second toolkit is resident on this server beside vanilla's.
`CleanUI` hard-requires `NeatUI_Framework`, a second client-only UI toolkit resident on this machine: 11 client Lua files defining a `NeatTool` global of 3-patch, 9-patch, percentage and text draw helpers, three `ISUIElement` scroll-view derives, and an `ISUIElement` compatibility shim that guards ten centre helpers, of which `getCentreX`, `getCentreY` and `getSelfCenterY` are the three the vanilla `42.20` `ISUIElement` lacks and the shim therefore adds [#2472/C/snapshot].
The shim is the part that reaches a mod: on this build those three methods appear on the vanilla base class every panel derives from whenever `CleanUI` is loaded, and a mod that calls one of them works only beside it.
The helpers are free to call but are a dependency on a workshop item, which a mod that ships to servers without `CleanUI` cannot assume.

<a id="layout"></a>
### Window geometry and `layout.ini`

Vanilla persists window geometry through one module, and a mod window can join it with a single call.
The alternative a resident viewer uses, writing its position into player modData, is cheaper to get right but crosses the wire on every drag ([simplestatus.md](../facts/other-mods/simplestatus.md#mp)).

`ISLayoutManager.RegisterWindow(name, funcs, target)` stores the window under its name and restores its saved layout at once, outside the tutorial game mode, has no unregister, and `ISLayoutManager`'s own reader and writer are what open `layout.ini` [#2473/C/C-only].
Window names are flat strings shared with every vanilla window, so a mod's name carries a vendor prefix.

`ISCollapsableWindow` implements the `RestoreLayout` and `SaveLayout` pair the layout manager calls, saving position, size and visibility through the default window functions plus a pin key that also restores the collapsed state, so a collapsable window registers with `ISCollapsableWindow` itself as its funcs, as vanilla's torn-off character-info tabs do [#2474/C/C-only].

`layout.ini` is sectioned by screen resolution: the reader files each window line under a `[WxH]` header, and restore and save both match the section to the current screen width and height, so a window's saved geometry does not carry across a resolution change [#2475/C/C-only].
A player who moves between a laptop and a monitor keeps two positions for the same panel, one per resolution, which is usually what they want.

`ISLayoutManager` writes `layout.ini` from its `OnPostSave` handler, registered on `Events.OnPostSave`, and every `OnPostSave` trigger site in the jar ends the session: `GameWindow.exit` fires it twice after the exit save, and `IngameState.updateInternal` fires it in its clean-exit branch and in its exception handler, which saves, fires the event and disconnects a client with `crash`; so window geometry persisted this way is written when a session ends, never during play, and a killed process loses it [#2476/C/C-only].
On a client with `GameClient.clientSave` set, `GameWindow.save` saves the world map and the visited map, triggers `OnSave` and returns before the save body that writes the world [#2477/C/C-only].
A live client confirms both ends: after a first registration under a name the file does not carry the mod's `stats.restoredVisible` read false, the panel hidden [#3215/M/n=2], and at a quit to desktop the file's mtime fell between the quit and the exit, the file carrying the mod panel's line [#3216/M/n=1]; a second boot wrote the same lines and again left `ModOptions.ini` empty [#3230/M/n=2], and a third, on the build that instantiates the panel before its registration, wrote the same panel line [#3252/M/n=3].
So the layout file is the cheap, local and late route: nothing crosses the wire, nothing is written during play, and a crash between two clean exits forgets every move made in that session.
Player modData is the immediate and remote route, and its cost is the transmit hazard described on [mp-model.md](mp-model.md#wipe-and-replace).
A mod can therefore keep its panel's geometry in the layout file with no code of its own beyond the registration, accepting that the file is written only when a session ends ([#2476/C/C-only], [#3216/M/n=1]).
The geometry rule at the top of this page follows from these rows.
The two routes are not exclusive: a mod can register with the layout manager for the position and keep only what must survive a crash in player modData.
Neither route is authoritative over anything but the panel's own placement, so neither touches the numbers the panel draws.

<a id="keybinds"></a>
### Keybinds and mod options

A mod key has two vanilla homes on this build: a row on the main keybinding page, or a keybind option on the mod's own options page.
Both are pure Lua; the engine knows a key only as a name and a code handed to it by Lua.
Of the two homes, the options page is the one that also carries the mod's other settings, so a mod with any option at all has a page already and its key belongs there.
The main keybinding page suits a key a player expects to find beside vanilla's own panel keys.

A mod adds a rebindable key to the main keybinding page by inserting a `{value, key}` row into the global `keyBinding` table: `MainOptions.loadKeys` walks that table, passes every row whose value does not start with `[` to `getCore():addKeyBinding` and records it as a known key, and vanilla inserts its own search-mode bind the same way from an `OnGameBoot` handler [#2478/C/C-only].
A row whose value starts with `[` is a section header on the page and carries no key.
`loadKeys` runs whenever the main screen is built: `MainScreen` is built from `Events.OnMainMenuEnter` and, in a game, from `Events.OnGameStart`, its `instantiate` calls `mainOptions:create`, and `MainOptions:create` calls `loadKeys`, so a `keyBinding` row must exist before `OnMainMenuEnter` to reach the main-menu build [#2479/C/C-only].
A stale `keysB42.ini` line for a key no `keyBinding` row defines any more is ignored, because the reader applies a line only when its name is in the known-keys table `loadKeys` builds from the live `keyBinding` table [#2480/C/C-only].
Uninstalling a mod therefore leaves its saved binding behind in the file, harmless and unread.

`PZAPI.ModOptions` is a shipped vanilla Lua API whose option pages take a keybind option through `Options:addKeyBind(id, name, key, tooltip)`, and it has no Java half: the literal `ModOptions` is in no class of the jar [#2481/C/C-only].
Vanilla loads `ModOptions.ini` through `PZAPI.ModOptions:load()` from `MainOptions:addModOptionsPanel`, which `MainOptions:create` runs when at least one mod page exists, as the main screen is built on `OnMainMenuEnter` and on `OnGameStart`; `load()` applies a saved line only to a page and option already created, and `CleanUI` makes its own call of `load()`, once, inside a protected call [#2482/C/C-only].
Until one of those loads runs, every option reads the default its page was created with; that no other vanilla Lua loads the file is unverified ([Open](#open)).
A quit to desktop does not write `ModOptions.ini`: after a session in which the mod's `modOptions.stats` read one load and no failure, the file stood at 0 bytes [#3218/M/n=1], as it did again on a third boot [#3253/M/n=2].
A page created after that build is missing from the options screen until the next one, which is a second reason to create the page at file scope.
`PZAPI.ModOptions:load()` keeps every `ModOptions.ini` line whose page or option id it does not recognise and `save()` writes those lines back after the known options, so an absent mod's settings survive a session without it; `save` writes each kept line with no line terminator of its own, so a single kept line round-trips intact and two or more come back joined on one line [#2483/C/C-only].
A mod that is switched off for a session and back on can therefore lose its saved values when another absent mod's lines share the file.
A `PZAPI.ModOptions` keybind is drawn on the mod options page as a row flagged `isModBind`, which keeps it out of the `keysB42.ini` rewrite `MainOptions:create` makes and out of the keybinding page's column centring, while the save on Apply writes every row, mod binds included, under their label text and adds a core binding under that text for the session, and the file reader then ignores those lines because no `keyBinding` row carries that name [#2484/C/C-only].
The mod-options value lives in `ModOptions.ini`; the stray `keysB42.ini` line is a side effect of the Apply save and nothing reads it back from the file.

`getCore():isKey(name, key)` is the vanilla idiom for testing a bound key in a handler, and it matches the binding's alternate key as well as its main key, which a comparison against `getCore():getKey(name)` does not [#2485/C/C-only].
A `PZAPI.ModOptions` keybind is not a core binding by name, so its handler compares the key code against the option's `getValue()` instead.
No installed workshop item is a third-party mod-options framework: no mod id, name or folder in the census names one, so `PZAPI.ModOptions` is the only options API a mod can rely on here [#2486/C/snapshot].
A panel that wants raw key events on the element itself calls `setWantKeyEvents(true)` and defines `onKeyPress`, `onKeyRepeat` and `onKeyRelease`, the Lua names the Java `UIElement` looks up on its table and calls; every vanilla toggle key instead goes through `Events.OnKeyPressed` [#2487/C/C-only].
The event route reaches the handler whether or not the panel has focus, which is what a show-and-hide key needs.
The keybind and options rules at the top of this page follow from the build timing and the load behaviour above.
A handler on that event runs for every key press in the session, so it returns at once on any key that is not its own.

<a id="textures"></a>
### Textures and fonts

`getTexture(name)` is one call to `Texture.getSharedTexture` with the name as given, and vanilla and mods alike pass a path rooted at `media/`, so a mod's own PNG under its `media/ui` is reached as `getTexture("media/ui/<file>.png")` [#2488/C/C-only].
`Texture.getSharedTexture` returns nil rather than raising on a dedicated server with no server GUI and on any exception while loading, which it logs, so a texture load belongs in a client file behind a nil check [#2489/C/C-only].
The texture rule at the top of this page follows from that nil return.
A chain of fallbacks — the mod's own icon, then a vendor default, then a placeholder — is the shape the resident viewer uses, each step behind the same nil check.
Texture paths share one namespace with vanilla's and every other mod's, so a mod's images sit under a vendor subfolder of `media/ui`.
Fonts are the `UIFont` enum constants, and text is measured through `getTextManager()`; a measure taken at file scope is the value for the font size at load, and a later change to the font-size option does not move it.

<a id="tooltip"></a>
### The inventory-item tooltip

The tooltip is the most constrained surface on this page, because the engine draws it and Lua only hosts the drawing.
The whole inventory-item tooltip body is built in Java: `ISToolTipInv:render` calls the item's `DoTooltip` twice, once under `setMeasureOnly(true)` to size the panel and once to draw, sets the panel's height from the measured tooltip and paints the background from that height between the two, and `InventoryItem.DoTooltip` is a single call into `DoTooltipEmbedded` [#2490/C/C-only].
The tooltip's height is set by Java from its own laid-out content plus `padBottom` before any Lua sees it, and a width under 150 is forced up to 150 [#2491/C/C-only].
`InventoryItem.DoTooltipEmbedded` skips its layout render, `endLayout` and `setHeight` tail when a `Layout` is passed in, which is how the engine composes a sub-item's rows inside one tooltip box [#2492/C/C-only].

The food block a nutrition mod will sit beside has its own gate.
The food tooltip's nutrition block has three gates, any one of which shows it: the debug arm (`Core.debug` with the `tooltipInfo` debug option), a packaged food whose label the viewer can read (not Illiterate, not too dark to read, no `NoLabel` modData), and the character holding `CharacterTrait.NUTRITIONIST` or `NUTRITIONIST2`, so a client launched with the debug flag can show the block without the trait [#2645/C/C-only].
The trait's own standing as display-only is [body-and-weight.md](../facts/body-and-weight.md#traits)'s [#0546/C/snapshot].
A test that reads the tooltip on a harness client, which runs with the debug flag, can therefore see the block on a character with no Nutritionist trait.

The install constructs `ISToolTipInv` at ten sites — the inventory pane, its context menu, the equipped-item panel, the hotbar, the trading window, the world-object context menu, the fluid bar, the energy bar, the crafting inventory panel and the Xui skin — so one wrap of the class's render covers the item tooltip at every one of them [#2494/C/C-only].
The crafting item-slot tooltip is a second, separate route with its own panel class and its own Lua wrap point, the plain function `ISItemSlot.drawTooltip(_itemSlot, _tooltip)`, which calls the slot's resource or stored item's `DoTooltip` [#2495/C/C-only].
`ISToolTipInv:render` does nothing at all while a context menu is flagged visible, because its whole body sits inside a test of `ISContextMenu.instance.visibleCheck`, so a wrap that draws after the original must repeat that test [#2496/C/C-only].
A wrap that skips the test paints its band over an open context menu with no tooltip behind it.
The sentinel that keeps the wrap single belongs in a global of its own, for the reason [lua-platform.md](lua-platform.md#dev-loop) gives [#0943/C/C-only].
The wrap reaches `self.item`, the Java tooltip object `self.tooltip`, the character it was given and the whole `ISPanel` draw surface, which is everything a line of mod text needs.
The two tooltip rules at the top of this page follow from the Java-built body, the fixed height and the context-menu test above.
Everything a nutrition mod wants to say about a food therefore goes through one wrapped method and one band below the engine's box, and a mod can reach the screen that way because the band is framed and drawn after the original returns, while the in-box padding route rests on a field write Lua may not make ([#2517/C/inference], [#2510/C/snapshot/unverified]).
The band's text is the mod's own, so it carries the mod's own numbers rather than echoing the engine's.

The resident interface mod leaves this route alone.
`CleanUI`'s live `42.19` tree neither defines nor wraps `ISToolTipInv`'s render and touches no `ISCharacterInfoWindow` method and no layout-manager registration: the census records no tooltip-wrap and no character-info-wrap hit for it [#2497/C/snapshot].
`CleanUI`'s own `ISInventoryPane.lua` and `ISInventoryPaneContextMenu.lua` still construct `ISToolTipInv`, so a wrap of `ISToolTipInv`'s render survives `CleanUI` while a wrap of `ISInventoryPane`'s tooltip method would be replaced by `CleanUI`'s copy [#2499/C/C-only].
Under `CleanUI` a multi-item stack's tooltip is built from one representative display item plus `tooltip:setWeightOfStack(w)`, so a tooltip wrap sees a display item and not the group, and `CleanUI` skips the rebuild while the item and the stack weight are unchanged [#2500/C/C-only].
A per-item line therefore describes the representative item, and a line meant to sum a stack has to read the stack weight the tooltip carries rather than walk a group it never sees.
That `CleanUI` also ships no file named after any vanilla class this page relies on is unverified ([Open](#open)).

<a id="character-info"></a>
### The character-info window

The character-info window is the vanilla home for per-character panels, and a mod tab there sits beside the skills and health tabs.
A mod adds a character-info tab by wrapping `ISCharacterInfoWindow`'s `createChildren` to call `self.panel:addView(getText(...), view)`, and the wrap must be installed at file scope, because the window is built inside `createPlayerData` on `Events.OnCreatePlayer` [#2501/C/C-only].
`AutoCook` ships the worked example at a mod-unique path, wrapping the tab-tear-off and save methods beside it ([autocook.md](../facts/other-mods/autocook.md#architecture)).
A mod tab must not write its own name into `layout.current`, because vanilla's `RestoreLayout` passes that key through `xpSystemText[...]` to `activateView` whenever it is not a floating vanilla tab, and `xpSystemText` carries no entry for a name vanilla does not own [#2502/C/C-only].
`ISTabPanel` keys `getView` and `activateView` on a tab's displayed name, and the character-info window's `toggleView` looks the view up by that name, so a mod tab's name is a translated string and the same string is the toggle argument [#2503/C/C-only].
A live client took a mod tab through the wrapped `createChildren` at first sight with no error, and its render count read 0 at every check [#3221/M/n=2].
At a quit the character-info line the game wrote to `layout.ini` carried the mod tab's name after vanilla's five, with `current` on vanilla's tab [#3217/M/n=2].
A key that opens the mod tab therefore passes the translated name, exactly as vanilla's own panel keys pass theirs.
The tab rule at the top of this page follows from the build timing and the restore lookup above.
The wrap is not idempotent on its own: a second run of the file stacks a second wrapper and a second tab, so the install sits behind a sentinel like any other wrap.
A tab costs three method wraps where a registry would cost one call, which is the price of the missing registry under [Walls and bounds](#walls).
The tab's panel is an ordinary derive, usually of `ISPanelJoypad` so a controller can reach it, built at the tab's own size.

Two readings of the info tab bear on a mod that writes traits or perk levels.
`ISCharacterScreen` rebuilds its trait icon row on render whenever the displayed list, read from `getKnownTraits()`, differs from the icons it holds, so a trait change written server-side appears on that screen without a UI refresh once the client's trait list carries it [#2504/C/C-only].
Whether and when the client's list carries it is a packet question, answered on [mp-model.md](mp-model.md#sync-globals).
`ISCharacterScreen` and `ISPlayerStatsUI` each assign the Strength and Fitness perk levels to a field that neither file reads again [#2505/C/C-only].
A remapped perk level therefore has no hidden reader on those two screens.

<a id="cadence"></a>
### Events and cadence

A panel's own callbacks are the per-frame surface, and the global UI events are the alternative for drawing that belongs to no panel.
`OnPostUIDraw` fires once per `UIManager.render`, after the element pass and only when the Lua thread is the UI default thread [#2506/C/C-only].
`OnRenderTick` is the per-rendered-frame hook: `GameWindow.onRender`'s whole body is its trigger [#2507/C/C-only].
Both run every rendered frame, so whatever a handler does there it does at the frame rate, and a value it reads is read at the frame rate unless the handler caches it.
A widget's own `render()` was counted at about one call per client tick in the one live reading, an inference and not a per-frame trace: a framework moodle and a plain derived widget each counted 240 calls across a read window of about 4 s while the client's tick counter read 60.03 a second in a later window ([#3195/M/n=1], [#3198/M/n=1]).
The simulation-tier rule for slow work — the minute hooks, a cheap early-out on the player update, and no steady `OnTick` — is [lessons.md](lessons.md#rules)'s [#1071/C/snapshot].
The value a panel draws changes at the push, not at the frame, and the cadence rule for reading it is [ui-and-moodles.md](../areas/ui-and-moodles.md#read-cadence)'s; the resident viewer's own render loop throttles its reads to a frame count ([simplestatus.md](../facts/other-mods/simplestatus.md#architecture)).

The resident interface mod keeps its tick handlers short-lived.
`CleanUI`'s live `42.19` tree registers 5 `OnGameBoot`, 5 `OnGameStart`, 5 `OnTick`, 1 `OnKeyPressed`, 1 `OnCreatePlayer` and 1 `OnContainerUpdate` handler, and four of its five `OnTick` handlers remove themselves once their bootstrap or deferred action queue is done, while the fifth, the deferred options-toggle handler, stays registered and returns at once while nothing is pending [#2508/C/snapshot].
A one-shot `OnTick` handler that removes itself is the cheapest way to defer work by one tick, and a standing one is affordable only behind an early-out of that kind.
A mod's panel shares the frame with that resident load, so a nutrition panel keeps its own per-frame work to drawing values it already holds.

<a id="java-surface"></a>
### The Java UI surface

Three Java UI classes matter to a mod: the base element every Lua widget wraps, the tooltip object, and the moodle stack.
`zombie.ui.MoodlesUI` is a public final `UIElement` subclass in the exposer's class set, its `getInstance()` is public static, `clientW` and `clientH` are public fields and `UIElement`'s `getX`, `getY`, `getWidth` and `getHeight` are public, so the vanilla moodle stack's box is readable as an anchor for a mod's own icon column though the class offers no mutator [#2509/C/C-only].
The exposer test itself is [lua-platform.md](lua-platform.md#java-members)'s [#0963/C/C-only].
A live client confirms the exposure: the class resolved as a table, its instance getter as a function returning a userdata [#3196/M/n=1], and the box read 1238, 424, 32 and 720 for x, y, width and height at player creation and again later [#3197/M/n=1].
`ObjectTooltip` is a public final `UIElement` subclass whose `padLeft`, `padTop`, `padRight` and `padBottom` are public int fields and whose public drawing surface is `DrawText`, `DrawTextCentre`, `DrawTextRight`, `DrawValueRight`, `DrawValueRightNoPlus`, `DrawTextureScaled`, `DrawTextureScaledAspect`, `DrawProgressBar`, `adjustWidth`, `beginLayout`, `endLayout`, `getLineSpacing` and `getFont` [#2511/C/C-only].
A public instance field is not a door the exposer opens: the exposer publishes an exposed class's public instance methods and copies its public static fields in as values when it exposes the class, with no route to an instance field [#2735/C/C-only].
The one Lua route to a field is reflective and debug-only: the three class-field globals throw unless the game was launched with the `-debug` argument, the field getter hands back a field of the object's own class already set accessible, and the reflection field class is exposed to Lua under debug alone [#2745/C/C-only].
A harness client, launched with that argument, can therefore reach a field that a player's release client cannot, so a field read or write a debug probe makes is no evidence for a shipped mod.
So the tidy tooltip route — raising `padBottom` before the measure pass so the background covers the mod's band — rests on a field write that no route read here gives a release client, and a mod plans on its own framed band instead.
`UIElement.render`'s two early-return tests both read the parent — its `maxDrawHeight` and its `renderClippedChildren` flag — so a top-level element on the UI manager's list, which has no parent, is never culled by them [#2512/C/C-only].
A band drawn below a top-level tooltip panel is therefore not culled by the element's own render, though nothing here proves it lands on screen.
Reading the moodle stack's box is the one thing the Java surface offers a status-icon column; drawing into the stack is not on offer.
Any other Java UI class a mod wants is reached the same way: test it against the exposer's class set, then read its access flags before treating a public member as a door.

## Walls and bounds
<a id="walls"></a>

- `ISCharacterInfoWindow` has no tab registry: its five tabs are hard-coded in `createChildren`, again in `RestoreLayout`'s floating table and again in `SaveLayout`'s five parent tests [#2513/C/C-only].
- `ISHealthPanel` and `ISCharacterScreen` expose no extension point: `ISHealthPanel`'s only handler-list method, `checkItems(handlers)`, takes a list `doBodyPartContextMenu` builds locally [#2514/C/C-only].
- The engine has no keybind registration and no mod-key option: `getOptionModsKey` and `registerKeyBind` are in no class of the jar, and `Core`'s key surface is `getKey`, `getAltKey`, `isKey`, two `getKeyBinding` overloads, `addKeyBinding` and `reinitKeyMaps` [#2515/C/C-only].
- The routes by which a mod can show a moodle or a status icon are [ui-and-moodles.md](../areas/ui-and-moodles.md#moodle-route)'s.

Not covered: the joypad half of every surface (`ISPanelJoypad`'s navigation, controller focus, the character window's bumper cycling and the controller path through the tooltip); the Xui skin layer and whether a skin changes the tooltip route; the rest of the inventory pane's own tooltip method in vanilla and in `CleanUI`; the options screen's Apply and its `save()` path, the keybinding page beyond `loadKeys` — the duplicate-bind dialog, the key-setting dialog and the old key-file migration; whether a mod can register a character stat; a live font-size change and how a panel re-lays itself out; split screen; and any measurement of frame time or draw cost, which no shipped command takes; the unmeasured behaviours of the shipped surfaces (the band's placement, a saved line's restore, the tab's tear-off, the key press, the scrolled clip) sit under [Open](#open), each with the synthesiser that settles it.

## Open
<a id="open"></a>

- Whether the tooltip band lands on screen below the engine's box, above it when the box's bottom would leave the screen, and clear of an anchored slot, and what its draw leaves of the box's height, is unmeasured: the band's entry function ran under the probe and the hover draw count read 0 on both boots — settled by a hover synthesiser reading the band's pixels or the element's draw calls [#3244/M/n=2/open].
- Whether a saved `visible=true` panel line restores the panel open is unmeasured: the fixture's layout file carried no line for the panel and the quit wrote `visible=false` — settled by a second boot on a user directory carrying the line [#3245/M/n=1/open].
- Whether the tab draws, survives a tear-off through its wrap and fires the layout save's `current`-clearing branch is unmeasured: the tab's render and tear-off counts read 0 and the tab was never the active one at the quit — settled by a click synthesiser that activates the tab and tears it off before the quit [#3246/M/n=1/open].
- Whether the panel's key press toggles it is unmeasured: `keyPresses` read 0 on every read and the toggle was a `lua.call` — settled by a key synthesiser [#3247/M/n=1/open].
- Whether a scrolled panel clips its rows at the window's edge is unmeasured: no wheel was synthesised — settled by a wheel synthesiser reading the rows' draw calls after a scroll [#3248/M/n=1/open].
- That no tree of `CleanUI` ships a file named `ISToolTipInv.lua`, `ISUIElement.lua`, `ISPanel.lua`, `ISPanelJoypad.lua`, `ISCollapsableWindow.lua`, `ISTabPanel.lua`, `ISLayoutManager.lua`, `ISCharacterInfoWindow.lua` or `ISHealthPanel.lua` is unverified: the scan of the workshop tree is not a committed dataset; re-measure by extending the inventory census to record each mod's file list and reading `CleanUI`'s row [#2498/C/snapshot/unverified].
- That no vanilla Lua file accesses a `padBottom` field on any object, the literal `.padBottom` being absent from the install's Lua, is unverified: the scan is not a committed dataset; re-measure by a committed grep of `media/lua`, and settle the write itself with a probe that sets the field from Lua and reads the tooltip height back [#2510/C/snapshot/unverified].
- That no vanilla Lua other than `MainOptions:addModOptionsPanel` calls `PZAPI.ModOptions:load()` is unverified: the scan of the install's Lua is not a committed dataset; re-measure by a committed grep of `media/lua` for `ModOptions:load` [#2528/C/snapshot/unverified].

## See also

- [ui-and-moodles.md](../areas/ui-and-moodles.md#read-cadence) — what a panel may believe, how often it reads, and the moodle routes.
- [lua-platform.md](lua-platform.md#dev-loop) — the wrapper sentinel and reload rules every wrap on this page follows.
- [lua-platform.md](lua-platform.md#java-members) — the exposure test for any Java UI class a mod reads.
- [mp-model.md](mp-model.md#wipe-and-replace) — what a player-modData position write costs a neighbour.
- [mod-anatomy.md](mod-anatomy.md#translations) — the translation merge behind tab names and option labels.
- [simplestatus.md](../facts/other-mods/simplestatus.md#architecture) — the resident viewer's panel, its throttled render loop and its registration API.
- [autocook.md](../facts/other-mods/autocook.md#architecture) — the worked character-info tab.
- [moodleframework.md](../facts/other-mods/moodleframework.md) — the framework a status-icon column would sit beside.
- [lessons.md](lessons.md#rules) — the event-tier rule the cadence section leans on.
