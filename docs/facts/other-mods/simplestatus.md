# Simple Status — the read side of the nutrition store
Verified against 42.20.4 (b0bbce05d5) · 2026-10-01 · scope: one workshop mod torn down as a pure client-side viewer of the player's status numbers — what it draws, how it is built, the techniques it demonstrates, the costs it pays and the one call it makes that crosses the wire; the packets it consumes belong to [wire-packets.md](../wire-packets.md#player-stats-packet) and the transmit wipe to [mp-model.md](../../platform/mp-model.md#wipe-and-replace).

## Key facts
<a id="techniques"></a>

- A vendor-prefixed translation key is a sound load probe: a client-side lookup of one of the mod's own keys answers the mod's value with the miss flag false, and because vanilla defines no key under that prefix and a translation miss returns the key itself, a mod-absent run cannot pass the probe by echoing the key back [#1502/M/n=1].
- A prefixed translation key is a cheap load probe that survives a mod having no scripts and no server state: 52 keys in 13 language trees under a vendor prefix vanilla never uses are this subject's only bus-readable evidence that the mod loaded [#1511/C/snapshot].
- Deriving a client-side indicator from packet-carried inputs beats syncing it, and the technique is the dependency check rather than the trick: it holds only while every input is packet-carried, and here one of them — the weight-band traits — is not, so the dependency list must be written down when it is used [#1508].
- One modData key holding a flat table of scalars exercises all four types the wire carries — string, number, boolean and the containing table itself — and contains none of the ones the wire silently drops, which is a property worth checking deliberately rather than discovering later [#1509].
- Consuming extension points and patching nothing is a clean shape for a UI mod: a derived panel with super-calls, two vanilla event dispatchers and the vanilla mod-options API, with zero vanilla tables touched, zero script blocks and one global name in the whole mod [#1510].

## How it works

Simple Status is a workshop mod that draws the player's status numbers in a panel of bars, and it is in this library because it is the read side of the same store an item-pass rebalance writes.
It holds no state of the game's, defines no item and runs no code on a dedicated server.
That makes it a clean specimen of three things at once: the shape of a mod that consumes extension points instead of patching, the cost of reading a server-pushed store on a frame-count timer rather than at the push, and the blast radius of the one vanilla call it makes that reaches across the wire.

A viewer is a useful subject precisely because it cannot be wrong about the game.
It can only be late, or be reading a field the wire does not carry, or be drawing a number against a scale somebody else chose.
All three of those failures belong to the reader rather than to the store, and all three are what a nutrition overhaul's own interface will meet.
It is also the only teardown subject with a user interface at all, so it is the only place this library has read how a panel is built, persisted and restored.
The question it answers is not whether to ship a panel but what a panel may believe.
A bar is only as trustworthy as the packet behind the getter it reads, and this mod is the library's worked case of that distinction.

The sections below read it in that order.
What it does is the player-facing surface; the architecture is the file layout, the entry points, the data model and the version history behind them; the multiplayer section is the two vanilla mechanisms it consumes and the one it fires.
Everything the mod pays for, and everything it collides with, sits under [Walls and bounds](#pitfalls).

<a id="what-it-does"></a>
### What it does

Simple Status draws a draggable bar panel of the player's status numbers, one row per stat, built on the player-creation event and added to the UI manager [#1469].
The panel is the whole of its player-facing surface: there is no menu screen, no overlay and no second window.
Building on player creation rather than on game start is what makes the panel per-character rather than per-session, and it is why the stat list is fixed the moment the character exists.

The mod offers 36 stats, four of them the nutrition macros and one the weight, of which 18 render by default: 18 carry an explicit shown flag of true, 15 an explicit false, and the three reversible partners inherit their partner's flag and are skipped as primaries by the bar builder [#1470/C/snapshot].
The reversible partners are the pairs whose two ends are the same quantity read from opposite directions, which is why the builder treats only one end of each pair as a bar of its own.
The default set is a choice the mod makes and the player overrides, so the shown flags are configuration rather than capability.
The stats on offer run from health, endurance and the hunger and thirst pair, through the mood, pain and sickness group, to the four nutrition macros, the weight and the weight capacity.
Only that last handful matters to a nutrition overhaul; the rest are along for the ride.

A right-click menu toggles each bar's visibility, the three reversible pairs, the layout, the ruler ticks and the font size, and two key binds come from the vanilla mod-options API; every choice is persisted into one player-modData key and transmitted, so the panel returns where the player left it after a relog [#1471].
That one persisted key is both the mod's whole data model and its whole multiplayer footprint, and the two are the same fact seen from different sides.
Persisting through player modData rather than through a file of its own is the single decision that gives a client-only viewer a multiplayer surface at all.
The layout, the ruler ticks and the font size change how the same numbers are drawn rather than which numbers are read, so none of them touches what the panel costs.
The bar is draggable and lockable, so its position is state the player sets rather than a layout the mod chooses.

Simple Status writes nothing else and owns nothing: every number it draws is read live off vanilla getters at render time, which makes it the read side of the same store a write-side mod attacks [#1472].
A viewer with no store of its own cannot desync from the game; it can only be late, or be reading a field the wire does not carry.
Which of the two it is, bar by bar, is the whole of its multiplayer behaviour.
Reading off the getter at render time also means there is no moment at which the mod could disagree with itself, because it keeps no copy to disagree with.
Nothing on the panel is authoritative, and nothing on it can be made authoritative by the mod.
That is the property a nutrition overhaul's own interface should copy deliberately: draw the authority, never mirror it.

<a id="architecture"></a>
### Architecture

Simple Status is workshop item `2867431511`, one mod, declaring the id `simpleStatus` in a folder named `SimpleStatus` — a case-only drift that resolves on Windows because path lookup is case-insensitive, which is exactly why this subject cannot settle the folder-rename question — and it declares no author, no minimum version, no build version and no dependency in any of the five reachable mod.info files, all of it read cold from the one installed item [#1465/C/snapshot].
An empty dependency list is worth noting for what it removes: nothing has to be installed beside it, and nothing about load order follows from its declaration.
A case-only difference between folder and id is a live hazard on a case-sensitive filesystem and invisible on the one this library reads from, which is why it is recorded as a drift rather than as a defect.

The item has five version folders — `42`, `42.14`, `42.15`, `42.16` and `42.20` — beside a common directory with no media tree and a root-level `B41` media tree, `42.20.4` resolves the `42.20/` tree, whose client Lua files number 7, and the item totals 1 379 005 bytes, swept on 2026-09-30 [T13.57].
The engine loads the newest version folder the build admits ([mod-anatomy.md](../../platform/mod-anatomy.md#version-dirs)), so every other folder is inert on disk, and the version folders below are the only release history the item carries.
The empty common directory earns a line of its own: it exists, the info chain skips it, and it costs the loader nothing.

The mod's architecture is an 8-row file table dated 2026-09-10: 7 client Lua files totalling 1 580 lines, of which the stat definitions are 708 and the panel 583, plus 13 language trees carrying 52 translation keys each, and no script directory in any of its five media trees [#1473/C/snapshot].
Every one of those seven Lua files ends with a newline, so every line count above is real, while the `mod.info` does not, so a newline-counting tool answers 6 for its 7 lines [#1473/C/snapshot].
Paths in the table are relative to the item's `mods/SimpleStatus/` directory.
The table reads the `42.16/` tree, which is on disk beside the resolved `42.20/` tree and is not the one the engine loads.

| File | Lines | Side | Role |
|---|---:|---|---|
| `42.16/media/lua/client/ss.stats.lua` | **708** | client | the 36 stat definitions; **all 12** nutrition reads |
| `42.16/media/lua/client/ISSSBar.lua` | **583** | client | the `SSBar` panel (an `ISPanel` derive), the context menu, `savePlayerData` — the mod's only write |
| `42.16/media/lua/client/ss.utils.lua` | **122** | client | colours, fonts, text measurement |
| `42.16/media/lua/client/ss.main.lua` | **87** | client | config load, the two `Events.*.Add`, the three prints |
| `42.16/media/lua/client/SimpleStatus.lua` | **34** | client | the mod's **only** `_G` name: `SimpleStatus`, with `isNewer` and `addStat` |
| `42.16/media/lua/client/ss.mods.compatible.lua` | **33** | client | **entirely commented out** — a returned no-op |
| `42.16/media/lua/client/ss.options.lua` | **13** | client | `PZAPI.ModOptions` key binds, `setup()` run at require time |
| `42.16/media/lua/shared/Translate/<13 langs>/IG_UI.json` | — | **shared** | the mod's only non-client files: **52** keys per language — 40 `IGUI_SS_BARTITLE_*`, 12 `IGUI_SS_OPT_*` |

Every Lua file sits under the client directory, so the mod is client-only by layout rather than by guard: on a dedicated server it registers nothing and runs no code, and the only part of it the server loads is the shared translation tree.
Client-only by layout is the stronger form of the property, because a guard can be reached by the wrong branch and a missing directory cannot.
The absence of a scripts directory is structural rather than unscanned, which means the mod ships no item, no recipe and no script block for a vanilla definition to collide with.
A mod with no scripts and no server state also has almost no surface for a harness to read, which is what makes its translation tree the only probe available.
The shared translation tree is the one thing a dedicated server does load from it, and the engine reports that as a file-level shadow rather than a key collision.
Nothing about that shadowing changes what the client resolves, because vanilla defines no key under the mod's prefix for it to shadow.

The mod has two entry points, both client-only: the player-creation event builds the panel and the key-pressed event forwards keys to the panel's handler; nothing is patched, because every method it defines is on its own derived panel class or its own stats table and the four vanilla methods it calls are super-calls from overrides on that derived class [#1475].
This is the sanctioned derive-and-super idiom rather than a monkey patch, and it is the reason the mod has no order relationship with anything else in the corpus.
Two dispatchers and a derive are the whole of its coupling to the game, and both dispatchers are vanilla, so there is no patched method for a neighbour to lose a race against.
The panel itself is an ordinary derived widget: it initialises, it prerenders, it handles mouse release and right-mouse release, and each of those is an override that calls its parent before doing anything of its own.
Everything else on the class belongs to the mod, which is why the whole render path can be followed without leaving its two largest files.
The stat definitions are the mod's data rather than its code: each stat is a table of a value function, a percentage function, a text function and a colour function, and the bar builder walks the list and calls them.
That shape is why adding a stat is a one-line registration.

The mod's global footprint is one name, and grepped across the whole installed 230-mod workshop corpus the only files assigning it are this mod's own five copies of the file that declares it, with no other installed mod so much as mentioning the name [#1476/C/snapshot].
One global that nobody else touches is the whole of its namespace risk.
A corpus grep is a dated sweep, so the finding is that nothing installed on that date touched the name rather than that nothing ever will.
The resolved `42.20/` copy's one global carries a registration API a consumer mod can call instead of writing a panel: `SimpleStatus:addStat(name, stat, reverse_stat)` requires `stat.valueFn(player)` and refuses a duplicate or malformed stat with a console message, and `SimpleStatus:addCharacterStat(name, key, opts)` builds that value function from a `CharacterStat.REGISTRY` lookup [T13.60].
A nutrient a mod registers as a character stat could therefore reach this panel through the second call, and whether a consumer should lean on it at all is an [Open](#open) decision.
On the resolved `42.20/` tree `SimpleStatus:addStat` registers a reverse stat into the reverse table, its value list and the reverse lookup at the call, so a stat registered as the alternate view of an existing one reaches the player-creation toggle list and the settings menu, and the bar builder skips only that alternate, leaving the primary on the bar; the registration window is the extender's one remaining constraint [T13.64].

In the resolved `42.20/` copy the panel's prerender advances a frame counter and calls the bar preparation — the only code that calls a bar's value, percentage, text and colour functions — only when the counter is a multiple of 10, resets the counter and adjusts the window size when it reaches 60, and draws the bars from the prepared values on every frame [T13.58].
The throttle is a frame count and not a clock: a faster render reads more often, and nothing on the path is keyed to the arrival of the store it reads.
That reading is taken from the code: no shipped command measures frame time or Lua call counts, so what is recorded is a code shape and not a cost.
The waste that remains scales with the number of visible bars rather than with the number of stats defined, so hiding a bar is still the one thing a player can do to lower it.

The mod's persisted state is one player-modData key holding a flat table of scalars, a 6-row leaf table dated 2026-09-10 that expands to 45 leaves — 6 named ones, 36 per-stat shown flags and 3 toggle flags — beside no sandbox options, no command bus and no global modData in the live tree [#1478/C/snapshot].

| Leaf | Type |
|---|---|
| `SS_pos_x`, `SS_pos_y` | number |
| `SS_locked` | boolean |
| `SS_fontSize` | string (`Small`/`Medium`/`Large`) |
| `SS_isVertical`, `SS_isRulerOn` | boolean |
| `SS_shown_<stat>` ×36 | boolean |
| `SS_tog_fatigue`, `SS_tog_happy`, `SS_tog_dirtiness` | boolean |

Every leaf is a scalar and the container is a plain table, which is what makes the payload safe on the wire and is the property the technique line above is about.
A flat table of scalars is also the easiest shape to reason about across a whole-table replacement, because there is no nesting for a partial merge to disagree over.
Mod options exist beside the key, but they are client-local key binds rather than stored state, so they never reach the server at all.
The per-stat shown flags dominate the leaf count, which is why the table has so few rows and the key expands to so many leaves.
Nothing on the key is server-authoritative, so nothing is lost when the server's copy of it is replaced.

The mod's version history is a 4-row table dated 2026-09-10 running from a flat `B41` tree of 7 files and 1 820 lines, through two trees of 9 files and 1 671 lines keeping the config in global modData with an init and receive pair, to two trees of 7 files keeping it per player [#1479/C/snapshot].

| Folder | Lua files | Lua lines | Config store |
|---|---:|---:|---|
| root `media/` (`B41` flat) | 7 (incl. `ss.json.lua`, 388 lines) | 1 820 | — (`B41` tree, unread) |
| `42/`, `42.14/` | 9 (incl. `client/ss.events.lua` **and `server/ss.save.config.lua`**) | 1 671 | **global** `ModData.getOrCreate("SimpleStatusConfig")` + `ModData.transmit`, with an `OnInitGlobalModData` / `OnReceiveGlobalModData` pair in the server file and the client half in `ss.events.lua` and `ISSSBar.lua` |
| `42.15/` | 7 | 1 582 | **per-player** `player:getModData()` — the server file and `ss.events.lua` both gone |
| **`42.16/`** (the tree the file table reads) | 7 | **1 580** | per-player; adds a 13th (`PT`) translation tree |

The server file and the global config store were dropped at `42.15/`, one version folder before the live tree, so the config name exists in two incompatible stores across the mod's history — a global table keyed by username and a per-player modData key — and a census of the global one is non-discriminating in both directions, because the create-or-get call creates the table for the census itself and the retired server half only ever created it empty [#1480].
Anyone probing this mod for its config has to know which store the version folder under test uses, and has to know that a census of the global one cannot answer either way.
The history also shows the mod moving off a global store and onto a per-player one, which is the direction per-player state should move in general.
Each version folder is a whole tree rather than a delta, and only the live one is read ([mod-anatomy.md](../../platform/mod-anatomy.md#version-dirs)).
Which folder is the live one is itself dated: the workshop corpus drifts under this library, and the file and history tables above name the `42.16/` tree, which the resolved `42.20/` tree stands beside ([#1466/C/snapshot], [lessons.md](../../platform/lessons.md#corpus-drift)).
The retired folders are therefore inert on disk, and a probe that reads them is reading something the game never loads.
It also means the mod's own history is a sequence of complete rewrites rather than a migration, and nothing in it upgrades a stored config from the older store to the newer one.

The mod's three console prints appear on the client in execution order and together prove the bar was built [#1503/M/n=1].
Those three lines are the only positive evidence that any of the architecture above actually ran, because a client-only viewer with no scripts and no server state exposes nothing else a harness can read.
Two of them name the player, which makes them a per-character reading rather than a per-session one.
A mod that printed nothing at all would have left this subject with the translation probe and nothing else.

<a id="mp"></a>
### Multiplayer behaviour

The mod has no networking of its own: no command bus, no server Lua, and nothing it sends but a single vanilla call.
Its multiplayer behaviour is therefore two vanilla mechanisms it consumes and one it fires, and each of the three is owned by another page of this library.
The inbound pair decides whether its bars can be believed; the outbound one decides what it costs a neighbour.
The two halves are independent: nothing it transmits changes what it reads, and nothing it reads changes when it transmits.

Inbound it reads the player-stats packet, whose field list is what decides which of its bars can be trusted on a client ([#1481], [wire-packets.md](../wire-packets.md#player-stats-packet)).
A client-side reader of that store is a staircase behind the server's ramp, and every cross-side gap the mod's bars showed landed inside the band one read skew plus one push window explains ([#1483], [#1486/M/n=1], [wire-packets.md](../wire-packets.md#staircase)).
Weight is the one drawn field whose gap takes the opposite sign, because the client never writes back a weight of its own and its mirror sits below a rising server ([#1484/M/n=1]).
The mirrored weight is also narrowed by the wire, which is visible directly in the values the two sides hold ([#1487/M/n=1]).
The three weight-direction flags the weight bar draws are not on the wire at all and agree anyway, because the engine recomputes them on the client from values that are ([#1489], [#1490/M/n=1]).
A write into the store reaches the client within a measured upper bound, which is what being late amounts to here ([#1493/M/n=1], [mp-model.md](../../platform/mp-model.md#routes-server-to-client)).
Late is the best a viewer of a pushed store can be, and nothing in this mod makes it worse or better than the packet does.
The consequence for a nutrition overhaul's own interface is that a bar can be correct and still trail the authority it draws, and no amount of client-side work closes that gap.

What a client-side reader gets right and wrong splits on the packet's field list both times: on player nutrition everything it draws is right and late by under a second, while on a cooked item the two age-window fields, the cookable and custom-weight flags and the thirst getter are wrong on a client [#1523/M/n=1].
That is the general result the pair of reader teardowns produced, and it is the rule to apply to any viewer: ask what the packet carries, not what the getter returns.
Each half of the split rests on one session and one subject, on a character and an item that were not varied.

Outbound, the mod's whole multiplayer contract is one transmit call fired from seven UI-input-driven sites, each of which rewrites the server's whole copy of that player's modData from the client's [#1482].
Every one of those sites is a mouse or key handler, so nothing but a human at a keyboard can fire them and no harness command can synthesise one.
The drag release is one of the mod's save sites: the panel's mouse-up handler returns at once when the panel is locked and otherwise records the new position and calls the save, which writes the whole config key into player modData and transmits it, so every completed drag of an unlocked panel replaces the server's copy of that player's modData once [T13.61].
Player modData does not cross sides at all until something calls that transmit, which is why this mod's config key reaches the server while a mod that never transmits keeps its settings on the client that set them ([#1637], [mp-model.md](../../platform/mp-model.md#player-moddata)).
The call is a whole-table wipe and replace rather than a per-key update, in both directions ([#1091], [#1496/M/n=1], [mp-model.md](../../platform/mp-model.md#wipe-and-replace)).
The mod's own payload survives it intact, because every leaf is one of the types the modData packet carries ([#1495], [wire-packets.md](../wire-packets.md#moddata-packet)).
The loss falls on a neighbour instead: keep server-authoritative per-player state out of player modData, or guarantee the client's copy is complete before any client transmits ([#1085/M/n=2], [lessons.md](../../platform/lessons.md#anti-patterns)).
The asymmetry is the point — the mod that loses data is never the mod that called the transmit [#1085/M/n=2].
A harness can read what this mod's numbers are but not what the mod does with them, because its panel state never leaves the client until a human moves it.
The outbound half is therefore established through the vanilla call the mod makes rather than through the mod's own handlers.

## Walls and bounds

<a id="pitfalls"></a>
### Pitfalls

Each line below is a cost the mod pays, stated as the mechanism that causes it rather than as a review of the mod.
None is a wall a neighbour runs into; they are shapes not to copy, and the one cost that does fall on a neighbour is under [Multiplayer behaviour](#mp) rather than here.

Cache anything read from a pushed store at the push cadence rather than the frame cadence: a source that changes once a second is read many times a second by an uncached value function, whatever the render loop's own tick [T13.59] [T13.58].
That rule is a code reading of this mod's own render loop set against the measured arrival of its source, and the cost it names is client-side only.
The resolved copy's frame-count throttle lowers the read count without tying it to the push, so a panel that draws more numbers than this one keys its cache to the arrival instead.

The mod hard-codes display bands that encode vanilla's balance — calories at -2000, 1000 and 3500, carbohydrates and lipids at -500, 0 and 1000, proteins breaking at -300, 50, 300 and 700 with multiplier captions between 50 and 300 and at or below -300 — so if those numbers move the colours lie, silently [#1514].
A reader mod's thresholds are a copy of somebody else's balance, and nothing in the engine tells it when that balance changes.
There is no versioning on the bands and no way for another mod to annotate them.
The bands are also the only place the mod encodes a judgement rather than a reading, which is why they are the only place it can be wrong about a game it does not write to.

The mod does environment-dependent work at file-load time, unguarded: its options file calls the mod-options API at require time while the panel file is still being resolved, with no protected call and no nil check, so on a build without that API the whole require chain would take the mod down and no events would register at all [#1515].
The API is vanilla on the build this library reads, so the failure is latent rather than live — which is exactly the kind of dependency that surfaces on somebody else's build.
The blast radius is the whole mod rather than the option, because the failure happens before either event is registered.

Three dead branches read like live code: one settings-menu site indexes the toggle table by the reverse name while its two partner sites key it by the primary name so it never fires, one local is assigned from modData and never read, and a wholly commented-out compatibility function is still called; a seventh oddity is not a defect — one type string is spelled correctly while seven others carry a misspelling, inert because the only test reads the last eight characters [#1517/C/snapshot].
They are recorded because they read as defects to anyone reading the file, not because any of them changes what the mod does.
A reader auditing the mod spends time on all of them before concluding that none matters, which is the cost dead code imposes on a neighbour.

One global the mod calls has no Lua definition anywhere in the game's tree: it is a Java-exposed global reached only from the hover-bar path, present on every B42 build this library has touched, and it is the one name in the file with no Lua source to point at — a version dependency nobody wrote down [#1518/C/snapshot].
A global with no findable definition is a dependency on the engine's own namespace, and the engine's namespace is not part of any published contract.
The name is reached from one hover path only, so the dependency stays invisible until a player hovers the panel in the one layout that uses it.

<a id="compat"></a>
### Compatibility

Simple Status ships no licence or readme file and its fetched Workshop record carries no licence field, so its permissions posture is default Steam Workshop terms: read it, do not vendor it [#1468/W/snapshot].
Nothing of it is copied into this library; only its patterns are taken.
An absent licence is not a permissive one, and an absent author leaves nobody to ask.

Load order is irrelevant to the mod itself — no dependency line, no monkey-patching, no script blocks, no global collision in the corpus and both its events vanilla dispatchers — and its only order-sensitive surface is outbound: a mod extending it must register after its declaring file has run and before the player-creation event, because the bar builder snapshots the stat list at player creation [#1519].
That window is narrow and undocumented by the mod.
A mod that wants a bar of its own therefore has a timing problem to solve and, on the resolved tree, nothing else on the registration side ([Architecture](#architecture)).

The mod replaces no vanilla UI file — it adds a panel of its own to the UI manager — so a UI-replacing neighbour has nothing to fight over, and the only shared resources are screen space and two default key binds, both user-rebindable [#1521].
A UI mod that adds rather than replaces is the shape that survives a crowded load order, and it is the shape a nutrition overhaul's own panel should take.
Screen space is the only resource it genuinely contends for, and that contention is the player's to resolve.
A neighbour built on the command bus has nothing to collide with either, because the mod holds no command-bus site at all (see [Architecture](#architecture)).

The mod is a viewer of exactly the numbers an item-pass rebalance moves: the five getters it draws are the five fields such a pass changes, so any change to the vanilla macro numbers is immediately visible to users through its bar with no cooperation needed and no way to annotate it, and because its display bands are hard-coded, re-basing the macro scale makes its colours and its two multiplier captions wrong silently on every client that has it installed [#1522].
This is a neighbour whose calibration a nutrition overhaul can invalidate without touching a line of it, and the invalidation is silent on both sides.
The visibility cuts the other way too: a rebalance that stays inside vanilla's existing bands is legible to every user of this bar for free.
Depending on the mod is not on the table: it declares no author and no licence, and a client-only viewer gives a nutrition overhaul nothing it cannot draw itself.

Not covered: the flat `B41` root tree was never read and no single-player process was ever booted; no shipped command measures frame time or Lua call counts, so the render loop's cost is a code shape read off the resolved copy rather than a measurement; no bus command can synthesise a click or a key press, so none of the mod's save sites was ever fired from the bus and its persisted config was never observed populated on either side; and the workshop tree drifts under Steam's own updates, so every census here is the dated sweep it names rather than today's disk.

## Open
<a id="open"></a>

One file count on this page is unverified; what follows is that count, the dependency the mod's sharpest claim rests on, and the decisions its facts force on a nutrition overhaul.

- Whether the weight-band traits reach a multiplayer client, and by which packet, is [mp-model.md](../../platform/mp-model.md)'s question, and it is the one hidden input under the weight bar's direction suffix — the flags were measured to agree on a character holding no band trait [#1490/M/n=1].
- The design must decide whether it re-bases the vanilla macro scale, because this bar's display bands and its multiplier captions are hard-coded and go wrong silently on every client that has it installed [#1514, #1522].
- The design must decide where its own per-player nutrient state lives, because any player-modData key the server holds and the client's copy does not is destroyed by this mod's next bar drag [#1482].
- The design must decide at what cadence its own interface reads what it draws, because this mod's resolved copy throttles its reads to a frame count rather than to the push its store arrives on [T13.58] [T13.59].
- The design must decide whether it treats this mod's registration API as an extension point at all, given that it is the only one offered, that the resolved tree keeps its reverse indexes at registration, and that the mod declares no author and no licence [T13.60] [T13.64].
- That the resolved `42.20/` tree holds one mod.info, 7 Lua files, 13 JSON files and 41 PNG files is unverified: the count of the item's file list is not a committed dataset; re-measure by extending the inventory census to record per-tree file counts and reading this item's row [T13.63].

## See also

- [catalog.md](catalog.md#status) — where this mod sits among the teardown picks, and the sweep that chose it.
- [longtermpreservation.md](longtermpreservation.md#mp) — the write side of the same store, and the item fields a client gets wrong.
- [autocook.md](autocook.md#mp) — another client-only mod whose settings ride somebody else's transmit.
- [../wire-packets.md](../wire-packets.md#player-stats-packet) — the packet this mod's bars consume, and the field list that decides which of them are trustworthy.
- [../wire-packets.md](../wire-packets.md#moddata-packet) — the types the modData packet carries and the ones it drops.
- [../nutrition-core.md](../nutrition-core.md#weight-model) — the thresholds and multipliers the weight bar's direction suffix is derived from.
- [../body-and-weight.md](../body-and-weight.md#weight-traits) — the band traits that are the suffix's one uncarried input.
- [../../platform/mp-model.md](../../platform/mp-model.md#wipe-and-replace) — the transmit boundary this mod fires from user input.
- [../../platform/lessons.md](../../platform/lessons.md#anti-patterns) — the rule the transmit hazard is written up as.
