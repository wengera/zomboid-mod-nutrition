# Auto Cook — a client-only mod across two media trees
Verified against 42.20.4 (b0bbce05d5) · 2026-09-22 · scope: what this workshop mod does, how it is split across `common/` and a version folder, the state it keeps, and what it collides with; the engine mechanisms it exercises belong to the platform pages

## Key facts
<a id="techniques"></a>

- Splitting a mod across `common/` plus a version folder keeps the per-build delta small — this mod's B42 port is three files and about 40 lines while the other seven files and 1 238 lines are shared across every build it supports — and the dependency to write down is that the `common/` copy of any shadowed file is dead code on that build and can rot silently [#1353/C/snapshot].
- A `common/`-hosted entry point with a version-folder implementation is one registration against one per-build body: Auto Cook registers its event in `common/` and its handlers call into the version tree, which is how it avoids re-shipping 1 238 lines per build [#1323].
- Queueing the game's own timed action instead of reimplementing it inherits every multiplayer guarantee the vanilla action already has: this mod builds a real add-item-in-recipe action and a one-tick continuation that calls back for the next ingredient, so cooking time, interruption and the crafting rules stay vanilla's [#1354].
- A vendor-prefixed translation key is a load probe for a mod that ships no scripts and writes no server state: vanilla declares zero keys with this mod's prefix and a translation miss returns the key itself, so a client-side text lookup expecting the mod's own value cannot pass on a mod-absent run [#1355].
- Save-and-call wrapping of a vanilla UI method composes with any other mod that adds a tab, which a wholesale replacement would not [#1356].
- A generic tab registrar keyed on the tab name's two translation keys makes adding a character page one call, which is a de-facto public extension point [#1357].

## How it works

Auto Cook automates the clicking of an evolved-recipe meal and nothing else: it adds no items, no recipes and no scripts, and every line of it runs in the client's Lua VM.
It is read here two ways — cold, from the two media trees it ships, and once on a live dedicated server with a real client, where only its load-time state and its read side were reachable.
The engine mechanisms it exercises — the version-folder merge, the translation merge, the player-modData transmit and the Kahlua nil call — belong to the platform pages and are cited here rather than restated.
Read it as two things at once: a worked example of the two-tree layout, and a downstream consumer whose behaviour a food rebalance changes without either mod touching the other.
It is neither a dependency of a nutrition mod nor a conflict with one.
What makes it worth a page is that it is the corpus's sharpest example of the layout, and that its own settings reach the server without it ever asking them to.
Its whole surface on the engine is three client entry points, one nested modData key and a handful of bare globals.
Everything else it touches, it touches through vanilla.

<a id="what-it-does"></a>
### What it does in play

Right-clicking a cooking base item gains an Auto Cook option for every evolved recipe that item can start, and picking it walks one item per ingredient into the inventory, runs the real vanilla `ISAddItemInRecipe` timed action and queues a one-tick `ISContinue` that calls back for the next, leaving simulated cooking time unchanged [#1304/C/C-only].
The mod adds no cooking mechanic of its own.
It drives vanilla's, one ingredient at a time, and stops when the recipe will take no more.
What it changes is the number of clicks, which is why its whole player-facing surface is a context-menu option and a settings tab.

Which ingredient Auto Cook picks is one of five cooking diets chosen from a new Cook tab in the character info window, and the same tab holds six settings persisted per character in player modData, a seventh being commented out [#1305/C/C-only].
The diet is the only setting that decides anything about the meal; the rest cap duplicates, allow rot, or bound the spices.
A player who never opens the Cook tab still gets the context-menu option, because the diet has a default the mod derives at load.
The evolved-recipe lookup, the cookable test and the spice rule that all of it drives are vanilla's, and they are [`cooking-and-recipes.md#evolved`](../cooking-and-recipes.md#evolved).
Nothing it does is a new mechanic; what it removes is the tedium of feeding an evolved recipe one item at a time.
The mod leaves the recipe, the timings and the failure modes exactly where vanilla put them.
That is what makes it safe to read as an exemplar: the parts worth copying are structural rather than behavioural.
Both sentences above are read from the shipped Lua rather than exercised, for the reason given under [Open](#open).

<a id="architecture"></a>
### How it is laid out and where it runs

Auto Cook is workshop item `3388721641`, one mod, declaring the id `AutoCook` in a folder also named `AutoCook`, so its declared id and its folder do not drift [#1301/C/snapshot].
Nothing about this mod is where a single-tree reading would look for it.
Its event registration, its only vanilla patch and its whole translation set live in the shared tree, while the live version folder holds the per-build delta and little else.
The census is therefore the first reading to take, because on this subject a census of one media root is wrong about most of the mod.

Auto Cook's file census over both media trees is 5 rows, 19 files and 129 161 bytes, of which 10 are client `.lua` files totalling 2 155 lines read end to end on 2026-09-10 — 3 files and 917 lines in `42.13/media/lua/client/` against 7 files and 1 238 lines in `common/media/lua/client/`, plus 4 translation files and 5 tree-root files [#1306/C/snapshot].

| Tree | Files | `.lua` lines | Bytes | What |
|---|---:|---:|---:|---|
| `42.13/media/lua/client/` | 3 `.lua` | **917** (395 + 124 + 398) | 42 604 | `AutoCook.lua`, `AutoCook_AutoCraftRecipes.lua`, `ISCharacterCook.lua` |
| `common/media/lua/client/` | 7 `.lua` | **1 238** (362 + 124 + 145 + 117 + 398 + 50 + 42) | 56 469 | the same three **plus** `AutoCook_Diets.lua`, `AutoCook_RISCookMenuInsertion.lua`, `ISCharacterInfoWindow_AddTab.lua`, `ISContinue.lua` |
| `common/media/lua/shared/Translate/EN/` | 4 | 81 | 5 588 | `ContextMenu.json` + `UI.json` (live) and `ContextMenu_EN.txt` + `UI_EN.txt` (B41, never parsed) |
| `common/` root | `mod.info`, 2 PNG | — | 12 405 | — |
| `42/` | 2 PNG | — | 12 095 | icon + poster only; **no `media/`, no `mod.info`** |

A sweep that resolves a single media root sees the live folder only, and here the live folder is the smaller half.
The flag that says so is the media-root list itself: more than one entry means the row's other numbers are a partial view of the item.
The three files that exist in both trees were read in full in the version copy, and their shared copies covered by an exhaustive diff.
Not every census row is code: the translation set and the tree-root files carry the mod's identity and its artwork, and neither is executed.
The shared tree is the bigger of the two by file count and by line count, which is the whole reason the split pays for itself.
A tree that ships artwork and no manifest is inert to the loader, whatever its name suggests.
Reading this mod from its live folder alone would miss its event registration entirely.

Auto Cook's `42/` folder holds two PNGs and nothing else — no `media/` and no `mod.info` — so it contributes no Lua to any build [#1307/C/snapshot].
Auto Cook ships no `media/scripts` in any tree, no `server/` or `shared/` Lua beyond four translation files and no `sandbox-options.txt`, so its script-item-block count of 0 is structurally true rather than unscanned [#1308/C/snapshot].
That distinction matters when reading a corpus sweep: a zero can mean nothing was found or that there was nothing to find, and here it is the second.
Auto Cook is 10 client Lua files across both trees with 0 server and 0 shared Lua, its only shared content being four translation files, and a sweep of both trees returns zero for `sendClientCommand`, `sendServerCommand`, `OnClientCommand`, `OnServerCommand`, `transmitModData`, `sendItemStats` and `SandboxVars` [#1330/C/snapshot].
The shared Lua it does ship is data rather than code, so there is no shared-tree execution path to reason about at all.

Three entry points exist and all three are client-side, and the two that matter live in the shared tree.
Auto Cook's only `Events.*.Add` is in its common tree and registers on `OnPreFillInventoryObjectContextMenu`, which vanilla triggers on every inventory right-click, so the live version folder holds no event registration at all and the mod's inventory row reads as inert [#1320/C/snapshot].
Auto Cook's second entry point is a call to `addCharacterPageTab` at file load from its version tree, while the function itself is defined only in the common tree, and it wraps three `ISCharacterInfoWindow` methods [#1321].
Auto Cook's third entry point runs `AutoCook:init` on the local player only behind `isDebugEnabled`, so it is dead on a normal client [#1322].
The shape worth naming is the split itself: the registration lives in the shared tree and the body it calls lives in the version tree.
It is a legitimate pattern, and the author's reason for it is plain in the file sizes — it is how a per-build port stays small.
Its cost falls on whoever reads the corpus from an inventory rather than from the files, because a mod laid out this way looks like it registers nothing.

Auto Cook's version tree changes exactly three files against its common tree — the main file by 33 lines, the auto-craft recipe file by 1 and the character tab by 3 — and its `42/` tree contributes no Lua, so the per-build delta is three files because the merge rule lets the rest be shared [#1332/C/snapshot].
The version tree is the current build's delta; the shared tree is the older baseline that every build this mod supports still runs.
The translation pair the engine does read is the one the mod's own load probe leans on, and it lives in the shared tree with everything else durable.
That merge rule is the engine's and not the mod's: the version folder's file wins a same-relative-path collision while `common/` supplies everything the version folder does not ship ([#1048/M/n=2], [`platform/mod-anatomy.md#version-dirs`](../../platform/mod-anatomy.md#version-dirs)), and translations merge into a shared map instead of shadowing ([#0840/C/C-only], [`platform/mod-anatomy.md#translations`](../../platform/mod-anatomy.md#translations)).
Every census figure above is one item read cold as installed, on a workshop corpus that drifts between sweeps, so each is a dated snapshot rather than a standing property of the mod.

<a id="data-model"></a>
### The state it keeps, and what it does at load

The mod keeps one nested key in player modData and one Lua global, and they do not agree about what persists.
The modData key is what a census can see; the global is what the mod actually reads when it decides anything.
Both come into existence at spawn with no user input, which is the only reason any of this was reachable without a right-click.

The character-info window is built at spawn with no user input — `createPlayerData` instantiates it, `addToUIManager` reaches `createChildren` through `instantiate`, the wrapped `createChildren` adds the Cook view, and `addChild` instantiates it into `ISCharacterCook:createChildren`, which calls `AutoCook.init` — so the mod's nested player-modData key exists the moment the window is built rather than when the tab is opened [#1324].

```
ISPlayerData.createPlayerData(id)                media/lua/client/ISUI/PlayerData/ISPlayerData.lua:168
  ISPlayerDataObject:new(id)                     …/ISPlayerDataObject.lua:93-95
    ISCharacterInfoWindow:new() :initialise() :addToUIManager()
      ISUIElement:addToUIManager -> :instantiate()          …/ISUI/ISUIElement.lua:1365-1368
        ISUIElement:instantiate  -> self:createChildren()   ISUIElement.lua:1007
          ISCharacterInfoWindow:createChildren   <- WRAPPED, common/…/ISCharacterInfoWindow_AddTab.lua:7
            pageType:new(...) ; :initialise()               …_AddTab.lua:10-11
            self.panel:addView(getText("UI_Cook"), view)    …_AddTab.lua:13
              ISTabPanel:addView -> self:addChild(view)     …/ISUI/ISTabPanel.lua:494
                ISUIElement:addChild -> otherElement:instantiate()   ISUIElement.lua:1455-1457
                  ISCharacterCook:createChildren            42.13/…/ISCharacterCook.lua:15
                    AutoCook.init(self, self.char)          42.13/…/ISCharacterCook.lua:17
                      player:getModData().AutoCook = {}     42.13/…/AutoCook.lua:38
```

The tab's own initialiser does not reach that chain; the instantiate inside the parent's add-child call does.
So the window-build path, not the player, is what creates the key.
Nothing this mod keeps is server-authoritative, and nothing it keeps is shared between players.

Auto Cook's data model is one 8-row table dated 2026-09-10: one nested player-modData key with eight dotted leaves written by four handlers and never transmitted by the mod, one Lua global, no sandbox options and no item or recipe scripts [#1325/C/snapshot].

| Store | Key | Written by | Transmitted? |
|---|---|---|---|
| `IsoPlayer:getModData()` | **`AutoCook`** — a nested table, created **empty** | `AutoCook:init` | **never by this mod** (no `transmitModData` call anywhere in the item) |
| … `.CookMode` | integer 1-5 | `onComboSelectCookMode` | never |
| … `.MaxDuplicate`, `.MaxSpices` | integer | `onNumberInput`, only when `button ~= nil` | never |
| … `.PrioritizeVariety`, `.UseRotten`, `.CompleteExistingMeal`, `.SmartSpices` | boolean | `onTickChange` | never |
| … `.AutoCraftIngredients` | forced `false` **on every load after the first** — the write sits in `init`'s **`else`** branch, the "load from modData" path taken only when the key already exists | `AutoCook:init` | never |
| `_G.AutoCook` | 23 file-scope scalars + the functions of three files | file scope, and the function definitions in both trees | n/a (a Lua global) |
| sandbox options | **none** — no `sandbox-options.txt`, no `SandboxVars.` reference in either tree | — | — |
| item / recipe scripts | **none** — no script item blocks, no `media/scripts` in any tree | — | — |

Auto Cook's `AutoCraftIngredients` leaf is forced false only on the load-from-modData path, which `init` takes when the key already exists, so it is not written at all on a character's first load [#1326].
A cold read that calls that write unconditional is wrong about the only load a new character ever performs.
On a fresh character Auto Cook's nested modData table is empty and all eight of its dotted leaves are missing — on the client at every snapshot and on the server from the transmit onward [#1327/M/n=1].
Auto Cook's live settings sit on its Lua global rather than in modData: `CookMode` read 1, `MaxSpices` read -1 and `Verbose` read false on the client, and a `CookMode` of 1 rather than 5 says the fixture character carries no Nutritionist trait [#1328/M/n=1].
The reader that produced those values walks the global and never calls what it finds, so the functions it resolved were read and not invoked.
The dotted leaves are the tab's own settings, and the global is the running copy of them.
A handler writes the global and then copies it into modData, so the two diverge only where `init` writes the global alone.
That is the one place a persisted value is lost, and it is a derived default rather than a player's choice.
`AutoCook:init` creates the empty modData table on a first run and writes the Nutritionist default `CookMode` of 5 onto the Lua global only, never into modData, while on later runs it copies every persisted modData key onto the global — so the settings are per client rather than per character [#1329].
The practical consequence is that a modData reading of this mod says it is installed and says nothing about how it is configured.

Auto Cook's nested key is present in the client's player modData 1.044 s after session ready with no user input, in a table of 6 keys [#1333/M/n=1].
That key proves only that the common tree ran and the require chain completed, because both copies of the file write it at the same line.
Which physical copy executed is the version-dir reading the platform page owns ([#0828/M/n=2], [`platform/mod-anatomy.md#version-dirs`](../../platform/mod-anatomy.md#version-dirs)).
Every reading in this subsection is one session on one fixture with one fresh character on one machine.

<a id="mp"></a>
### What it does on a dedicated server

Authority lives entirely on the server, and the mod does not participate in maintaining it.
It has no networking of its own, so its whole multiplayer contract is reading two server-owned stores off the client's mirror and queueing vanilla timed actions that do their own syncing.
What it does instead of sending is read, and every read it makes is of something the server owns.
The exposure question for a mod shaped like this is therefore not what it sends but what a neighbour sends on its behalf.

Before any transmit the server holds no Auto Cook key at all: the key is missing at both the join census 3.073 s after session ready, with a key count of 0, and the late census at 42.102 s, with a key count of 4 [#1334/M/n=1].
The keys the server does grow in that window are vanilla's own, written server-side and lazily, so a server key count is only a reading beside its wall offset.
Auto Cook has 9 `getModData` sites per tree and 0 `transmitModData` calls, so it never puts its settings on the wire itself, yet one `transmitModData` by any other mod on that client pushes its whole nested table to the server [#1339/M/n=1].
In this session the neighbouring transmit was the harness probe rather than a second mod.
The transmit's own shape — a whole-table wipe and replace in either direction — is [`platform/mp-model.md#wipe-and-replace`](../../platform/mp-model.md#wipe-and-replace) ([#1496/M/n=1], [#1042/M/n=2]).
On a real server the neighbour is an ordinary UI event: the read-side teardown beside this one calls the transmit immediately after writing its config key ([#1626], [`catalog.md#api-surface`](catalog.md#api-surface)).
For a nutrition mod the reading cuts both ways, because the same passive route that carries this mod's settings would carry ours.
The mod's own contribution to the wire is nothing at all, and that is exactly why the exposure is easy to miss.
What crosses is what a neighbour's call carries, and what it carries is the whole table rather than the key that changed.
A nutrition mod that wants per-character settings has the same shape and inherits the same exposure.
Privacy is not a property any mod can claim for what it leaves in player modData.

Auto Cook reads server-owned state at 7 sites, all of them on the client: the five nutrition macros and three weight-direction flags for the smart-spice gate, the nutritionist filter and the tab's warnings, the two diet comparators, the freshness getters, the leftovers getters, and one script-item read [#1349/C/snapshot].

| Site | Reads | Owner |
|---|---|---|
| the version tree's `AutoCook.lua` | `getWeight`, `isIncWeight`, `isDecWeight` — the smart-spice gate | **server** |
| the version tree's `AutoCook.lua` | `getWeight` / `getLipids` / `getCarbohydrates` / `getProteins` — the nutritionist filter | **server** |
| the version tree's `ISCharacterCook.lua` | the same five, for the tab's warnings | **server** |
| `common/…/AutoCook_Diets.lua` | `getProteins`, `getWeight` — the diet comparators | **server** |
| `common/…/AutoCook_Diets.lua` | `getOffAge`, `getOffAgeMax`, `getAge` — the freshness diet | **server, and never synced** |
| `common/…/AutoCook_Diets.lua` | `getCalories`, `getHungChange` — the leftovers diet | server; `hungChange` is packet-carried, the derived thirst getter is not faithful |
| the version tree's `AutoCook_AutoCraftRecipes.lua` | `item:getHungerChange() < 0` on a **script** item | script, not instance — identical on both sides for free |

Every decision Auto Cook takes is taken on the client from its mirror of server-authoritative state, and because the nutrition store is pushed at 1 Hz and at eat time ([#0114], [`wire-packets.md#player-stats-packet`](../wire-packets.md#player-stats-packet)) the macro reads are right and late by under a second [#1352/C/C-only].
The player reads are therefore the safe half of its read set, and the item reads are the exposed half.
On the read side the split is between the player store and the item store, and only one of the two is pushed on a schedule.
The tab's warnings read the same macros the spice gate does, so a stale mirror would show in the UI as well as in the choice.
Auto Cook's freshness and leftovers diets rank ingredients on item fields that on a dedicated server may be the last pushed values rather than live ones, because the age getters never cross the wire and a held item's live fields move on a client only while something is pushing them [#1350/C/inference].
The aging half of that is measured and belongs to the packet page ([#1242/M/n=1], [`wire-packets.md#desyncs`](../wire-packets.md#desyncs)).
The consequence for the diets is reasoning from the packet's field list rather than a measurement, because the diets themselves were never run.
Auto Cook's auto-craft filter reads the hunger change off a script item rather than an instance, so that value is identical on both sides for free [#1351].
That contrast is the lesson of the whole subsection: a script read costs nothing to trust, and an instance read costs a sync guarantee this mod does not have.

## Walls and bounds

<a id="pitfalls"></a>
### What it gets wrong, and the mechanism behind each

Each line states what the mod pays for, and names the engine row that explains why it is a cost rather than a bug.
None of them breaks the mod as shipped; each is a price the layout or the language makes easy to pay without noticing.

- Auto Cook's common tree carries four calls to members `42.20.4` removed — three to the string-argument trait test and one to the item type-string getter — none of them at file scope, so a common-wins state would not die at file load but when the character-info window is built at spawn, where the tab's `createChildren` reaches three of the four [#1358].
  The failure would be silent and partial, because an unguarded Kahlua nil call aborts the rest of the handler body it fires in ([#0948/M/n=1], [`platform/lua-platform.md#raises`](../../platform/lua-platform.md#raises)).
  Those calls are harmless only because the version folder wins a collision ([#1048/M/n=2]), which no line of the mod asserts and no reader should assume.
- Encoding a decision in a nil return breaks when the caller's fallback is take whatever is next: this mod's diet comparator returns nil to avoid over-protein, and on the next iteration the guard is false so control falls to the branch that accepts the next candidate outright with no comparison at all [#1359].
  A sentinel value, or a value-and-reason pair, is what the caller needed instead.
- Three vanilla UI wrappers in this mod each capture the current value into a local and replace the method, so a second execution of the file or a second registrar call stacks a second wrapper: two Cook tabs, and the tab name appended twice to the saved layout [#1360].
  The only in-game route to a second execution is a Lua reload, and the measured session ran under an explicit no-reload constraint, so the stacking is read rather than seen.
  The sentinel that makes wrapping reload-safe is [`platform/lua-platform.md#dev-loop`](../../platform/lua-platform.md#dev-loop) ([#0943/C/C-only]).
- Auto Cook defines four bare globals, none of which collides with vanilla, and the tab registrar is the sharp one: any other mod defining a function of that name replaces this one wholesale, and this mod's own call site would then run the other mod's implementation [#1361/C/snapshot].
  All four were checked absent from the game's whole Lua tree on the day of the sweep, which is a statement about that tree and not about the workshop.
- Auto Cook's `init` copies every persisted modData key onto a Lua global, so a second character on the same client inherits the first one's diet until its own `init` runs, and the Nutritionist default is written to the global only and is therefore re-derived every load and silently lost as a persisted value [#1362].
  The measured corollary is the empty table under [the data model](#data-model): a census of this mod reads as installed and unconfigured whatever the player picked before.
- Auto Cook carries about fifty lines of crafting path behind a flag hard-disabled at file scope and re-forced in `init`, with its tick box commented out, and beside it four inert code defects: a method declared with no parameters but called with an argument, an `init` invoked with a dot on a method declared with a colon, and an unparenthesised `and`/`or` that means the recipe enabled test is never consulted on a non-debug client [#1363].
  All of it is cosmetic, and it is recorded only because it reads like a live feature.
- Auto Cook ships two B41-layout translation text files carrying the same 38 strings as its live JSON pair, about 5 KB of inert weight that `42.20.4` never parses, because the `Translator` opens `.json` and nothing else [#1364].
  The cost is not the bytes but a maintainer editing the file the engine never opens.
- A mod can hold server-authoritative state in player modData only with a workaround, because the transmit that carries it is someone else's to call ([#1151/M/n=2], [`reference/wall-map.md`](../../reference/wall-map.md)).

<a id="compat"></a>
### What it collides with, and what a nutrition mod must do about it

Auto Cook declares nothing at all about its neighbours, so every collision below was found by reading rather than from a manifest.
Two of them are with one other mod in the corpus, one is with a mod the corpus does not have, and the rest is the coupling with a nutrition mod.
That coupling runs one way: this mod consumes what a food rebalance defines, and defines nothing a rebalance could contradict.

- Auto Cook's `mod.info` is 9 lines carrying 9 keys and has no `require=`, `incompatible=`, `loadModAfter=` or `loadModBefore=` line, so the mod declares an empty dependency list and no load-order constraint of any kind [#1302/C/snapshot].
  An empty dependency list is a fact about the manifest and never a guarantee about runtime, as the lines below show.
- Load order is irrelevant to whether Auto Cook works and the mod declares no order at all; its one ordering-sensitive surface is outbound, because two mods both defining the tab registrar collide on the name and the later loader wins [#1365].
- Auto Cook patches three vanilla Lua methods, all on the character info window, and no Java surface, no script blocks and zero vanilla script-block redefinitions, because it ships no scripts at all [#1366/C/snapshot].
  That patched surface is entirely UI, so nothing it replaces can change what an item is worth.
- CleanUI ships no copy of the character info window in any of its trees and never mentions the tab registrar's name, so Auto Cook's three wrappers have nothing to fight; what it does replace is Auto Cook's only entry point, the inventory context-menu file, which exists in only 3 of its 7 trees, so on a `42.12` to `42.14` resolution the collision does not arise [#1367/C/snapshot].
- Because `pcall` does contain a Kahlua nil call ([#0944/M/n=1], [#0945/M/n=1], [`platform/lua-platform.md#pcall`](../../platform/lua-platform.md#pcall)), CleanUI's pcall-wrapped event trigger contains a raising listener, so with that mod resident a raising listener on the inventory context-menu event shows as that mod's own printed failure line rather than a raw Lua error and a driver's nil-call regex must add it [#1369/C/C-only].
  No catch names the missing member either way, so a console grep stays the witness for a raise inside that dispatch.
- CleanUI's copy of the inventory context-menu file is a fork of a `42.19` vanilla file, so it silently reverts any vanilla change to that menu made since, for every mod on that event rather than only for this one [#1371/C/snapshot].
- Auto Cook carries an explicit compatibility shim for a mod not in the corpus: a require of a file that ships with that mod, inside a file-scope conditional on the mod being active, which makes it a load-order-sensitive require; the guard itself is the same call vanilla makes and the branch is dead here [#1372].
  A require inside a file-scope conditional is the one place this mod's own load can depend on another mod being present.
- Auto Cook adds no items, no recipes, no script blocks and no sandbox options, so a rebalance of vanilla food macros changes what it chooses and nothing it defines; the coupling runs the other way, because a nutrition mod must not break the evolved-recipe lookup, the recipe item and cookable tests, the spice rule or the five macros and three direction flags it reads, and new mod nutrients will be invisible to its diets [#1377/C/snapshot].
  A nutrition mod therefore has to treat this one as a reader it must not starve, rather than as a dependency to satisfy.
- Auto Cook ships no licence or readme file and its fetched Workshop record carries no licence field, so its permissions posture is default Steam Workshop terms: read it, do not vendor it [#1303/W/snapshot].
- Neither CleanUI reading booted the two mods together: both are cold reads of whole items, taken on a corpus that drifts between sweeps.

Not covered: every other consumer of the evolved-recipe path outside this library's corpus, the single-player path, on which no reading here was taken, the mod's own save and load round trip, and any build other than the one in the stamp.

## Open
<a id="open"></a>

- Auto Cook's cooking pipeline was never reached by any run: its only entry is a context-menu option whose handler runs on a right-click, and nothing on the shipped bus clicks, presses a key or calls a trigger, so the item chooser, the food filter, the spice gate, the acceptance test and all five diets stay code readings until the bus can drive a context menu [#1378/C/C-only].
- Whether a pcall-wrapped event trigger changes what an unguarded raise does inside a dispatch — settled by a three-mod profile booted twice with the two mod orders, reading the loader's override tail, both mods' globals and the client console for both failure signatures; -> X26 ([#1292/C/open], [`areas/open-questions.md#x26`](../../areas/open-questions.md#x26)).
- Whether the weight-direction flags this mod's spice gate reads can desync is the packet page's question rather than this one's ([#1348/C/inference/open], [`wire-packets.md#open`](../wire-packets.md#open)).
- Decision: whether the nutrition mod keeps any per-character settings in player modData at all — whatever sits there is one neighbour's transmit away from the server, whatever the owning mod does [#1339/M/n=1].
- Decision: whether the nutrition mod exposes its new nutrients to third-party choosers or leaves them invisible — a diet mod optimises against whatever macro set it can read, silently [#1377/C/snapshot].
- Decision: whether the nutrition mod ships a `common/` tree beside its version folder — the per-build delta is small and the cost is a shadowed copy that rots unread [#1353/C/snapshot].
- Decision: whether the nutrition mod mirrors settings onto a Lua global at all — a global is a cache nothing persists, and the modData is the only truth [#1362].

## See also

- [`wire-packets.md`](../wire-packets.md) — the packets this mod reads off and never writes to, and the fields that never cross.
- [`platform/mp-model.md`](../../platform/mp-model.md) — the player-modData transmit that carries its table, and the wipe-and-replace shape on both sides.
- [`platform/mod-anatomy.md`](../../platform/mod-anatomy.md) — the version-folder merge rule this mod's whole layout rests on, and the translation merge beside it.
- [`platform/lua-platform.md`](../../platform/lua-platform.md) — the Kahlua nil call, the protected call that contains it, and the wrapper sentinel.
- [`platform/lessons.md`](../../platform/lessons.md) — the layout rule and the anti-patterns this teardown feeds.
- [`cooking-and-recipes.md#evolved`](../cooking-and-recipes.md#evolved) — the evolved-recipe system every Auto Cook option starts.
- [`nutrition-core.md`](../nutrition-core.md) — the macro store its diets rank on.
- [`catalog.md`](catalog.md) — the corpus sweep this mod's row comes from.
- [`simplestatus.md`](simplestatus.md) — the read-side teardown whose transmit sites make this mod's modData exposure concrete.
- [`longtermpreservation.md`](longtermpreservation.md) — the item-side teardown at the other end of the same sync question.
- [`reference/wall-map.md`](../../reference/wall-map.md) — the sync verdicts cited above, in one place.
- [`reference/experiments.md`](../../reference/experiments.md) — the named experiments for the rows under Open.
