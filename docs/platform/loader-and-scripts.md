# Loader and scripts
Verified against 42.20.4 (b0bbce05d5) · 2026-10-01 · scope: how a relative path becomes one file, how the Lua execution list is built, what the `item` and `craftRecipe` grammars are, and the block-level merge inside a script file — bucket append, per-key merge, sorted replay, path collisions, default modData, item identity, name resolution, per-side loading and reload; the file-level merge between a version dir and `common/`, translations and the checksum gate are `mod-anatomy.md`, and the item key reference is `facts/food-item-model.md`.

## Rules

- Restate only the keys a pass changes: a repeated `item` block appends a body and the reset before it is a bare return, so every key a later body omits keeps the value an earlier body gave it [#2007/C/C-only, #1006/M/n=1].
- Give every script file a mod-unique relative path: the file map holds one absolute path per relative path and the script walk drops a repeat, so the loser's blocks are never parsed — a code reading, since no session has shipped the same relative script path from two mods [#1046, #1047/C/C-only].
- Give every Lua file a mod-unique relative path too: a mod file at a vanilla relative path runs in vanilla's slot, before every mod's own block, wherever the mod sits in `Mods=` — also a code reading, since no boot has exercised a vanilla-path replacement [#0852/C/C-only].
- Never assume a `require` reaches your own copy: it resolves through the same merged map, with no per-mod search path, to whatever absolute path that map currently holds [#0853/C/C-only].
- Do not derive body order from `Mods=`: bodies replay sorted by the stored script path, so a mod's position in `Mods=` decides nothing about which body wins a key [#1055/M/n=2].
- Keep `template_` out of a script file's basename: the replay comparator pre-sorts every `template_`-prefixed basename ahead of every other file before it compares paths at all [#1233/C/C-only].
- Assign a mod's own file-scope Lua globals at file scope: the mod tree executes inside `LoadDirBase` ahead of the engine's own `Load`, and an assignment from an event handler or a bus command afterwards is inert [#1216/C/C-only].
- Put a per-type value in the item script, or in a Lua table keyed by full type where no script key reaches, rather than in per-instance Lua state: script data loads per side and never crosses the wire, so the two sides agree for free [#1058/M/n=2, #2682/C/C-only].
- Reach a new nutrient on an item through an unrecognised key inside the vanilla `item` block, and on a drink's fluid through a Lua table keyed by the fluid's type string: the parser's default arm rawsets the key into the item's default modData and every instance receives a deep copy, while a `fluid` block has no default arm and stores no unrecognised key [#1089, #1187/C/C-only, #2676/C/C-only, #2682/C/C-only, #2684/C/C-only].
- Spell a script value for the type its key parses as: an int, a float, a bool where only the literal `true` is true, a semicolon-split list or a bare string [#0214].
- Keep every value on a known key well formed: a malformed value raises `InvalidParameterException` and aborts the load, and a line with no equals sign dies on the split [#1188/C/C-only].
- Qualify a modded script name with its module at every lookup: a dot-less name is sent to the base module and resolves against neither spelling the shipped lookup tries [#1455/M/n=1].
- Address a redefined item by its full type and never by net id or script file name: the per-body init runs once per appended body, re-stamping the file name and allocating a fresh net id [#1007/C/C-only].
- Declare a mod's own items in the mod's own module when the mod adds rather than rebalances: a new name collides with nothing and grows the pool by exactly what it declares [#1020/M/n=1].
- Read an `overrides` line with an empty tail as "this mod ships no `common/`": relativising a missing directory against itself yields the empty string, which marks no collision at all [#1452, #1217/M/n=1].
- Halve a client's `overrides` count before comparing it with a server's: the loader prints one line per shadowed file per Lua state, and a multiplayer client runs two [#0829/M/n=1].

## How it works

<a id="file-map"></a>
### The file map

`ZomboidFileSystem.loadMod` runs two unconditional `activeFileMap` passes, one per media root, so the version dir's entry overwrites `common/`'s for a same relative path, and `ZomboidFileSystem.getAbsolutePath` is literally a lookup of the lower-cased relative path in that map [#0827/C/C-only].
That direction — which of a mod's two trees supplies a file — is [the version dir against `common/`](mod-anatomy.md#version-dirs) and is not restated here; this section owns the map itself.

`activeFileMap` holds one absolute path per relative path, filled by those two unconditional puts, and the script walk drops any relative path it has already seen [#1046].
`getAbsolutePath` is that map's `get` of the lower-cased relative path and nothing else, and the map is pre-seeded with vanilla's whole media tree before any mod loads, so only paths under `media/` can shadow vanilla while a mod's tree-root files enter the map from the `common/` pass and can be shadowed only by that mod's own version dir [#1312].
The map is therefore the whole of path resolution: there is no search order to appeal to after it, and a file that lost its key is not read from anywhere.
Every key in it is lower-cased, so two files whose relative paths differ only in case are one key and one of them is unreachable — a consequence read from the lower-cased key rather than a collision any run has produced.
A mod's own tree-root files — its `mod.info`, its icon and its poster — share the map with everything else, and only that mod's own version dir can shadow the `common/` copy of one; the print's gate names no tail but `mod.info` and `poster.png`.

Before each overwriting put the loader prints one line per shadowed file in the form `mod "<id>" overrides <relative path>`, from a format constant through the mod debug channel, gated on the key already existing and on the path not ending `mod.info` or `poster.png` [#1311].
Measured, the loader prints one `mod "<id>" overrides <relpath>` line per shadowed file per Lua state, the tail being the lower-cased relative path: one line on the server and two on the client for a single shadowed file [#0829/M/n=1].
A mod that shadows nothing and ships `common/` prints no `overrides` line at all: every such line in that session came from the shadowing mod, and the `common/`-only mod that collided with nothing printed none [#0830/M/n=1].

A mod that ships no `common/` prints an `overrides` line with an empty tail, one per such mod per Lua state, because the loader reaches the folder search's non-directory branch and the relative file comes back empty [#0832/M/n=1].
The committed evidence for that arm is the mechanism plus one of the session's three empty tails, the others lying in console logs the repository does not keep.
The cause is separate from any collision: the folder search adds a path to the load list as a file when it is not a directory, which a missing directory is, and relativising that path against itself returns the empty string, which has sat in the file map since the first mod without a `common/` tree [#1452].
An `overrides` line with nothing after it is a single line with an empty relative path, not a census of zero: both sessions' mod-log keys carry the mod's name followed by nothing, 88 characters inside a 200-character capture limit [#1450/M/n=2].
Put together, a line with a path tail prints once per Lua state for each shadowed file, while an empty-tail line prints once per Lua state for every mod with no `common/` tree and marks no collision at all [#1049/M/n=3].
The two shapes are the loader's only visible signal about the map, and neither of them says which mod lost: a tailed line names the mod that took the path, and a mod whose file was overwritten prints nothing.
Reading the print therefore tells you that a collision happened and who won, and a reader who wants to know what was displaced has to compare the two trees themselves.

<a id="lua-load-order"></a>
### The Lua execution list

`LuaManager.LoadDirBase` builds the Lua execution list vanilla-first, sorted case-insensitively, then per mod the `common/` block and the version-dir block, each sorted case-insensitively [#0850/C/C-only].
`LoadDirBase` then walks that list through a hash set: a relative path already seen is skipped, and the survivor is resolved through `ZomboidFileSystem.getAbsolutePath` and run [#0851/C/C-only].
A doubled relative path therefore executes once, from the file the map holds, whichever tree of whichever mod put it there [#1313].

A mod file at a vanilla relative path replaces vanilla's body in vanilla's slot: the path is deduped at vanilla's position in the list while the file that executes is whatever the file map holds, so the replacement runs before every mod's own block rather than where the mod sits in `Mods=` [#0852/C/C-only].
`require` resolves against the same merged file map: there is no per-mod search path, and a `require` hits the one absolute path the map currently holds for that relative path [#0853/C/C-only].
Both readings are of the code, and no boot has exercised a vanilla-path replacement.
The two facts together make shadowing a Lua file a door and a trap at once: a mod that wants to change vanilla's behaviour early has a reliable way in, and two mods that both want the same file cannot compose, because the map is path-granular and the loser's whole file is gone rather than the part it disagreed about [#1176/C/C-only].
There is also no partial replacement to reach for: whatever entry the map holds is the entire body that executes at that path [#1176/C/C-only].

A mod's file-scope assignment to `ZomboidGlobals` lands because the mod tree executes inside `LoadDirBase` ahead of `Load()`, on the client through `GameWindow.init` and on a dedicated server through `GameServer.doMinimumInit`, while an assignment from an event handler, `OnGameStart`, `OnInitGlobalModData` or a bus command is inert — the one exception being `OnGameBoot` on the dedicated server, one instruction before `Load` [#1216/C/C-only].
That branch is read from the code and unmeasured: no run has assigned one of those globals and read the drain back.

<a id="script-dsl"></a>
### The script grammar

A script file is a nest of named blocks: a `module` block holding `item`, `craftRecipe` and the other script-type blocks, each of which holds `Key = Value` lines terminated by commas, with block comments stripped before the parse.
The module name is the first half of every name declared inside it, so an `item Apple` inside `module Base` is addressed everywhere else as `Base.Apple`, and a mod that declares its own module is declaring its own namespace with it.
A file may hold several modules and a module may be reopened in another file, which is what makes a redefinition possible at all.
One method parses every `Key = Value` line of an `item` block for every item type in the game, `Item.DoParam`, an if/else chain of 440 `equalsIgnoreCase` comparisons over 396 distinct keys, counted on this build [#0211/C/snapshot].
Script values parse as `Integer.parseInt` for an int, `Float.parseFloat` for a float, `Boolean.parseBoolean` or a case-insensitive match so that only the literal `true` is true for a bool, a semicolon `trim().split` for a list, and a bare `putfield` for a string [#0214].
A malformed value on a known key throws `InvalidParameterException` carrying the key and the item's name [#0213].
Which keys exist, what each one sets and how many blocks write it is [the item key reference](../facts/food-item-model.md#script-keys); this section owns the grammar those keys sit in.

The vanilla `Base.Apple` item block declares 17 keys, counted in the generated food script file and reproduced verbatim in the override probe's restatement [#1012].
A new item declared in the mod's own module collides with nothing and grows the pool by exactly the items it declares: the probe module read three foods with `module Base` unchanged at 722 [#1020/M/n=1].

The engine tolerates a brace-unbalanced script file: a block comment opened at one line and closed inside a later item body leaves the comment-stripped file at 17 opening against 18 closing braces, and the engine still loaded all 15 of the mod's item blocks [#1446/M/n=1].
That file is a workshop mod's dried-goods script, which carries 17 opening braces against 18 closing ones after comment stripping and whose 15 blocks answered a census of 14 Skittles foods at join, the live blocks minus one non-food item [#1673/M/n=1].
The tolerance is one file on one build, reproduced on a second run, and is a reading of what the engine does rather than a contract it offers.
A file that a hand-written parser and the engine both accept today is not a file that both will accept tomorrow, so a brace count is worth keeping even where nothing enforces it.

<a id="craft-recipe-grammar"></a>
### The `craftRecipe` block

A `craftRecipe` IO line is an `item` with a count or a `variable` range, then a bracketed type list, a `tags[…]` list, a `mapper:<name>` or a wildcard, then optional `mode:`, `flags[…]`, `mappers[…]` and `overlayMapper` tokens; a fluid sub-line is a signed `-fluid` with a count and either a fluid name or a `categories[…]` list, optionally `mode:mixture` [#0692].

```
item <N | variable[<min>:<max>]> [<Type;Type>] | tags[<t;t>] | mapper:<name> | [*]
     [mode:keep|destroy|mixture] [flags[…]] [mappers[…]] [overlayMapper]
-fluid <N> [<Fluid>] | categories[…] [mode:mixture]
```

A bracketed list splits on semicolons and an entry may carry a per-alternative count, a leading minus marks a fluid sub-line that the loader attaches to the input above it rather than adding to the input list, and an output `mapper:<name>` resolves to every key of that mapper except the literal `default`.
Above the IO lines a block may set the keys a mod is most likely to reach for: `time`, `Tags` and `category`, the `timedAction` it runs under, `xpAward` and `SkillRequired`, the learn gates `NeedToBeLearn`, `AutoLearnAll` and `AutoLearnAny`, the script-hook keys `OnCreate` and `OnTest`, plus `AllowBatchCraft`, `MetaRecipe`, `Tooltip`, `overlayStyle`, `recipeGroup` and `Icon` — a selection of the top-level keys rather than a census of them.
A block may also ship no `outputs` at all, or an empty one, and mutate an input through `OnCreate` instead of yielding an item, which is what the recipes that yield nothing do [#0686/C/snapshot].

An item mapper collapses a four-input, four-output family into one recipe block, and the engine's possible-result-items lookup resolved the mapped output slot to all four cured meats [#1438/M/n=1].
That is the grammar's one real compression: a family of inputs and a family of outputs paired by name, declared once, with the engine resolving the mapped slot at lookup time.
No legacy `recipe` block ships on this build while the loader is intact: the script type still registers the token and `Recipe.Load` still exists, and the live all-recipes list came back at size 0 [#0678/M/n=1].
What an input line costs a food and what an output carries away is [the recipe economics](../facts/cooking-and-recipes.md#uses), which rests on this grammar rather than restating it.

<a id="file-list"></a>
### The stored script path

The script file list is keyed on the lower-cased path relative to the mod's version directory, the same shape vanilla's own files take [#1045].
`ScriptManager.searchFolders` stores that lower-cased relative script path, and that stored string is what later orders the replay [#2009/C/C-only].
The stored key carries no mod component, which is why a mod's folder name and its stored script path cannot be separated by measurement.
Two things follow from the key being relative rather than absolute: a mod's file and vanilla's file can collide at all, because both are spelled from their own root down; and a mod's files sort against every other mod's by basename and sub-path alone, with nothing in the string to say which mod supplied them.
That single string is the input to the dedupe of the file walk and to the comparator that orders the replay, so a mod choosing a script filename is choosing both its collision risk and its position in the replay.

<a id="bucket-append"></a>
### A repeated name appends

When the loader already holds an item's name the parsed body is appended to the existing object's script-body list and no second script object is created [#1002].
`ScriptType.Item` carries `ResetExisting`, and `LoadScripts` sets its start index to 0 on a reload and 1 otherwise before calling `reset()` on every body whose index is at or above it, so on an initial load the reset runs before every body but the first [#1003].
`BaseScriptObject.reset()V` is a bare return and neither `Item` nor `GameEntityScript` overrides it, so the reset the loader calls before a repeated body does nothing at all [#1004].
The chain is real and inert: the flag is set, the call is made, and the method it resolves to has no body.
Every consequence of a repeated name comes from that combination — a list of bodies that grows, and a reset that clears nothing before each of them is replayed.
Nothing here is specific to items overriding items: the bucket is keyed on the script name, so the second body may come from any file, in any mod, in any tree.

<a id="per-key-merge"></a>
### The per-key merge

`Item.Load` parses the body and assigns each `key = value` element through `Item.DoParam`, and nothing clears a field the body does not name [#1005].
A repeated script name appends a body to the bucket rather than replacing it, and the reset the loader calls before every body but the first is a bare return, so the item parser assigns per key [#2007/C/C-only].
Redefining an item name merges fields across bodies in replay order with the last writer winning per key, so every key a later body omits keeps the value an earlier body gave it [#1006/M/n=1].

A full restatement of `Base.Apple` in `module Base` carrying `Calories = 400.0` reads `getCalories` 400 on the client and 400 on the server, against vanilla's 95.0 [#1008/M/n=1].
The keys a full restatement copies verbatim read their vanilla values identically on both sides: `getCarbohydrates` 25.13, `getLipids` 0.31, `getProteins` 0.47 and `getHungChange` -0.16 [#1009/M/n=1].
A redefinition replaces rather than adds: the food count of `module Base` stayed at 722 with a delta of 0 across three redefinition boots [#1010/M/n=3].

A partial `item Orange` block naming only `DisplayCategory`, `ItemType` and `Calories = 400.0` reads `getCalories` 400 on both sides [#1013/M/n=1].
The instance getters a partial block does not name stay at vanilla on both sides: `getCarbohydrates` 16.27, `getLipids` 0.30, `getProteins` 1.0 and `getHungChange` -0.12 [#1014/M/n=1].
The script keys a partial block does not name stay at vanilla on both sides: `DaysFresh` 6, `DaysTotallyRotten` 9, `HungerChange` -12 and `ThirstChange` -8 [#1015/M/n=1].
The instance of an item narrowed by a partial block keeps the vanilla shelf life the block never restated: `offAge` 6 and `offAgeMax` 9, read on the server only [#1016/M/one-side].

The practical shape of this is that a partial block is the cheap route into a vanilla item: restate the keys the mod owns and every key it omits keeps whatever upstream says, including whatever a later patch changes it to.
The same property is what makes a pass over many items robust for every key it does not declare and contested only on the keys two mods both declare.
It also means a partial block cannot remove a key: there is no route from a script body to an absent value, only to a different one.

The measured half of the merge is one item on one build with one key type, a float macro on a `base:food`, in one session against three mods written for it.
The arm that omits `ItemType` from a partial block, and a second mod's partial block landing against an already-populated default modData table, are both unrun — see [the walls](#walls).

<a id="sorted-replay"></a>
### The sorted replay

`ScriptManager.Load` pools vanilla's files and then every mod's `common/` and version dir in `Mods=` order as stored, sorts the vanilla and mod lists separately with a `template_`-first comparator that compares the stored path strings, and appends the mod list after vanilla's, so the sort and not `Mods=` decides the replay order [#1051].
One exception precedes the replay's path compare: `ScriptManager$38.compare` takes each side's basename and pre-sorts every `template_`-prefixed file ahead of every file that is not, returning -1 and +1 for that test alone [#1233/C/C-only].
The item pass controls that exception through its own filenames, by not naming one `template_*`.

In a boot whose `Mods=` named the watermelon probe first, `Base.Watermelon` read 999 on both sides, the body of the mod first in `Mods=` and last alphabetically [#1053/M/n=1].
With the same three bodies permuted so that the probe sat in the middle of `Mods=`, `Base.Watermelon` still read 999 on both sides, where 111 would have said first-in-`Mods=` wins and 777 `Mods=`-last wins [#1054/M/n=1].
Script bodies replay sorted by the stored script path, independent of `Mods=` position, with the last body winning per key, and `Mods=`-order-last-wins, first-in-`Mods=`-wins and alphabetical-first are all falsified [#1055/M/n=2].
Three rival replay orderings are therefore dead: `Mods=`-last, first-in-`Mods=` and alphabetical-first [#1232/M/n=2].
The rule rests on two permutations of the same three mod bodies, in which the winner held the first and second `Mods=` slots, plus a third session's independent kills; the sort key itself is read from the code, because no boot separates the mod id from the folder name, the stored script path or the `mod.info` display name.

The loader's own `loading` lines for each mod id walk `Mods=` order, which is a separate order from the body replay and is the reason the two are easy to confuse [#2001/M/n=3].
Two orders exist in one boot and only one of them decides a value: the mod list is walked in the order an operator wrote it, and the bodies are replayed in the order their file paths sort.
A reader watching the console sees the first and infers the second, which is exactly the inference the permutations above falsify.

What is safe to rely on today is the per-key half rather than the ordering half: whichever body lands last wins only the keys it names, so two mods collide on the intersection of the keys they both declare and nowhere else.
An operator cannot reorder that intersection by editing the mod list, and a mod author can shrink it by declaring fewer keys.

<a id="path-collisions"></a>
### Two mods at one relative path

Two mods shipping the same relative script path do not both load: one file wins and the other's blocks are never parsed [#1047/C/C-only].
The winner is the later of the two unconditional puts into the file map, and the loser's blocks are not merged, deferred or reported as a parse failure — they are simply never seen.
For a Lua file where only one mod sits at a given relative path the load-order question between the two dissolves: the file-map put is unconditional and only one mod in the corpus sits at that relative path, so its copy wins in both mod orders, and because the Lua load list runs vanilla's block first the surviving entry is vanilla's slot resolved through the file map, which means that mod's bytes execute before every mod file [#1368].
Order would matter only if a second mod shipped the same path, and none in the surveyed corpus does.
The two collisions are resolved by two different mechanisms and are worth keeping apart: two mods at one relative path is a file-map question, decided before a parser ever sees the content, while two mods declaring one script name in different files is a bucket question, decided by the replay.
The first loses a whole file silently; the second loses nothing and merges — see [the per-key merge](#per-key-merge).
The practical rule for either is the same: a mod-unique relative path makes the first question disappear and leaves only the second, which the grammar itself can narrow.

<a id="default-moddata"></a>
### The default modData arm

An unknown script key is neither dropped nor thrown: the fall-through writes it into the item's `defaultModData` as a `Double` when the value parses and as a `String` otherwise, so a dead key silently becomes mod data readable from Lua [#0212].
`Item.DoParam`'s default arm rawsets an unrecognised key into `Item.defaultModData` as a `java.lang.Double` when `Double.parseDouble` accepts the value and otherwise as the raw, untrimmed string [#1187/C/C-only].
An unrecognised key inside a vanilla `item` block becomes default modData on every instance: that default arm rawsets it into the table and `Item.InstanceItem` copies the table onto every instance, so a script-declared mod nutrient is readable from Lua off the item's modData [#1089].
`Item.InstanceItem` also passes a script `Tooltip` value to `InventoryItem.setTooltip`, whose first act is a rawset of `Tooltip` into the item's modData, so any script `Tooltip` line becomes an item-modData key on every side that instantiates the item [#1044].
A census of an item's modData that does not exclude that key will report vanilla as a finding.
The arm is a route and a hazard at once: it is the one way a script line can reach a Lua-readable per-item value, and it is also why a typo in a key name produces no error and no effect anyone will notice.
A key that lands there is on the item's default table rather than on the script object, so the value is read from an instance's modData and never from a macro getter.

<a id="identity"></a>
### What a redefinition does to identity

`Item.InitLoadPP` runs once per appended body, re-stamping `Item.fileName` so a redefined item reports the last mod's script file, and allocating a fresh net id into `netIdToItem` and `netItemToId` for the same `moduleDotType` [#1007/C/C-only].
The side effect is read from the code and unmeasured, which makes the re-stamped file name and the fresh net id the two properties of a redefined item that nothing here licenses relying on.
The merge leaves the item's identity in an odd place: the values are a composite of every body, while the file name records only the body that happened to land last, so an item's own account of where it came from names one of its authors and not the others.
The identity that survives a redefinition unchanged is the module-qualified name, which is the key the bucket is stored under and the key every lookup uses.

<a id="name-resolution"></a>
### A bare name against a qualified one

`ScriptManager`'s by-name script lookups answer to both the bare name and the `Base.`-qualified name [#0645/M/n=15].
A recipe lookup by name needs the module prefix once the name is a mod's own: the qualified name resolves while the bare name resolves against neither spelling the shipped lookup tries, because the script bucket lookup sends a dot-less name to the base module [#1455/M/n=1].
The two readings agree — the bare form works exactly as far as the base module reaches, and a mod that declares its own module is outside it.
The failure is quiet rather than loud: a bare name that belongs to another module resolves to nothing, so a caller gets an absent script rather than an error naming the module it should have asked for.
A tool that wants to find a modded name without knowing its module has to fall back on scanning the whole collection, which is what this library's own harness does.

<a id="per-side-load"></a>
### Script data loads per side

Both sides load the same script definitions from the same files and no packet carries one: the item packet read field by field carries instance state only, with no script key among the fields it applies [#0646/C/inference].
That half is read from the code rather than measured, and the no-packet claim is an inference from one packet's field list rather than a sweep of the whole protocol; the field list is the item packet's contract on [wire-packets.md](../facts/wire-packets.md#item-stats-packet).
A mod that changes a script key changes it on whichever side loaded the mod, with no runtime reconciliation, because definitions are load-time state [#0648/C/inference].

Script data is loaded per side and never synced, so the two sides' definitions of an item are two readings rather than one: reached through the script manager's item getter with the game's own find call as the fallback, the two sides agreed field for field on a mod item [#0919/M/n=1].
Item scripts load per side and never sync, so a script-declared value is identical on the client and the server for free [#1058/M/n=2].
A workshop mod's item script read on the server and on the client came back identical field for field — hunger change -60, thirst change 20, 53 days fresh, 60 days to rotten, cookable true, 300 minutes to cook and 900 to burn — differing only in which side answered [#1393/M/n=1].
Script data is owned by neither side and crosses no wire: both sides load it, so a script value is free on both sides, at the price of the checksum gate [#1243/M/n=1].
That gate is [the script checksum](mod-anatomy.md#checksum-gate) and is the whole price of the route.

The contrast worth carrying out of this section is between the two halves of a mod: what it writes in script is correct on both sides for nothing, and what it writes in Lua on an instance reaches the other side only through a packet.
A design that can express a value as a script key has bought agreement; a design that has to compute the value at runtime has bought a sync problem instead.

<a id="reload"></a>
### A script reload

A reload takes the other arm of the same loader: `LoadScripts` starts its reset at the first body rather than the second, so on a reload the reset runs before every body including the first, and for an item that call is the same bare return it is on an initial load.
The flags that would take another path on a reload, the reset-once-on-reload and pre-reload arms, are unread, and no reload has been driven in a running session.
Whether the merge survives one is therefore [an open row](#open), not a fact this page states either way.

## Walls and bounds
<a id="walls"></a>

The log lines that enumerate `common/` before the version dir come from `AdvancedAnimator.loadModMedia`'s media walk, not from the `activeFileMap` pass, so they corroborate the merge order and are never evidence about the map pass itself [#0834/C/C-only].
Two loader log lines are routinely misread: the `common/`-enumerated-first lines are the media walk rather than the `activeFileMap` pass, and an empty-tail `overrides` line means the mod has no `common/` rather than a collision, a client printing twice as many of them as there are mods because it runs two Lua states [#1217/M/n=1].
A malformed value on a known script key raises `InvalidParameterException` and aborts the load, and a line with no equals sign dies at the split's second element [#1188/C/C-only].
The per-key merge is measured on one item of one build and one key type, and the arm that omits `ItemType` from a partial block, together with a second mod's partial block landing against an already-populated default modData table, has never been run and is [an open question with a purpose-built probe behind it](../areas/open-questions.md#x15) [#1281/C/open].
Which string orders the replay is read from the code alone, because the mod id, the folder name, the stored script path and the `mod.info` display name sort identically in every boot this library ran, and the boot that would separate them is [the four-mod separator](../areas/open-questions.md#x19) [#1285/C/open].
The one-path-per-relative-path rule across two mods is a code reading: no session has shipped the same relative path from two different mods, for a script file or for a Lua file, and the sharpest arm — a mod file at a vanilla relative script path, which the same read predicts is dropped entirely — waits on [the collision probe](../areas/open-questions.md#x20) [#1286/C/open].
Whether the per-body net-id reallocation ever puts a stale id on the wire is unread, which leaves a redefined item's net id a property this page describes and does not license, and it waits on [the identity probe](../areas/open-questions.md#x27) [#1293/C/open].
Not covered: the other script types this same loader parses — entities, vehicles, fluids, animations, models and the `template_` files the comparator sorts first — the tokenizer that turns a file into blocks, the asset pipelines that read the same file map for textures and models, and what the loader does when a script file is added or removed while a session runs; this library read none of them.

## Open
<a id="open"></a>

- Whether the per-key merge survives a `reloadlua` or a script reload is unread — the reset runs before the first body too on a reload, still a no-op for an item, but the reset-once-on-reload and pre-reload flags take other paths this library did not read — settled by driving a reload in a running session and re-reading a merged item's keys [#1062/C/C-only/open].
- That a boot whose `Mods=` named the override probe before the eat-hook probe read `Base.Watermelon` at 111 on both sides, the body of the mod earlier in `Mods=`, is unverified: the reading rests on a restricted artifact key and is a reading rather than a rule, killing `Mods=`-last-wins and nothing else with four rival orderings surviving it; re-measure by the four-mod separator that ties each candidate sort key to a different body [#1052/M/n=1/unverified].
- That script and registry ids are lower-cased because the registries are case-insensitive is unverified: it was not re-verified this phase, and its measured neighbour is only the loader's `overrides` tail, which is a lower-cased relative path; re-measure by declaring one id in two cases and reading which spellings the script lookups answer to [#1117/C/C-only/unverified].
- Decision the rows force: whether the item pass ships one minimal `module Base` block per item or a full restatement of each, given that a partial block merges per key and that the body which lands last is decided by the stored script path [#1006/M/n=1, #1055/M/n=2].
- Decision the rows force: whether a mod nutrient is declared as an unrecognised key inside the vanilla `item` block or carried in Lua, given that the parser's default arm makes such a key default modData on every instance and that script data crosses no wire [#1089, #1058/M/n=2].
- Decision the rows force: whether the pass's script files take mod-unique basenames, given that the file map holds one absolute path per relative path and that no session has measured the two-mod collision [#1046, #1047/C/C-only].
- Decision the rows force: whether the pass declares any key whose value it computes rather than writes literally, given that a malformed value on a known key aborts the whole load [#1188/C/C-only].

## Worked examples

| shape | file:lines | what it shows |
|---|---|---|
| a full restatement of a vanilla block | `testing/experiments/TKX_ItemOverride/42.20/media/scripts/tkx_item_override.txt:3-22` | the vanilla `Apple` block copied verbatim into `module Base` with one macro changed — the route that costs every key |
| the minimal override block | `testing/experiments/TKX_ItemOverride/42.20/media/scripts/tkx_item_override.txt:24-29` | a partial `item Orange` naming three keys and nothing else, the body the per-key merge is read from |
| the same item name in a second file | `testing/experiments/TKX_ZWatermelon/42.20/media/scripts/tkx_zwatermelon.txt:3-24` | a second `item Watermelon` body, identical to the first apart from its `Calories`, so the replay winner is the only thing a reading can be about |
| the sort-key probe | `testing/experiments/TKX_ZWatermelon/42.20/mod.info:1-5` | a mod id built to sort last, against a script basename that sorts last as well — which is why this pair cannot separate the two |
| the merge reading | `testing/experiments/x121_overrides.py:644-656` | the instance-getter witness pair and the server-side instance read that discriminate the merge from a reset |
| the replay discriminator | `testing/experiments/x124_order.py:109-131` | every value the subject can come back as, and what each one would mean, written before the boot |
| the permutation that killed the rivals | `testing/experiments/x125_order2.py:122-142` | the same three bodies re-ordered, with the candidate table naming what each reading selects and what it kills |
| the `overrides` tail parser | `testing/experiments/x122_loader.py:355-368` | an empty tail kept as the empty string rather than dropped, which is what makes the empty-tail line countable instead of invisible |

## See also

- [`mod-anatomy.md`](mod-anatomy.md) — the file-level merge between a version dir and `common/`, the id chain, translations and the script checksum gate this page's per-side rule rests on.
- [`lua-platform.md`](lua-platform.md) — the Kahlua dialect a loaded file runs under, and the script hook keys an `item` block names.
- [`mp-model.md`](mp-model.md) — what a Lua edit to an instance must cross, once a script value is no longer enough.
- [`overview.md`](overview.md) — the two Lua states a client runs, which is why every per-state count doubles there.
- [`../facts/food-item-model.md`](../facts/food-item-model.md#script-keys) — the item key reference this grammar carries.
- [`../facts/cooking-and-recipes.md`](../facts/cooking-and-recipes.md#uses) — what a craft input costs, on top of the `craftRecipe` grammar here.
- [`../facts/other-mods/longtermpreservation.md`](../facts/other-mods/longtermpreservation.md#techniques) — the corpus mod that adds in its own module and pins shelf life in the script.
- [`../facts/other-mods/autocook.md`](../facts/other-mods/autocook.md#architecture) — the corpus mod whose shadowed files supply the measured `overrides` lines.
- [`../reference/experiments.md`](../reference/experiments.md) — the named experiments the walls above hand their open questions to.
