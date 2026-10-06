# MoodleFramework — the moodle widget library
Verified against 42.20.4 (b0bbce05d5) · 2026-10-06 · scope: one workshop mod torn down as a client-side moodle widget library — its registration surface, the value it draws, its version-folder layout, its data model, its missing multiplayer surface, and the techniques and costs a consuming mod inherits; the pinned-level wall belongs to [the wall map](../../reference/wall-map.md#d1), the merge rule to [mod-anatomy.md](../../platform/mod-anatomy.md#version-dirs) and the command bus to [mp-model.md](../../platform/mp-model.md#command-bus).

## Key facts
<a id="techniques"></a>

- A framework moodle is invisible until its value crosses a threshold: the widget joins the UI manager only while its polarity is non-neutral, and its stored value starts at 0.5, neutral under the default thresholds, so a registered but never-set moodle renders nothing and an absent render is not evidence that the framework failed [#2534/C/C-only].
- A framework moodle renders on a dedicated-server client: set to 0.95 it read level 4, joined the UI manager and its render calls climbed, and set back to 0.5 it left the UI manager and its render count held [#1295/M/n=1] [#3192/M/n=1] [#3193/M/n=1].
- A framework moodle set on its bad side reaches a level and joins the UI manager like a good-side one, and its plate is tinted by the polarity the value reaches, a blend of the engine's gray towards its bad or good highlight colour by level, a neutral value drawing in gray: the first bad-side reading read level 3 on the UI manager after a forced value [#3229/M/n=1] [#3234/C/C-only].
- The framework never clamps: `:setValue` stores its argument with no range check, so the consumer holds its own value inside the 0-to-1 convention before the call [#2535/C/C-only].
- A server-authoritative value reaches the moodle only over the consumer's own bus: the server sends it with `sendServerCommand`, and a client `OnServerCommand` handler receives it and calls `MF.getMoodle(name, playerNum):setValue(v)` [#2540/C/inference].
- Detection is a type test, `type(MF) == "table" and type(MF.createMoodle) == "function"`, run at `OnGameBoot` or later: the framework defines `MF` at file-load time, before that event, while a test at the consumer's own file scope runs before the framework's file whenever the consumer's file [loads first](../../platform/loader-and-scripts.md#lua-load-order); `require "MF_ISMoodle"` is no detection, because it fails when the framework is absent [#2547/C/inference].
- Configuration waits for the widget: `MF.getMoodle` answers nil until the framework's own player-creation handler has built it, so the consumer configures and first sets its moodle from a player-creation handler of its own registered after its `MF.createMoodle` call [#2548/C/inference].
- The consumer ships every asset: a sized icon under `media/ui/<size>/` or the unsized fallback, optional per-level icons and up to sixteen tooltip keys per moodle, while the plate and the border are vanilla's own textures [#2551/C/C-only].
- The tooltip keys follow vanilla's `Moodles.json` shape with bare keys and not the `B41` `Moodles_EN { }` table the mod's own instructions show; that the `B41` layout fails for moodle keys is not measured, the failure being measured for item names only [#2552/C/C-only] [#1025/M/n=1].
- The vanilla moodle stack and the framework both draw through a `UIElement` in the UI manager, so any mod can take the framework's route without it, deriving an `ISUIElement`, adding it to the UI manager and drawing in `render()`, without sharing the framework's stack offset; vanilla Lua also draws text from the `OnPreUIDraw` event with no widget, and both readings are of the code, never drawn [#2555/C/inference].

## How it works

MoodleFramework is a workshop library that other mods call to put a moodle of their own on screen beside the vanilla stack.
The mod ships no moodle texture and no moodle text of its own, so every moodle it draws is a consumer's [#2551/C/C-only].
What it does is the registration surface and the value it draws; the architecture is the version-folder layout and what executes from it; the data model is where the value lives; the multiplayer section is the surface it lacks.
Everything a consumer pays for, and everything the framework collides with, sits under [Walls and bounds](#pitfalls).

<a id="what-it-does"></a>
### What it does

A mod cannot register a working moodle type of its own, because the engine pins an unmatched type's level at the minimum every tick [#1140/C/C-only].
MoodleFramework registers no engine `MoodleType`: `MoodleType.register`, `registerBase` and every other registry mutator are absent from all four of its folders, so its moodles are plain `ISUIElement` widgets and the pinned-level wall does not apply to them [#2531/C/C-only].
It is a widget library and not a registry wrapper, so the registry's mutate-then-validate hazard on a duplicate id cannot reach it either [#1198/C/C-only].
The vanilla stack offers no seat for a new moodle: `zombie.ui.MoodlesUI` has 15 members, the constructor, `getInstance`, `setCharacter`, `render`, `update`, `wiggle(MoodleType)`, two mouse handlers, `isCurrentlyAnimating`, two texture-size helpers and four `MoodleType`-keyed background helpers, with no add, insert or register, and although `exposeAll` exposes the class to Lua, reaching it gives a mod nothing to hand a new moodle to [#2554/C/C-only].
`wiggle` and the four background helpers all take a registered `MoodleType`, which is exactly what a framework moodle never is [#2554/C/C-only].
That is why the framework draws beside the vanilla stack rather than inside it.

MoodleFramework's registration surface is two globals, `MF.createMoodle(moodleName)` and `MF.getMoodle(moodleName, playerNum)`: the first adds, on its first call for a name only, one `OnCreatePlayer` handler that constructs the widget, and the second returns the widget or nil [#2532/C/C-only].
The create call takes nothing but the name, so polarity, thresholds, textures and text are all set afterwards on the instance the access call returns.
The create call registers nothing with the engine; it records the name and waits for a player to exist.
The access call reads a per-player-number store, which is what makes the library split-screen safe when the caller passes the player number.

A MoodleFramework moodle's level and polarity are derived and never settable: `:setValue(value)` is the only write, and `:getLevel()` (0 to 4) and `:getGoodBadNeutral()` (1 good, 2 bad, 0 neutral) read the value against eight thresholds whose defaults are 0.1, 0.2, 0.3 and 0.4 bad and 0.6, 0.7, 0.8 and 0.9 good [#2533/C/C-only].
Polarity is a consequence of where the value sits, so there is no good-moodle flag and no level setter to reach for.
A good level and a bad level of the same depth share one level number, and the polarity getter is what tells them apart.
The consequence for a consumer is that it controls a moodle through one float and a threshold table, and nothing else.
A design that wants the level itself to be authoritative has to send a value the thresholds map to that level, because there is nothing to send a level to.
On a live client a value of 0.5 left the moodle at level 0, polarity 0, off the UI manager and with no render call in about 4 s [#3191/M/n=1].
A value moved back to 0.5 after 0.95 took the widget off the UI manager again and held its render count [#3193/M/n=1].

<a id="architecture"></a>
### Architecture

MoodleFramework is workshop item `3396446795`, one mod declaring the id `MoodleFramework`, shipped as the folders `42.0/`, `42.13/`, `42.20/` and `common/` [#1319/C/snapshot].
Its `mod.info` sat in `42.0/` alone when the tree was read on 2026-09-10, its config file has no copy in the newer folders, and a re-read on 2026-10-06 found a `common/mod.info` (modversion 2.8, dated 2026-09-07) beside the `42.0/` one [#1614] [#1319/C/snapshot].
On the 2026-09-10 tree that layout made the layout lint and the engine open different `mod.info` files for it, though both declare the same id [#0824/C/snapshot]; the lint's chain was not re-run on the 2026-10-06 tree, so whether the two still differ is unread.
On `42.20.4` the resolver keeps one version folder, the highest at or below the running build [#0825/C/C-only], and the loader then lets that folder's files win a same-path collision while `common/` supplies everything the folder does not ship [#1310].
Under that rule the mod is whole: the `42.20/` moodle file overwrites `common/`'s, and the config file, having no version-folder counterpart, survives and executes [#1319/C/snapshot].
A boot confirms it: with a dedicated-server client the server logged one loading line for the mod and the client two, the client resolved the namespace table with both registration functions, and the session ran with no error on either side ([#3188/M/n=1], [#0884/M/n=1]).
The `42.0/` and `42.13/` folders are not loaded on this build [#0825/C/C-only]; of their moodle files only the `42.0/` copy, identical to `common/`'s, carries the dead calls set out under [Pitfalls](#pitfalls).

MoodleFramework runs on the client only: every Lua file in its four folders sits under `media/lua/client/` (`MF_ISMoodle.lua` in each, `MF_Config.lua` in `42.0/` and `common/`), it ships no code file under `lua/server/` or `lua/shared/`, and `MF` is therefore nil on a dedicated server [#2536/C/C-only].
Client-only by layout is the strong form of the property: no guard can be reached by the wrong branch, because the server never loads the files.
The only other content under its `media/lua` is a translation tree for its own options page, which is data and not code.
Every framework call a consumer makes therefore lives in the consumer's own client file, and a server file that names `MF` reads nil.
A boot read exactly that: the server's `MF` and the two names under it failed at the table while the client resolved all three [#3190/M/n=1].

The `42.20` folder's `MF_ISMoodle.lua` calls `MF.hasBackground`, `MF.hasBGColor` and `MF.hasBorder` from `render()`, and all three are defined only in `MF_Config.lua`, so the config file is a hard runtime dependency of the moodle file and not an optional extra [#2541/C/C-only].
The config file that executes is `common/`'s copy, byte-identical to the `42.0/` copy (`md5 559f9a62eb288ef78e452edfc329e631` both), because `42.20/` ships no counterpart for it [#2542/C/C-only].
Which of the two identical copies executes is therefore bookkeeping and not behaviour.
That the config file executes is measured: on the client `MF.key` read the mod's name and the four helpers the config file defines resolved as functions, and that no other file supplies them is a reading of the dated tree [#3189/M/n=1].
The merge rule is load-bearing twice over here: it keeps the executing moodle file current, and it is the only thing that supplies that file's config dependency.
Within the mod the Lua loader sorts each block case-insensitively [#0850/C/C-only], so the config file loads before the moodle file in the `common/` block and its options page is built at file scope.

The mod's whole namespace is one global table, `MF`, created with an `or` guard in both files so that either may run first.
Its events are all client-side and are listed under [Multiplayer](#mp).
Its single touch of the nutrition system is a debug print of the player's proteins inside a moodle-level log line [#1589].

<a id="data-model"></a>
### Data model

The moodle value the executing copy stores is a per-client Lua table, `MF.MoodleData`, keyed by `tostring(char)` and not player modData, so it is neither saved nor transmitted nor stable across the character object being rebuilt, and no other mod's `transmitModData` can wipe it [#2538/C/C-only].
The key is an identity string, so a respawn or a reconnect starts a fresh entry and the old one is never pruned.
A consumer therefore sets its value again after every player creation rather than assuming the value survived.
The widget instances live in a second table, keyed by player number and then by moodle name, which is the store the access call reads.

The pre-`42.20` copies of `MF_ISMoodle.lua` wrote player modData and reset `getModData().Moodles` to an empty table on the session's first moodle, but never transmitted it; the `42.20` copy that executes writes no modData and reads it only for another moodle framework's `MoodleManager` key [#2539/C/C-only].
Neither of those older copies executes on this build, and even they could not trigger a transmit wipe, because they never transmitted.
The executing copy still carries the defensive accessor those copies needed: a missing character table, moodle table or moodle entry is recreated on access rather than raising.
With the store out of modData that guard now protects against nothing but its own first use, and it costs nothing to keep.

<a id="mp"></a>
### Multiplayer

MoodleFramework has no multiplayer surface: `sendClientCommand`, `sendServerCommand` and `transmitModData` are absent from all four of its folders, and the only events it registers are `OnCreatePlayer`, `OnPlayerDeath` and `OnMainMenuEnter`, with no `OnClientCommand` or `OnServerCommand` handler [#2537/C/C-only].
The framework carries nothing from the server and asks for nothing from it.
The value a client draws is a value that client's own Lua set, and nothing else.
The player-stats packet carries none of a mod's own fields, so there is no packet a framework moodle could read a server value from [#0129/M/n=1].
The route a server-held nutrient takes to a framework moodle is the command bus [#1153/C/C-only], and the technique is written at [the techniques](#techniques).
Because the executing copy writes no player modData, the [wipe-and-replace hazard](../../platform/mp-model.md#wipe-and-replace) of a player-modData transmit reaches the framework in neither direction: it cannot wipe a nutrition mod's keys, and a nutrition mod's transmit cannot wipe its levels.
A second client never draws another player's framework moodle, because the store is per client process and per character object.
Split-screen is handled by player number, and a caller that omits it gets the active local player's widget, which is wrong for any other local player [#2532/C/C-only].

## Walls and bounds

<a id="pitfalls"></a>
### Pitfalls

The engine has no `Moodles.getNumMoodles()`: no class in the jar contains the name, yet the `common/` and `42.0/` copies of `MF_ISMoodle.lua` call it from their `getXYPosition`, which the constructor calls, so either copy would raise on `42.20.4` if it won the collision [#2543/C/C-only].
The `common/` and `42.0/` copies also call `MoodleType.FromIndex(i)`, which is not among `MoodleType`'s eight methods, and read `MoodleType.FoodEaten`, whose Java field is `FOOD_EATEN` registered from the string `FoodEaten`, so the `B41` spelling reads nil and the food-eaten moodle would count toward the stack offset at every non-zero level [#2544/C/C-only].
Those two copies are byte-identical, the `42.13/` copy walks the moodle registry and calls neither dead method, and a broken copy executes only when neither `42.20/` nor `42.13/` is a version folder the resolver keeps [#2543/C/C-only].
A release that drops both, or ships only folders the resolver scores above the build, puts the broken copy back in play, and a consumer cannot see which copy runs from its own code.

MoodleFramework contains no `pcall` in any of its four folders: every call it makes into the engine and every call a consumer makes into it is unprotected, so the consumer's own protected call at the boundary is the only guard [#2546/C/C-only].
That is the [boundary rule](../../platform/lua-platform.md#pcall) applied in full: the consumer wraps its own framework calls, because the framework wraps nothing.
The harness client runs in debug mode, where an unguarded mod error [parks the client](../../platform/lua-platform.md#debug-break), so an unwrapped framework call is a test hazard as well as a runtime one.

MoodleFramework positions its moodles at the frame cadence with no cache: `render()` calls `getXYPosition()` every frame for every visible moodle, and that walks every vanilla `MoodleType` in `Registries.MOODLE_TYPE`, reads a `getMoodleLevel` per type, walks another mod's `MoodleManager` modData table and sorts its own moodle-name list [#2549/C/C-only].
That is a count of reads off the code, not a measured cost [#2549/C/C-only].
Every moodle a consumer puts on the UI manager adds one such walk to each frame, so a consumer that registers N moodles adds N walks [#2549/C/C-only].
Against the [read-cadence rule](../../areas/ui-and-moodles.md#read-cadence) this is the frame cadence and not the push cadence, and a consumer cannot cache it away because it is the framework's own code.
What a consumer does control is how often it calls `:setValue`, and that is the cadence the read-cadence rule governs.

A mod also cannot retune a vanilla moodle's thresholds nor change what a vanilla moodle does, so the framework is not a way around that wall [#1141/C/C-only].

<a id="compat"></a>
### Compatibility

MoodleFramework calls `HasTrait(String)`, `getTypeString` and `loadstring` nowhere in any of its four folders [#2545/C/C-only].
No removed-API hazard is in its code, so its build risk on this front is only the version-folder layout above.

MoodleFramework's config file mutates the engine's shared `Color.gray` in place from a Mod Options colour picker whose default is white rather than vanilla gray, on `OnMainMenuEnter` and on every apply of its options page [#2550/C/C-only].
Any mod that draws with `Color.gray` on a client that has the framework installed draws with the framework's colour instead.
A nutrition interface that never draws with that colour object is untouched by it.

MoodleFramework has two consumers in the installed corpus holding seven moodles between them: `QualityCooking` creates one, `QualityCookingMeal`, and `MoreDifficultZonesB42` creates six, `SD6Tier1` to `SD6Tier6`, from a `common/media` file [#2556/C/snapshot].
That count is swept on the dated census and the corpus drifts; the census reads each mod's live version folder only, so the second consumer is read from its file.
A nutrition moodle therefore joins a stack that is already in use, and its names must not collide with those.

`MoodlesUI` is called from vanilla's own Lua, where `ISReloadWeaponAction` calls `MoodlesUI.getInstance()` seven times, six of them to wiggle a vanilla moodle, and by no mod in the installed corpus, whose only mentions of the name are comments in MoodleFramework's own copies [#2557/C/snapshot].
No corpus mod touches the Java stack, so there is no neighbour a framework moodle or a private widget could collide with there.
Both the framework and a private widget are additive widgets rather than patches of a vanilla widget, so either satisfies the rule against patching what a resident interface mod redraws [#1083/C/snapshot].

Not covered: vanilla's `PZAPI.ModOptions` signatures the config page assumes; `ISUIElement`'s lifecycle beyond adding to and removing from the UI manager; the translator's treatment of a mod's own `Moodles.json` keys; the other moodle-manager mod whose modData key the framework reads; the framework's frame-time cost; whether `CleanUI` moves, hides or redraws a framework moodle; split-screen and controller behaviour; and the death and respawn path beyond the two lines that remove and suspend a widget.

## Open
<a id="open"></a>

- That no vanilla Lua draws the moodle stack, the 29 moodle-named files under the install's `media/lua` all being translation files and the stack being the Java `MoodlesUI`, is unverified: it rests on a file-name match and a grep of the install's Lua whose output is not a committed dataset; re-measure by a committed scan of the install's `media/lua` [#2553/C/snapshot/unverified].
- Where a mod-drawn column lands beside a framework moodle on screen is unread: the framework's offset counts vanilla, the other moodle manager and its own moodles and nothing else, so a private widget and a framework moodle drawn in one slot overlap [#2549/C/C-only] [#2555/C/inference]; the two were read in separate boots, the column at x 1184 and the framework moodle at x 1238 against a vanilla band from 1238, never together on one screen, and the framework moodle's y read 162 on its bad side where the first session's read 120, for a reason no run explains ([#3223/M/n=1], [#3229/M/n=1], [#3197/M/n=1]).

## See also

- [catalog.md](catalog.md#status) — where this mod sits in the corpus and the layout table its folders appear in.
- [simplestatus.md](simplestatus.md#architecture) — the other client-only interface mod torn down here, and its frame-cadence read.
- [../wire-packets.md](../wire-packets.md#player-stats-packet) — the packet a framework moodle cannot read a mod value from.
- [../../platform/mp-model.md](../../platform/mp-model.md#command-bus) — the bus a server value takes to the client that draws it.
- [../../platform/mod-anatomy.md](../../platform/mod-anatomy.md#version-dirs) — the resolver and merge rule that decide which of its copies executes.
- [../../platform/loader-and-scripts.md](../../platform/loader-and-scripts.md#lua-load-order) — the load order behind the detection technique.
- [../../platform/lua-platform.md](../../platform/lua-platform.md#pcall) — the boundary rule the consumer applies because the framework does not.
- [../../areas/ui-and-moodles.md](../../areas/ui-and-moodles.md#moodle-route) — the nutrition lens on the moodle route.
- [../../reference/wall-map.md](../../reference/wall-map.md#d1) — the pinned-level wall the framework steps around.
