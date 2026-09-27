# MoodleFramework — desk read

Read 2026-09-27 against the installed copy of workshop item `3396446795` (`D:\SteamLibrary\steamapps\workshop\content\108600\3396446795\mods\MoodleFramework`, read-only) and against the 42.20.4 install's own `media/lua` and `projectzomboid.jar` (`b0bbce05d5`).
Nothing was booted. Every statement below is a reading of code on disk, or of the jar through `C:\Users\Angus\pz-b42\pz.sh`, and is graded C.
Line cites name the version folder the file lives in; the copy the 42.20.4 build executes is settled in [the layout table](#d1-layout).

## Summary for the design

MoodleFramework is a pure client-side Lua widget library, not a wrapper over the engine's moodle system: it never calls `MoodleType.register`, so the pinned-level wall (#1140) does not apply to it at all.
It derives one `ISUIElement` subclass, `MF.ISMoodle`, and pushes one instance per (moodle name × player number) into `UIManager` through `addToUIManager`, drawing its own texture, border, chevrons and hover tooltip beside the Java-drawn vanilla stack.
Its whole registration surface is two globals — `MF.createMoodle(name)` and `MF.getMoodle(name, playerNum)` — plus about sixteen methods on the returned instance, and the value it draws is a single float the consumer sets with `:setValue(v)`.
Level is derived, never set: eight thresholds (four bad, four good, default `0.1/0.2/0.3/0.4` and `0.6/0.7/0.8/0.9`) map the value to a level 0–4 and a polarity of good, bad or neutral, and the moodle is added to `UIManager` only while that polarity is non-neutral.
That last detail matters for X29: a freshly created moodle holds `Value = 0.5`, which is neutral under the default thresholds, so a framework moodle renders nothing at all until the consuming mod calls `:setValue` past a threshold — a run that registers a moodle and never sets its value would correctly see nothing, and that is the framework working, not failing.
On this build the 42.20 folder's copy of `MF_ISMoodle.lua` no longer touches player modData: the earlier copies wrote `character:getModData().Moodles`, and the executing copy keeps the same table in a plain client-side Lua map `MF.MoodleData` keyed by `tostring(char)`, with the comment "mod data are now server side".
So the framework writes no modData, calls no `transmitModData`, and contains no `sendClientCommand` or `sendServerCommand` anywhere in any of its four folders — it cannot wipe another mod's player-modData keys, and the library's E9 wipe-and-replace hazard does not reach it.
The price of that is that a framework moodle's value is per-client, in-memory, transient and invisible to the server: nothing persists it across a reload and nothing carries it over the wire.
Consequently a server-authoritative nutrition mod must mirror the value to the client over its own bus (`sendServerCommand` → `OnServerCommand`) and call `MF.getMoodle(name, playerNum):setValue(v)` in its own client Lua; the framework supplies no route and asks for none.
The framework is 100 per cent client: all four of its executable Lua files sit under `media/lua/client/`, so on a dedicated server `MF` is nil and every framework call must live in the consumer's own `media/lua/client/` file.
The 42.20 copy still depends on `MF_Config.lua` at render time (`MF.hasBackground`, `MF.hasBorder`, `MF.hasBGColor`), and that file has no 42.20 counterpart, so the copy that executes is `common/media/lua/client/MF_Config.lua` — byte-identical to the 42.0 copy — which confirms #1319 by reading the call sites rather than only the layout.
The version folders are not equivalent and the merge rule is load-bearing rather than cosmetic: the 42.0 and `common/` copies of `MF_ISMoodle.lua` call `Moodles.getNumMoodles()`, which is absent jar-wide on 42.20.4, and `MoodleType.FromIndex` / `MoodleType.FoodEaten`, which are absent from `MoodleType` on this build — so if `common/` ever won that collision the framework would raise on the first render.
Against the page's read-cadence rule the framework is expensive by construction: `render()` runs per frame per visible moodle and calls `getXYPosition()`, which walks every vanilla `MoodleType` in `Registries.MOODLE_TYPE`, reads `getMoodleLevel` for each, walks another mod's `MoodleManager` modData table, and builds and `table.sort`s the modded-moodle name list — all per frame, and none of it cached.
There are no `pcall`s anywhere in the framework, so the consumer's protected call at the boundary is the only thing standing between a framework change and the consumer's own handler, which is exactly what the library's boundary rule asks for.
Detection is easy and cheap: `MF` and `MF.createMoodle` are defined at Lua file-load time, therefore before `OnGameBoot` fires, so a consumer can test `type(MF) == "table" and type(MF.createMoodle) == "function"` at its own file scope and fall back; `require "MF_ISMoodle"` is the fragile form, because it raises when the framework is absent.
For the fallback itself, the alternative is cheaper than the page assumes: no vanilla Lua draws the moodle stack at all (it is `zombie.ui.MoodlesUI` in Java, whose member list offers no add or register), so the framework's own route — `ISUIElement:derive` plus `addToUIManager` — is the only Lua moodle route there is, and a mod can take it directly in roughly the 150 lines of positioning and texture maths the framework spends on it.
The one thing the framework buys that a private widget cannot is stacking: its `getXYPosition` offsets a moodle below the vanilla stack, below Aiteron's moodles and below other framework moodles, so two independent stacks would overlap and a "optional framework, own fallback" design should expect the fallback to draw in a different screen slot rather than in the same one.
The consumer also owns every asset: the framework ships no moodle texture and no `Moodles_*` translation key, and expects `media/ui/<size>/<Name>.png` (B42) with `media/ui/<Name>.png` as fallback, plus `Moodles_<Name>_<Good|Bad>_lvl<N>` and `..._desc_lvl<N>` keys — and its own `HowTo.txt` states those keys in the B41 `Moodles_EN { }` text-table layout while vanilla B42 ships `Moodles.json` with bare keys, which is the shape to follow.

## A — the public API

Every row cites `42.20/media/lua/client/MF_ISMoodle.lua` unless the file is named, and that is the copy the 42.20.4 build executes.

### A1 — namespace functions and fields (what a consuming mod calls)

| item | file:line | what it does |
|---|---|---|
| `MF.createMoodle(moodleName)` | `42.20/…/MF_ISMoodle.lua:25` | the registration call. Marks `MF.createdMoodleTypes[moodleName] = true` and, only on the first call for that name, adds an `OnCreatePlayer` handler that constructs `MF.ISMoodle:new(moodleName, getSpecificPlayer(playerNum))`. Idempotent per name (a 42.13-and-later addition); takes no other argument, so polarity, thresholds, textures and text are all set afterwards on the instance. Registers nothing with the engine. |
| `MF.getMoodle(moodleName, playerNum)` | `42.20/…/MF_ISMoodle.lua:35` | the access call. Returns the instance out of `MF.MoodlesStorage[playerNum][moodleName]`, or `nil` when the player slot or the name is missing — which is the state before `OnCreatePlayer` has fired. With `playerNum` omitted it uses `getPlayer():getPlayerNum()`, falling back to `0` when there is no player. |
| `MF.MoodlesStorage` | `42.20/…/MF_ISMoodle.lua:8` | `playerNum -> moodleName -> instance`. Written in `:new` at `:541,:552`. The split-screen-safe registry `MF.getMoodle` reads. |
| `MF.MoodleData` | `42.20/…/MF_ISMoodle.lua:61` | the value store: a plain client-side Lua table keyed by `tostring(char)`, holding `{Moodles = {[name] = {Level, GoodBadNeutral, Value}}}`. Replaces the player-modData store the older copies used. |
| `MF.createdMoodleTypes` | `42.20/…/MF_ISMoodle.lua:21` | the dedupe set behind `createMoodle`; also the cheapest read for "has this name already been registered". |
| `MF.getSize()` | `42.20/…/MF_ISMoodle.lua:408` | returns `floor(MF.defaultWidth * MF.scale)`, recomputing `MF.scale` from `getCore():getOptionMoodleSize()` (and `getOptionFontSizeReal()` above 6.5). Called every frame from `getXYPosition`. |
| `MF.adjustScale()` | `42.20/…/MF_ISMoodle.lua:641` | repositions and resizes every stored moodle of every player from the current `MF.scale`. **Registered to no event anywhere in the mod** — an exported function a consumer would have to call itself if it changes `MF.scale` or `MF.defaultWidth`. |
| `MF.getMoodleARGB(gbn, level)` | `42.20/…/MF_ISMoodle.lua:654` | the background colour: a `level/4` lerp from `Color.gray` toward `getCore():getGoodHighlitedColor()` or `getBadHighlitedColor()`. Returns gray for neutral. |
| `MF.verbose` | `42.20/…/MF_ISMoodle.lua:9` | `false`. Set `true` and the framework prints level changes, missing-table recreations and disabled-call warnings, and `createChildren` adds a green debug panel (`:629-638`). A consumer may flip it; it is the only debug switch. |
| `MF.TooLargeValue` | `42.20/…/MF_ISMoodle.lua:10` | `100000`, the sentinel `setThresholds` substitutes for a `nil` threshold. |
| `MF.scale`, `MF.dynamicWidth`, `MF.defaultWidth`, `MF.xOffset`, `MF.yOffset` | `42.20/…/MF_ISMoodle.lua:11-15` | `nil`, `true`, `32`, `10`, `120` — geometry knobs. `xOffset`/`yOffset` are the whole stack's inset from the right edge and the top of the player's viewport. |
| `MF.yOff`, `MF.yMaxError`, `MF.yMinError`, `MF.yCorrectionPerFrame` | `42.20/…/MF_ISMoodle.lua:16-19` | the slide-in animation: a new moodle starts at absolute `y = 10000` and converges 15 per cent of the remaining error per frame. |
| `MF.hasBackground()`, `MF.hasBorder()`, `MF.hasBGColor()` | `common/…/MF_Config.lua:17,13,21` | read the three Mod Options tick boxes. **Called from `render()`**, so the config file is a hard runtime dependency of the 42.20 moodle file. |
| `MF.overrideGray()` | `common/…/MF_Config.lua:6` | mutates the engine's shared `Color.gray` in place from the colour-picker option. Registered to `OnMainMenuEnter` at `common/…/MF_Config.lua:45` and re-run on options apply (`:34-39`). A global side effect on a vanilla colour object, which is what the `Compute Colors` option exists to let a user switch off. |
| `MF.loadConfig()` | `common/…/MF_Config.lua:25` | builds the `PZAPI.ModOptions` page under id `MoodleFramework` (`MF.key`, `:4`) with one colour picker and three tick boxes, and wraps `options.apply`. Called at file scope (`:43`). |
| `MF.ISMoodle` | `42.20/…/MF_ISMoodle.lua:56` | `ISUIElement:derive("ISMoodles")` — the class. A consumer normally never touches it directly, but it is the extension point for overriding a method on all moodles. |

### A2 — instance methods (on what `MF.getMoodle` returns)

| item | file:line | what it does |
|---|---|---|
| `:setValue(value)` | `:83` | the only write. Stores `value` into the instance's `Value`, then recomputes and stores `Level` and `GoodBadNeutral` from it; starts the wiggle animation when either changed; adds the element to `UIManager` the first time polarity becomes non-neutral and removes it when polarity returns to neutral (`:102-109`). **No clamping and no range check** — the caller owns the `0..1` convention the `HowTo` states. No-op while suspended. |
| `:getValue()` | `:114` | the stored float; returns `0.5` while suspended. |
| `:getLevel()` | `:127` | `0..4`, derived. Tests `value >= threasholdGood<n> or value <= threasholdBad<n>` from 4 down to 1, so a good level and a bad level of the same depth share one number and the polarity getter is what separates them. Never settable. |
| `:getGoodBadNeutral()` | `:120` | `1` good, `2` bad, `0` neutral, derived from `threasholdGood1` / `threasholdBad1` only. This is the polarity a consumer reads; there is no setter and no "good moodle" flag — polarity is a consequence of where the value sits. |
| `:setThresholds(bad4, bad3, bad2, bad1, good1, good2, good3, good4)` | `:155` | sets all eight. A `nil` collapses outward: a nil `good4` becomes `+MF.TooLargeValue` and each lower good threshold defaults to the one above it, a nil `bad4` becomes `-MF.TooLargeValue` and each higher bad threshold defaults to the one below it. So passing only the four bad values makes a bad-only moodle that can never read good, and vice versa. Defaults are set in `:new` at `:517` to `(0.1,0.2,0.3,0.4, 0.6,0.7,0.8,0.9)`. |
| `:setTitle(gbn, level, text)` | `:176` | overrides the tooltip's first line for one polarity (`1` good / `2` bad) and one level `1..4`. Silently ignores a zero or nil argument. |
| `:setDescription(gbn, level, text)` | `:185` | same for the tooltip's second line. |
| `:setDescritpion(gbn, level, text)` | `:182` | the misspelled backward-compatibility alias that forwards to `:setDescription`. |
| `:getTitle(gbn, level)` | `:210` | the override if set, else lazily `getText("Moodles_"..name.."_"..("Good"|"Bad").."_lvl"..level)`, memoised into the slot on first use. |
| `:getDescription(gbn, level)` | `:229` | the same for `"Moodles_"..name.."_"..("Good"|"Bad").."_desc_lvl"..level`. |
| `:setPicture(gbn, level, texture)` | `:197` | overrides the moodle icon per polarity and level. Takes a `Texture`, not a path — the consumer calls `getTexture` itself. |
| `:setBackground(gbn, level, texture)` | `:191` | overrides the background plate per polarity and level; `nil` means the vanilla B42 plate `self.Background`. |
| `:setChevronCount(n)` | `:147` | draws `n` stacked chevrons at the icon's right edge (`:347-357`). The trend indicator. |
| `:setChevronIsUp(isUp)` | `:151` | chooses the up or down chevron textures. |
| `:doWiggle()` | `:203` | starts the attention-getting oscillation, if polarity is non-neutral. `setValue` already does this on a level or polarity change. |
| `:suspend()` / `:activate()` | `:558` / `:561` | set and clear `self.disable`. Suspend makes `setValue` a no-op, `getValue` answer `0.5` and `render` draw nothing; the framework calls `:suspend()` itself from its per-instance `OnPlayerDeath` handler (`:549`). |
| `:getMoodleData()` | `:62` | the defensive accessor: creates the character's table, the `Moodles` table and this moodle's entry if any is missing, and returns `(thisEntry, allMoodles)`. Semi-internal, but it is what makes a wipe by another mod non-fatal. |
| `:new(moodleName, character)` | `:500` | the constructor `createMoodle`'s handler calls. Builds the `ISUIElement` at the computed position, sets the default thresholds, copies any previous instance's overrides through `:handleCacheOverride`, unhooks the previous instance's death handler and UI registration, registers its own `OnPlayerDeath` handler, and stores itself in `MF.MoodlesStorage`. |
| `:render()`, `:getXYPosition()`, `:updateTextures(size)`, `:getPicture()`, `:mouseOverMoodle()`, `:isMouseOverMoodle()`, `:createChildren()`, `:handleCacheOverride()`, `:updateOscilatorXOffset()` | `:267`, `:441`, `:428`, `:361`, `:384`, `:367`, `:626`, `:565`, `:249` | internals. Listed because a consumer that overrides one of them is the only way to change layout, and because `render` and `getXYPosition` are the per-frame cost. |

### A3 — the assets and text the consumer must supply

| item | file:line | what it does |
|---|---|---|
| `media/ui/<size>/<Name>.png` | `42.20/…/MF_ISMoodle.lua:432` | the B42 default icon, looked up per current size. `<size>` is `MF.getSize()`: `32`, `48`, `64`, `80`, `96` or `128`. Vanilla ships the directories (`media/ui/32` … `media/ui/128`) and they are empty, so this is the intended mod slot. |
| `media/ui/<Name>.png` | `42.20/…/MF_ISMoodle.lua:436,595` | the B41-style unsized fallback, applied only when the sized lookup returned nothing. The `HowTo.txt` documents this one (30×30 with alpha). |
| `media/ui/<Name>_Good_<1..4>.png`, `media/ui/<Name>_Bad_<1..4>.png` | `42.20/…/MF_ISMoodle.lua:590-591` | optional per-level icons, loaded eagerly in `handleCacheOverride`; equivalent to calling `:setPicture` for each. |
| `media/ui/Moodles/<size>/_Moodles_BGsolid.png`, `_Moodles_BGoutline.png` | `42.20/…/MF_ISMoodle.lua:430-431` | the plate and border. **Vanilla's own files** — confirmed present at `media/ui/Moodles/32/…` in the install — so the consumer ships nothing for these. |
| `media/ui/Moodle_chevron_{up,down}{,_border}.png` | `42.20/…/MF_ISMoodle.lua:573-576` | the chevrons, again vanilla's own, present in `media/ui/`. |
| `Moodles_<Name>_Good_lvl<1..4>`, `Moodles_<Name>_Bad_lvl<1..4>`, and the matching `_desc_lvl<N>` | `42.20/…/MF_ISMoodle.lua:223,242` | the tooltip text keys, up to 16 per moodle. The framework ships none of them for any name. `HowTo.txt:9-27` gives them in a B41 `Moodles_EN { … }` text table; vanilla B42 ships `media/lua/shared/Translate/EN/Moodles.json` with bare keys (`"Moodles_Endurance_lvl1"`, `"Moodles_Endurance_desc_lvl1"`), which is the layout to copy. |

## B — the mechanism

| item | file:line | what it does |
|---|---|---|
| no engine moodle registration | — | `MoodleType.register` / `registerBase` appear nowhere in any of the four folders; `grep` over `*.lua` for `MoodleType` finds only the two read sites below. The framework therefore never meets the pinned-level wall (#1140) or the duplicate-id hazard (#1198) — it is a widget library, not a registry wrapper. |
| it draws its own widget | `42.20/…/MF_ISMoodle.lua:56`, `:103`, `:267` | `MF.ISMoodle = ISUIElement:derive("ISMoodles")`; `setValue` calls `self:addToUIManager()` the first time polarity is non-neutral; `UIManager` then calls `render()` each frame, which draws the plate, the border, the tooltip, the icon and the chevrons with `drawTextureScaled` / `drawTextureScaledUniform` / `drawRect` / `drawTextRight`. |
| it reads the vanilla stack to stack under it | `42.20/…/MF_ISMoodle.lua:458-467` | `Registries.MOODLE_TYPE:values()` then `self.char:getMoodles():getMoodleLevel(moodleType)` per type, adding one row's height for each vanilla moodle that is showing, with `MoodleType.FOOD_EATEN` counted only from level 3. A read of the engine's registry — nothing is written to it. |
| it reads another framework's modData to stack under that too | `42.20/…/MF_ISMoodle.lua:469-485` | `self.char:getModData().MoodleManager` (Aiteron's moodle manager), iterating `.moodles` and calling `moodleObj:getLevel()` where it exists. Read-only, and the one `getModData` call left in the executing copy. |
| it stacks its own moodles alphabetically | `42.20/…/MF_ISMoodle.lua:487-494` | collects the names out of its own store, `table.sort`s them, and offsets by each preceding non-zero-level moodle. The sort is new in 42.20 (42.13 and earlier used `pairs` order, which is unstable). |
| vanilla classes it touches | `42.20/…/MF_ISMoodle.lua:251,410-418,458,460,469,654-658`; `common/…/MF_Config.lua:9,26-31` | `PerformanceSettings.getLockFPS`, `getCore()` options and highlight colours, `Registries.MOODLE_TYPE`, `Moodles.getMoodleLevel`, `IsoGameCharacter.getModData`, `getNutrition():getProteins()` (a verbose-only debug print, `:98`), `Color.gray` (mutated in place), `getTexture`, `getText`, `getTextManager()`, `getMouseX/Y`, `getPlayerScreen{Left,Top,Width}`, `getSpecificPlayer`, `getPlayer`, `PZAPI.ModOptions`, `ISUIElement`, `ISPanel`. It wraps exactly one thing — `options.apply` at `common/…/MF_Config.lua:33-39` — and patches no vanilla Lua file. |
| events it registers | `42.20/…/MF_ISMoodle.lua:29`, `:545`, `:550`; `common/…/MF_Config.lua:45` | three, all client: `OnCreatePlayer` (one handler per registered moodle name, added inside `createMoodle`), `OnPlayerDeath` (one per instance, which removes the widget and suspends it; the previous instance's handler is removed on re-creation), and `OnMainMenuEnter` (`MF.overrideGray`). No `OnTick`, no `OnPlayerUpdate`, no `OnGameBoot`, no `OnClientCommand`, no `OnServerCommand`. |
| side | whole tree | client-only. The four executable Lua files are `{42.0,42.13,42.20,common}/media/lua/client/…`; the only other `media/lua` content is `{42.0,common}/media/lua/shared/Translate/EN/{UI.json,UI_EN.txt}`, which is translator data and not executed. `grep` finds no `isServer`, no `isClient`, no `lua/server/` and no `lua/shared/` code file. On a dedicated server `MF` is therefore nil. |
| the value across the wire | `42.20/…/MF_ISMoodle.lua:61-79` | nothing crosses. The store is `MF.MoodleData`, a client-process Lua table keyed by `tostring(self.char)`, created on demand, written only by `setValue`. It is not modData, so it is neither saved nor transmitted; it is not keyed by a stable id, so it does not survive the character object being rebuilt; and the framework has no send or receive call of any kind. The value is per client, set only from client Lua, and the framework carries nothing from the server. |
| per-frame cost | `42.20/…/MF_ISMoodle.lua:267-283`, `:441-497` | `render` calls `getXYPosition` every frame for every visible moodle, and that walks every vanilla `MoodleType`, reads a `getMoodleLevel` per type, walks the Aiteron modData table, and builds and sorts the modded-name list — plus `MF.getSize()` reading two `getCore()` options. Nothing is memoised between frames. Against `ui-and-moodles.md`'s read-cadence rule this is the frame cadence, not the push cadence, and the consumer cannot cache it away because it is the framework's own code. |
| render gate | `42.20/…/MF_ISMoodle.lua:102-109`, `:268-269`, `:517` | the element is in `UIManager` only while polarity is non-neutral, and `render` early-returns when polarity is neutral or the moodle is suspended. With the default value `0.5` and the default thresholds `0.4 / 0.6`, a registered-but-never-set moodle is neutral and therefore invisible. |

## C — multiplayer

| item | file:line | what it does |
|---|---|---|
| `sendClientCommand` | absent | zero hits over all four folders. |
| `sendServerCommand` | absent | zero hits over all four folders. |
| `transmitModData` | absent | zero hits over all four folders. |
| player modData writes, executing copy | none | the 42.20 copy writes no modData. Its one `getModData` call is the read at `42.20/…/MF_ISMoodle.lua:469`. |
| player modData writes, older copies | `42.0/…/MF_ISMoodle.lua:491-501` and `common/…/MF_ISMoodle.lua:491-501` (identical files), `42.13/…/MF_ISMoodle.lua:501-511` | the pre-42.20 constructor did write the player's modData, and worse: `character:getModData().Moodles = {}` on the first moodle of the session, gated on a one-shot `MF.ModDataClean` flag. Those copies do not execute on 42.20.4 (see [D1](#d1-layout)), and even they never transmitted — so no copy of this mod can trigger the wipe-and-replace failure, which needs a `transmitModData`. |
| the E9 exposure | — | not present. The framework neither writes nor transmits player modData on this build, so it cannot wipe another mod's keys, and a nutrition mod's own player-modData keys are safe from it. The reverse is also now safe: because the framework's store left modData, another mod's `transmitModData` can no longer wipe the framework's moodle levels — which is precisely what the stale comment at `42.20/…/MF_ISMoodle.lua:59-60` and the recreate-on-missing guard at `:68-77` were written for. |
| what a server-authoritative nutrition mod must do | derived | the framework offers no server side and no transport, so the consuming mod owns the whole route: (1) the server keeps the nutrient and computes, or sends the inputs for, a normalised `0..1` value; (2) the server pushes it to that client over the mod's own bus — `sendServerCommand(player, module, command, {name=…, value=…})` — at whatever cadence the design picks; (3) the client's `OnServerCommand` handler calls `MF.getMoodle(name, playerNum):setValue(value)` inside a `pcall`. The framework then derives level, polarity, colour and text on the client with no further help. The player-stats packet carries none of this (#0129), so there is no shortcut. |
| where the value must be computed | `42.20/…/MF_ISMoodle.lua:120-143` | level and polarity are computed on the client from the client's value, so if the design wants the level itself to be server-authoritative it must send the value (or a value the thresholds map to the intended level) rather than the level — there is no level setter. Sending a value and setting thresholds identically on the client is the only route. |
| what a second client sees | derived | nothing. The store is per client process and per `tostring(char)`, so a client only ever draws its own character's moodles; there is no path by which one player's framework moodle reaches another player's screen. |
| split screen | `42.20/…/MF_ISMoodle.lua:510`, `:541`, `:448-449` | handled: instances are keyed by `playerNum`, and geometry uses `getPlayerScreen{Left,Top,Width}(self.playerNum)`. A consumer that calls `MF.getMoodle(name)` with no `playerNum` gets `getPlayer()`'s slot, which is wrong for the second local player — pass `playerNum` explicitly. |

## D — robustness

<a id="d1-layout"></a>
### D1 — the version-folder layout and what executes

Resolution rule: `getModVersionDirName` keeps one version folder — the highest-scoring name at or below the running build — and `ZomboidFileSystem.loadMod` then runs pass A over `common/` and pass B over that one version folder, each ending in an unconditional `activeFileMap.put`, so the version folder wins a same-relative-path collision and `common/` supplies everything it does not ship (#0825, #1310). On 42.20.4 the resolved folder is `42.20`; `42.0` and `42.13` are not loaded at all.

| relative path | 42.0 | 42.13 | 42.20 | common | executes on 42.20.4 |
|---|---|---|---|---|---|
| `media/lua/client/MF_ISMoodle.lua` | yes (28 847 B, `559f…`-pair with common) | yes (29 255 B) | yes (28 611 B) | yes (28 847 B, byte-identical to 42.0) | **`42.20`** — pass B overwrites `common`'s |
| `media/lua/client/MF_Config.lua` | yes (1 848 B) | **no** | **no** | yes (1 848 B, byte-identical to 42.0) | **`common`** — no version-folder counterpart, so pass A's entry survives |
| `media/lua/shared/Translate/EN/UI.json` | yes | no | no | yes | `common` (and the `Translator` merges rather than resolving through the file map, #1318) |
| `media/lua/shared/Translate/EN/UI_EN.txt` | yes | no | no | yes | `common`, same caveat |
| `mod.info` | yes (232 B, no `author`/`versionMin`/`modversion`) | no | no | yes (323 B) | `common/mod.info` for the engine, `42.0/mod.info` for `tools/mod_lint.py` — the one corpus mod where the two differ, both declaring `id=MoodleFramework` (#0824) |
| `MoodleFramework.png`, `MoodleFrameworkIcon.png` | yes | no | no | yes | `common` |
| `HowTo.txt` (1 153 B), `HowTo.json` (**0 bytes**) | — | — | — | tree root only | neither is under `media/`, so neither loads; `HowTo.json` is an empty file shipped by accident |

Two consequences the design should hold on to. First, the 42.20 copy **still needs `MF_Config.lua`**: `render()` calls `MF.hasBackground()` at `42.20/…/MF_ISMoodle.lua:292`, `MF.hasBGColor()` at `:311` and `MF.hasBorder()` at `:321`, and all three are defined only in `MF_Config.lua` (`common/…/MF_Config.lua:13,17,21`). Without it the first visible frame raises on a nil call. So #1319's conclusion holds and now rests on the call sites rather than on the layout alone. Second, the executing `MF_Config.lua` is `common`'s copy, which is byte-identical to `42.0`'s (`md5 559f9a62eb288ef78e452edfc329e631` both), so the distinction is bookkeeping rather than behaviour.

Load order inside the mod is also fine: within each block `LuaManager.LoadDirBase` sorts case-insensitively (#0850), so `MF_Config.lua` precedes `MF_ISMoodle.lua`, and `MF_Config.lua`'s file-scope `MF.loadConfig()` (`:43`) runs after vanilla's own `media/lua/client/PZAPI/ModOptions.lua`, since vanilla's files are listed first.

### D2 — what the 42.20 copy changed, and why the merge rule is load-bearing

`42.13 -> 42.20` is one change of substance: the store moved out of player modData into `MF.MoodleData`, and the modded-moodle stacking walk became a sorted list. `42.0/common -> 42.13` is the bigger one: the B41 moodle-enumeration API was replaced.

| removed member called by an older copy | where | status on 42.20.4 | consequence if that copy won |
|---|---|---|---|
| `Moodles.getNumMoodles()` | `42.0/…/MF_ISMoodle.lua:439` and `common/…/MF_ISMoodle.lua:439` | **absent jar-wide** — `pz.sh grep getNumMoodles` returns "no class contains that literal", and `pz.sh methods zombie/characters/Moodles/Moodles` lists 12 methods without it | a nil call on the first `:new`, i.e. at `OnCreatePlayer`, before anything renders |
| `MoodleType.FromIndex(i)` | `42.0/…:448`, `common/…:448` | absent from `MoodleType`: `pz.sh methods zombie/scripting/objects/MoodleType` lists only `<init>`, `get(ResourceLocation)`, `toString`, `getTranslationName`, `register(String)`, `register(boolean,String)`, `registerBase(String)`, `<clinit>` | a nil call inside `getXYPosition` |
| `MoodleType.FoodEaten` | `42.0/…:450`, `common/…:450` | the Java field is `FOOD_EATEN` (`pz.sh refs zombie/scripting/objects/MoodleType '<clinit>'` shows the string `'FoodEaten'` registered into `MoodleType.FOOD_EATEN`), so the B41 spelling reads nil from Kahlua | silent, not a raise: the `~= nil` comparison is always true, so the food-eaten moodle would be counted at every level |
| `ISUIElement:createChildren(self)` | `42.0/…:625`, `common/…:625` | a colon call with an extra argument, fixed to `ISUIElement.createChildren(self)` in 42.20 (`:627`) | benign here, but it is the marker that the old copies are stale |

So the layout is not merely untidy: the file-level merge rule is the only thing keeping a copy that would raise on `OnCreatePlayer` out of the running game. Any future release that stops shipping `42.20/` (or ships a version folder the resolver scores above the build, which it never picks, #0825) puts the broken copy back in play. That is a live dependency risk for the consuming mod, and it is cheap to detect at runtime — see the minimal consumer's guard.

### D3 — removed-API hazards and general robustness

| item | file:line | what it does |
|---|---|---|
| `HasTrait(String)` | absent | zero hits over all four folders. |
| `getTypeString` | absent | zero hits over all four folders. |
| `loadstring` | absent | zero hits over all four folders. |
| `goto`, `%d` on a float, `#` on a Java list | not audited as a rule (these are harness rules, not engine rules) | the file uses `math.floor`, `tostring` and string concatenation for every number it prints, and `#names` only on its own Lua array at `:489` — no `#` on a Java list, and `pairs` over Java containers is never used: the `Registries.MOODLE_TYPE` walk uses `:size()` and `:get(i)` (`:459,:462`). |
| no `pcall` anywhere | `grep pcall` → 0 hits | every framework call into `getText`, `getTexture`, `getCore()`, `Registries`, `PerformanceSettings` and `PZAPI.ModOptions` is unprotected, and so is every consumer call into the framework. The library's boundary rule therefore applies in full: the consumer wraps its own `MF.*` calls. |
| `Color.gray` mutated in place | `common/…/MF_Config.lua:9` | `Color.gray:set(...)` writes the engine's shared gray. Any mod that reads `Color.gray` sees MoodleFramework's user-chosen value (default white, not vanilla gray). Not a hazard for a nutrition mod unless it draws with `Color.gray`. |
| store keyed by `tostring(char)` | `42.20/…/MF_ISMoodle.lua:63-66` | an identity string, so the entry is not stable across a character object being rebuilt (respawn, reconnect) and old entries are never pruned. A consumer must re-`setValue` after `OnCreatePlayer` rather than assume the value survived. |
| a value set before the instance exists is lost | `42.20/…/MF_ISMoodle.lua:35-53` | `MF.getMoodle` returns nil until the framework's own `OnCreatePlayer` handler has run, so a consumer that pushes a value early must either retry or drive its first push from its own `OnCreatePlayer` handler **registered after** `MF.createMoodle` (handlers fire in registration order). |
| the framework absent | derived | `MF` is simply nil. `require "MF_ISMoodle"` raises, because `require` resolves through the merged file map with no per-mod search path (#0853) and the path is not in the map. The detection that does not raise is `type(MF) == "table" and type(MF.createMoodle) == "function"`. |
| when `MF` is defined | `42.20/…/MF_ISMoodle.lua:7`; `common/…/MF_Config.lua:2` | at Lua file-load time, i.e. during `LoadDirBase` and therefore before `OnGameBoot` fires. A consumer's own file scope sees `MF` only if its file sorts after the framework's in the load list — vanilla first, then per mod in `Mods=` order — so the safe places for the guard are the consumer's own `OnGameBoot` or `OnCreatePlayer` handler, or its file scope plus a `mod.info` `require=MoodleFramework` (or `loadModAfter=`) to fix the order. |
| `MF.adjustScale` registered to nothing | `42.20/…/MF_ISMoodle.lua:641` | a resolution or moodle-size change repositions moodles only through the per-frame `getXYPosition`, which does handle it (`:443-446`); `adjustScale` is dead code the consumer may call but need not. |

## E — alternatives without the framework

| item | file:line | what it does |
|---|---|---|
| no vanilla Lua draws the moodle stack | install `media/lua` | `find media/lua -iname '*moodle*'` returns 29 files and every one is a `Translate/*/Moodles.json`. There is no `MoodlesUI.lua`, no `ISMoodleUI`, no moodle widget in `media/lua/client/ISUI/`. The 18 client Lua files that mention "moodle" only read levels (`ISHealthPanel`, `ISFitnessUI`, `ISEatFoodAction`, …). So there is no vanilla Lua moodle UI to subclass, extend or patch. |
| the stack is Java | jar `zombie/ui/MoodlesUI` | `pz.sh methods zombie/ui/MoodlesUI` lists 15 members: `getInstance()`, `setCharacter(IsoGameCharacter)`, `render()`, `update()`, `wiggle(MoodleType)`, `onMouseMove(DD)`, `onMouseMoveOutside(DD)`, `isCurrentlyAnimating()`, `getTextureSizeForOption()`, `getTextureSetIndexForSize(I)`, `isPercentageBackground(MoodleType)`, `getBackgroundPercentage(MoodleType)`, `drawPercentageBackground(MoodleType,F)`, `drawBackgroundPulse(MoodleType,F)`, `<init>`. **No add, insert, register or list mutator** — nothing a mod could hand a new moodle to. `wiggle(MoodleType)` takes a registered type, so it is useless for a mod moodle that was never registered. `MoodlesUI` does appear in `zombie/Lua/LuaManager$Exposer`'s constant pool, so the class is probably Lua-reachable, but reachable buys nothing without a mutator. |
| the Lua route that does exist | install `media/lua/client/ISUI/ISUIElement.lua:1365`, `:1373` | `ISUIElement:addToUIManager()` and `:removeFromUIManager()`. This is the whole mechanism MoodleFramework uses: derive, position, `addToUIManager`, draw in `render()`. Any mod can do the same in its own file with no dependency. |
| what a private fallback costs | derived from the framework's own code | the framework spends about 150 of its 671 lines on things a fallback needs: the size/scale maths (`:408-426`), the texture lookup and its B42/B41 fallback (`:428-439`), the stack offset (`:441-498`), the hover tooltip (`:367-405`) and the wiggle (`:249-265`). A minimal fallback that draws one icon at a fixed offset with a tooltip is far smaller. |
| what a private fallback cannot do | `42.20/…/MF_ISMoodle.lua:487-494` | share the stack. The framework's vertical offset counts vanilla moodles, Aiteron moodles and *its own* moodles; a mod drawing independently is not in that count, so a framework moodle and a fallback moodle would overlap. A dual-path design should therefore put the fallback in a different screen slot (or count framework moodles itself by reading `MF.MoodleData`, which is a public table but an internal shape). |
| the resident-interface constraint | `ui-and-moodles.md` rule, #1083 | `CleanUI` redraws the status surfaces on the target server. Both routes here — the framework and a private `ISUIElement` — are additive widgets rather than patches of vanilla widgets, so both satisfy that rule; the choice between them is not a `CleanUI` question. |

Read together: "optional framework, own fallback" is a cheaper design than the page's costing assumes, because the framework's route *is* the generic route and there is no third option to weigh. The framework buys shared stacking, per-level texture and text conventions, the Mod Options colour integration, and death/respawn handling; a fallback buys independence from a third-party mod's release cadence and from the version-folder hazard in [D2](#d2--what-the-4220-copy-changed-and-why-the-merge-rule-is-load-bearing). Both draw a client-side widget from a client-side value, so the server-to-client route the nutrition mod has to build is identical either way.

## Minimal consumer

**Untested.** Derived from the read above; never booted, never run under the harness. Kahlua-safe (no `goto`, no `%d`, no `#` on a Java list).

```lua
-- media/lua/client/NutMoodle.lua   -- client only: MF is nil on a dedicated server
-- mod.info should also carry: require=MoodleFramework   (or loadModAfter=MoodleFramework)

local MOODLE = "NutFibre"
local haveMF = false

local function mfReady()
    return type(MF) == "table"
       and type(MF.createMoodle) == "function"
       and type(MF.getMoodle) == "function"
end

-- register once, at boot, before OnCreatePlayer can fire
local function onBoot()
    if not mfReady() then return end                 -- framework absent: fall back or stay silent
    local ok = pcall(function() MF.createMoodle(MOODLE) end)
    haveMF = ok
end
Events.OnGameBoot.Add(onBoot)

-- configure the instance once per character, AFTER the framework's own handler has built it
local function onCreatePlayer(playerNum)
    if not haveMF then return end
    pcall(function()
        local m = MF.getMoodle(MOODLE, playerNum)
        if not m then return end
        -- bad-only moodle: the four nil good thresholds collapse to +MF.TooLargeValue
        m:setThresholds(0.10, 0.20, 0.30, 0.40, nil, nil, nil, nil)
        m:setChevronCount(0)
        m:setValue(0.5)                              -- neutral: draws nothing until a real value lands
    end)
end
Events.OnCreatePlayer.Add(onCreatePlayer)            -- registered after MF.createMoodle -> fires after it

-- the server mirrors the value over the mod's own bus; this is the only write
local function onServerCommand(module, command, args)
    if module ~= "NutritionMod" or command ~= "moodle" then return end
    if not haveMF then return end
    local v = args and args.value
    if type(v) ~= "number" then return end
    if v < 0 then v = 0 elseif v > 1 then v = 1 end   -- the framework does not clamp
    pcall(function()
        local m = MF.getMoodle(MOODLE, args.playerNum or 0)
        if m then m:setValue(v) end
    end)
end
Events.OnServerCommand.Add(onServerCommand)
```

Assets the consumer ships beside it: `media/ui/32/NutFibre.png` … `media/ui/128/NutFibre.png` (or a single `media/ui/NutFibre.png` fallback), and `Moodles_NutFibre_Bad_lvl1..4` plus `Moodles_NutFibre_Bad_desc_lvl1..4` in `media/lua/shared/Translate/EN/Moodles.json` with bare keys.

Three things this sketch is deliberate about, each read off the framework's code rather than guessed. The moodle is invisible until a value crosses a threshold, so a smoke test must push a value and not merely register. `MF.getMoodle` returns nil before the framework's `OnCreatePlayer` handler runs, so the configuration lives in a handler registered after `MF.createMoodle`. And every call into the framework is wrapped, because the framework wraps nothing itself.

## Claims candidates

Grade C throughout; one line per fact, wording as it would go on a page, with its pointer and bound.

1. MoodleFramework registers no engine `MoodleType`: `MoodleType.register`, `registerBase` and every other registry mutator are absent from all four of its version folders, so its moodles are plain `ISUIElement` widgets and the pinned-level wall does not apply to them. — `mod:3396446795/mods/MoodleFramework/42.20/media/lua/client/MF_ISMoodle.lua:56`; bound: C-only; grep over the mod's four folders, snapshot 2026-09-27.
2. MoodleFramework's registration surface is two globals, `MF.createMoodle(moodleName)` and `MF.getMoodle(moodleName, playerNum)`, the first adding one `OnCreatePlayer` handler per name that constructs the widget and the second returning it or nil. — `mod:…/42.20/…/MF_ISMoodle.lua:25`, `:35`; bound: C-only; snapshot 2026-09-27.
3. A MoodleFramework moodle's level and polarity are derived and never settable: `:setValue(value)` is the only write, and `:getLevel()` and `:getGoodBadNeutral()` read the value against eight thresholds whose defaults are `0.1/0.2/0.3/0.4` bad and `0.6/0.7/0.8/0.9` good. — `mod:…/42.20/…/MF_ISMoodle.lua:83`, `:120`, `:127`, `:517`; bound: C-only; snapshot 2026-09-27.
4. A MoodleFramework moodle is added to `UIManager` only while its polarity is non-neutral, and a registered moodle holds `Value = 0.5`, which is neutral under the default thresholds — so a moodle that is registered and never set renders nothing, and an absent render is not evidence the framework failed. — `mod:…/42.20/…/MF_ISMoodle.lua:102-109`, `:268-269`, `:517`; bound: C-only; snapshot 2026-09-27.
5. `MF.ISMoodle:setValue` does not clamp or range-check its argument, so the `0 <= v <= 1` convention is the caller's to enforce. — `mod:…/42.20/…/MF_ISMoodle.lua:83-110`; bound: C-only; snapshot 2026-09-27.
6. MoodleFramework runs on the client only: its four executable Lua files are all under `media/lua/client/`, it ships no `lua/server/` or `lua/shared/` code file, and `MF` is therefore nil on a dedicated server. — `mod:3396446795/mods/MoodleFramework/42.20/media/lua/client/MF_ISMoodle.lua:1`; bound: C-only; file-tree read, snapshot 2026-09-27.
7. MoodleFramework has no multiplayer surface at all: `sendClientCommand`, `sendServerCommand` and `transmitModData` are absent from all four of its version folders, and it registers no `OnClientCommand` or `OnServerCommand` handler. — `mod:…/42.20/…/MF_ISMoodle.lua:29`; bound: C-only; grep over the mod's four folders, snapshot 2026-09-27.
8. The moodle value the executing copy stores is a per-client Lua table, `MF.MoodleData`, keyed by `tostring(char)` — not player modData — so it is neither saved nor transmitted nor stable across a character object being rebuilt, and no other mod's `transmitModData` can wipe it. — `mod:…/42.20/…/MF_ISMoodle.lua:61-79`; bound: C-only; snapshot 2026-09-27.
9. The pre-42.20 copies of `MF_ISMoodle.lua` did write player modData and zeroed `getModData().Moodles` on the session's first moodle, but never transmitted it; the 42.20 copy that executes writes no modData and reads it only for another framework's `MoodleManager` key. — `mod:3396446795/mods/MoodleFramework/common/media/lua/client/MF_ISMoodle.lua:491-501`; `mod:…/42.20/…/MF_ISMoodle.lua:469`; bound: C-only; snapshot 2026-09-27.
10. A server-authoritative value reaches a MoodleFramework moodle only over the consuming mod's own bus: the framework has no transport, so the mod sends the value with `sendServerCommand`, receives it in a client `OnServerCommand` handler and calls `MF.getMoodle(name, playerNum):setValue(v)` there. — `mod:…/42.20/…/MF_ISMoodle.lua:35`, `:83`; bound: inference; a reading of the framework's absent transport beside #0129 and #1153.
11. The 42.20 folder's `MF_ISMoodle.lua` calls `MF.hasBackground`, `MF.hasBGColor` and `MF.hasBorder` from `render()`, all three defined only in `MF_Config.lua`, so the config file is a hard runtime dependency and not an optional extra. — `mod:…/42.20/…/MF_ISMoodle.lua:292`, `:311`, `:321`; `mod:3396446795/mods/MoodleFramework/common/media/lua/client/MF_Config.lua:13`, `:17`, `:21`; bound: C-only; snapshot 2026-09-27. (Sharpens #1319 from a layout derivation to a call-site reading.)
12. The `MF_Config.lua` that executes on 42.20.4 is `common/`'s copy, byte-identical to the `42.0/` copy (`md5 559f9a62eb288ef78e452edfc329e631`), because `42.20/` ships no counterpart for it. — `mod:3396446795/mods/MoodleFramework/common/media/lua/client/MF_Config.lua:2`; bound: C-only; hash and layout read, snapshot 2026-09-27.
13. The `common/` and `42.0/` copies of `MF_ISMoodle.lua` would raise on 42.20.4 if either won the collision: they call `Moodles.getNumMoodles()`, which no class in the jar contains, at the first widget construction. — `mod:3396446795/mods/MoodleFramework/common/media/lua/client/MF_ISMoodle.lua:439`; `jar:Moodles method list, 12 methods, no getNumMoodles; jar-wide grep returns no class`; bound: C-only; jar read 2026-09-27 on `b0bbce05d5`.
14. Those same copies also call `MoodleType.FromIndex(i)`, absent from `MoodleType`'s eight-member list on this build, and read `MoodleType.FoodEaten`, whose Java field is `FOOD_EATEN` (registered from the string `'FoodEaten'`), so the B41 spelling reads nil and the food-eaten moodle would be counted at every level. — `mod:3396446795/mods/MoodleFramework/common/media/lua/client/MF_ISMoodle.lua:448-450`; `jar:MoodleType method list; jar:MoodleType.<clinit> refs 'FoodEaten' -> MoodleType.FOOD_EATEN`; bound: C-only; jar read 2026-09-27.
15. MoodleFramework calls `HasTrait(String)`, `getTypeString` and `loadstring` nowhere in any of its four version folders. — `mod:3396446795/mods/MoodleFramework/42.20/media/lua/client/MF_ISMoodle.lua:1`; bound: C-only; grep over the mod's four folders, snapshot 2026-09-27.
16. MoodleFramework contains no `pcall`: every call it makes into the engine and every call a consumer makes into it is unprotected, so the consumer's own protected call at the boundary is the only guard. — `mod:3396446795/mods/MoodleFramework/42.20/media/lua/client/MF_ISMoodle.lua:1`; bound: C-only; grep over the mod's four folders, snapshot 2026-09-27.
17. MoodleFramework defines `MF` and `MF.createMoodle` at Lua file-load time, therefore before `OnGameBoot` fires, so a consumer detects it with `type(MF) == "table" and type(MF.createMoodle) == "function"` rather than with `require "MF_ISMoodle"`, which raises when the mod is absent. — `mod:…/42.20/…/MF_ISMoodle.lua:7`, `:25`; bound: inference; a reading of the file's top-level statements beside the Lua load order (#0850, #0853).
18. `MF.getMoodle` answers nil until MoodleFramework's own `OnCreatePlayer` handler has built the widget, so a consumer configures and first sets its moodle from an `OnCreatePlayer` handler registered after `MF.createMoodle`. — `mod:…/42.20/…/MF_ISMoodle.lua:29`, `:35-53`; bound: inference; a reading of the registration order.
19. MoodleFramework renders at the frame cadence with no cache: `render()` calls `getXYPosition()` every frame per visible moodle, and that walks every vanilla `MoodleType` in `Registries.MOODLE_TYPE`, reads a `getMoodleLevel` per type, walks another mod's `MoodleManager` modData table and sorts its own moodle-name list. — `mod:…/42.20/…/MF_ISMoodle.lua:267`, `:441`, `:458-494`; bound: C-only; a count of reads off the code, not a measured cost.
20. MoodleFramework's config file mutates the engine's shared `Color.gray` in place from a Mod Options colour picker, defaulting to white rather than vanilla gray, on `OnMainMenuEnter` and on every options apply. — `mod:3396446795/mods/MoodleFramework/common/media/lua/client/MF_Config.lua:6-11`, `:28`, `:45`; bound: C-only; snapshot 2026-09-27.
21. MoodleFramework ships no moodle texture and no `Moodles_*` translation key: a consumer supplies `media/ui/<size>/<Name>.png` (B42) or `media/ui/<Name>.png` (B41 fallback), optional `<Name>_Good_<n>.png` / `<Name>_Bad_<n>.png` per-level icons, and up to sixteen `Moodles_<Name>_<Good|Bad>_lvl<n>` and `..._desc_lvl<n>` keys; the background plate and border come from vanilla's own `media/ui/Moodles/<size>/` textures. — `mod:…/42.20/…/MF_ISMoodle.lua:223`, `:242`, `:430-438`, `:590-591`; bound: C-only; snapshot 2026-09-27.
22. MoodleFramework's `HowTo.txt` documents the moodle text keys in the B41 `Moodles_EN { }` table layout while vanilla 42.20.4 ships `media/lua/shared/Translate/EN/Moodles.json` with bare keys, so the consumer follows the vanilla B42 JSON shape rather than the mod's instructions. — `mod:3396446795/mods/MoodleFramework/HowTo.txt:9-27`; `install:media/lua/shared/Translate/EN/Moodles.json:2`; bound: C-only; snapshot 2026-09-27; that the B41 layout fails for moodle keys specifically is not measured (#1025 measured it for `ItemName`).
23. No vanilla Lua draws the moodle stack: every one of the 29 moodle-named files under the install's `media/lua` is a `Translate/*/Moodles.json`, and the stack is `zombie.ui.MoodlesUI` in Java. — `install:media/lua/shared/Translate/EN/Moodles.json:1`; `jar:MoodlesUI method list`; bound: C-only; file-tree and jar read 2026-09-27.
24. `zombie.ui.MoodlesUI` offers a mod no extension point: its 15 members are `getInstance`, `setCharacter`, `render`, `update`, `wiggle(MoodleType)`, two mouse handlers, `isCurrentlyAnimating`, two texture-size helpers and four `MoodleType`-keyed background helpers, with no add, insert or register. — `jar:MoodlesUI method list`; bound: C-only; jar read 2026-09-27 on `b0bbce05d5`; the class literal appears in `LuaManager$Exposer`'s constant pool, so it is probably Lua-reachable, but exposure was not confirmed by the strict membership test (#0963).
25. The only Lua route to a custom moodle widget is the one MoodleFramework itself takes — `ISUIElement:derive` plus `addToUIManager` — so a mod can draw its own moodle with no framework dependency, at the cost of not sharing the framework's stack offset and therefore overlapping a framework moodle. — `install:media/lua/client/ISUI/ISUIElement.lua:1365`; `mod:…/42.20/…/MF_ISMoodle.lua:56`, `:487-494`; bound: inference; a reading of both trees, never drawn.

## Not read

- Nothing was booted. No claim here is measured: the framework has still never run on 42.20.4, and X29's consequential leg — a framework moodle rendering above level zero on a client — remains open. What this read does is make that probe writable: register one moodle, push `:setValue(0.05)` from the client, and read the widget's presence in `UIManager` and its level through `MF.getMoodle(name, 0):getLevel()`.
- Whether the engine actually resolves `42.20` as this mod's version folder was not observed in a loader log; it is derived from `getModVersionDirName`'s rule (#0825) applied to the folder names on disk.
- Whether `MF_Config.lua`'s `PZAPI.ModOptions` page builds without error on this build, and whether `options:addColorPicker` / `addTickBox` have the signatures it assumes — vanilla's `media/lua/client/PZAPI/ModOptions.lua` was located but not read.
- `ISUIElement`'s own lifecycle beyond `addToUIManager` / `removeFromUIManager`: `initialise`, `createChildren`, `suspend`, `getXYPosition`'s interaction with `keepOnScreen`, and whether `render` is called for an element whose parent is `UIManager` at the same cadence as the Java moodle stack.
- The `Translator`'s treatment of a mod's `Moodles.json` (merge or shadow) for moodle keys specifically; #0841 and #1164 cover the merge generally and the override is unmeasured.
- Aiteron's MoodleManager mod itself — the `getModData().MoodleManager` shape the framework reads is taken from the framework's own code, not from that mod.
- Whether the framework's per-frame cost is material: no command in this repository measures frame time or Lua call counts, so item 19 above is a count of reads and never a cost.
- `CleanUI`'s interaction with a framework moodle (whether it moves, hides or redraws the modded stack) — not read on either side.
- Split-screen and controller behaviour, and the framework's death/respawn path beyond the two lines that remove the widget and suspend it.
