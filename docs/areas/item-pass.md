# Item pass
Verified against 42.20.4 (b0bbce05d5) · 2026-10-01 · scope: the nutrition-design reading of overriding vanilla foods — the routes into a vanilla item's nutrition, the minimal override block, which records a `module Base` pass covers and the pass's own risks; the merge, the replay and the path collisions are `platform/loader-and-scripts.md`, the keys are `facts/food-item-model.md`, what an eat does with a value is `facts/eating-pipeline.md`, and every count is `reference/datasets.md`.

## Rules
<a id="rules"></a>

- Restate only the keys the pass re-bases in a partial item block: every key the block omits keeps its vanilla value, which is what lets a pass over every record of `data/food-items.json` ship minimal blocks and leave icons, models, evolved recipes and spoilage tracking upstream — measured on one float macro of one food [#1017/M/n=1].
- Ship one `module Base` block per item: per-key last-wins makes the pass robust to the replay order for every key it does not touch and contested only on the keys two mods both declare [#1057/M/n=1].
- Do not derive body order from `Mods=`: bodies replay sorted by the stored script path, so a mod's position in `Mods=` decides nothing about which body wins a key [#1055/M/n=2].
- Keep `template_` out of a script file's basename: the replay comparator pre-sorts every `template_`-prefixed basename ahead of every other file before it compares paths at all [#1233/C/C-only].
- Give the pass's script files a mod-unique basename: two mods at one relative script path lose one file's blocks entirely — a code reading, since the across-two-mods arm is unmeasured [#1050/C/C-only].
- Spell a script value for the type its key parses as: an int, a float, a bool where only the literal `true` is true, a semicolon-split list or a bare string [#0214].
- Keep every value on a known key well formed: a malformed value raises `InvalidParameterException` and aborts the load, and a line with no equals sign dies on the split [#1188/C/C-only].
- Write every re-based value in the script's own units: the dataset carries hunger and thirst raw, as the script writes them, while an instance divides them by a hundred, and a drink row's nutrition is its fluid's per-litre figure rather than a key on the container's own block [#0323, #0626/C/snapshot, #1893, #2068/C/inference].
- Address a redefined item by its full type and never by net id or script file name: the per-body init runs once per appended body, re-stamping the file name and allocating a fresh net id [#1007/C/C-only].
- Ship byte-identical script files on both sides of a multiplayer session: the gate hashes file content with every CR byte dropped, so a mismatch is a disconnect rather than a silent degrade [#1182/C/C-only, #1231/C/C-only].
- Put item data in scripts and reach for a Lua field write only when the field is in `ItemStatsPacket` or the value may stay server-only: a script value is identical on both sides for free, while a Lua write to a live item never leaves the server [#1074/M/n=1].
- Change the eat path or the read-time getters, never the item, to make rot cost calories: an item's stored macros are a pure function of its script values and how much of it has been eaten — a reading of the aging write set rather than a measurement [#0255/C/inference].
- Declare a mod's own items in the mod's own module when the mod adds rather than rebalances: a new name collides with nothing and grows the pool by exactly what it declares [#1020/M/n=1].
- Read per-item macro values off an instance getter or out of the script text: the script object carries no macro getter, its four macro fields are private, and the dialect publishes methods rather than fields [#1011/M/n=1, #2732/M/n=1].
- Build a fresh instance through the `instanceItem` global to read a type's vanilla macros when no instance is at hand: the global reaches the item factory, which the exposer leaves out [#2679/C/C-only, #2680/C/C-only, #2741/C/inference].

## How it works

An item pass is a rebalance of vanilla foods shipped as script: one block per item, naming the vanilla item and the keys the rebalance owns.
Everything it rests on is a mechanism another page owns — the merge, the replay and the file map are the loader's, the keys are the item model's, and what an eat does with a value is the eating pipeline's — and this page is the reading of those mechanisms for one design.
It is in two parts: the smallest block that changes a key, and which records a pass over the base module reaches.
The pass's numbers themselves come from the design and the dataset rather than from here, and every per-food value is [the dataset](../reference/datasets.md).
The routes a mod can take into a vanilla food, script and Lua alike, are under [Options](#route-options), and the pass's own risks under [Walls and bounds](#walls).

<a id="minimal-block"></a>
### The minimal override block

The smallest block that changes one key is an `item` block inside `module Base` that names the vanilla item and restates only the keys the pass re-bases.
Every key the block omits keeps its vanilla value, so a pass over every item record of the food dataset ([the counts](../reference/datasets.md#counts)) can ship minimal blocks and leave icons, models, evolved recipes and spoilage tracking at whatever upstream says [#1017/M/n=1].
An omitted key survives because the loader merges bodies per key ([#2007/C/C-only, #1006/M/n=1], [loader-and-scripts.md#per-key-merge](../platform/loader-and-scripts.md#per-key-merge)).
The merge is measured on one food and one float macro, so every other key type a block might name — a list, a string, a bool — rests on the code reading alone ([#1006/M/n=1]).

The measured minimal block is the loader page's partial `item Orange`: `DisplayCategory`, `ItemType` and one re-based macro, with every instance getter and script key it does not name reading vanilla on both sides ([#1013/M/n=1], [#1014/M/n=1], [#1015/M/n=1]).
`ItemType` can go: the same partial `item Orange` with `ItemType` omitted, booted as the only body after vanilla's, still merged into a food on both sides, with the base module's food count unmoved ([#1018/M/n=1], [loader-and-scripts.md#per-key-merge](../platform/loader-and-scripts.md#per-key-merge)).
So the smallest block a pass can ship on today's evidence is the item header, `DisplayCategory` and the keys it re-bases; whether `DisplayCategory` can go as well is unmeasured, because the probe kept it, and sits under [Open](#open) [#3136/C/open].

A whole re-declaration is not needed, and it is not free either.
A full restatement of a vanilla block works: the key it changes reads the new value and the keys it copied read their vanilla values on both sides ([#1008/M/n=1], [#1009/M/n=1]).
A redefinition replaces rather than adds, so neither shape grows the base module's food pool ([#1010/M/n=3]).
What a full restatement costs is every key it copies: a copied key is pinned at the value the pass copied, so an upstream patch to it no longer reaches the item, and it is contested with every other mod that declares the same key on the same item.
The pin holds against vanilla too, because a mod's body always replays after vanilla's own ([#1051], [loader-and-scripts.md#sorted-replay](../platform/loader-and-scripts.md#sorted-replay)).
A partial block pays none of that: it names what the rebalance owns and leaves every other key to whoever owns it upstream, including whatever a later patch changes it to.
The pin is a property of naming a key, not of changing it, so a generated block that restates a key at the value vanilla already gives it changes nothing today and still holds that key against every later patch.
Two blocks for one item inside the pass's own files are two bodies as well, so a pass split into one file per concern composes per key, the later body in stored-path order winning any key both name ([#1006/M/n=1], [#1055/M/n=2]).
Vanilla uses the same idiom on itself, its own scripts redefining some of their own item names, every one of them in the base module ([#1440/C/snapshot]).

A block changes a key's value and never removes one.
A pass can therefore add a key vanilla left out, `CustomWeight` for instance, and has no way to take one away ([#1005], [loader-and-scripts.md#per-key-merge](../platform/loader-and-scripts.md#per-key-merge)).
That makes absence a value of its own: an item that writes no shelf-life key reads back the never-ages sentinel rather than a zero ([#0619/M/n=1]).
A block that writes a zero where vanilla wrote nothing can therefore change the item rather than restate it.

Writing the block is where a pass fails quietly or loudly.
A misspelled key fails quietly: the parser's default arm writes an unrecognised key into the item's default modData and re-bases nothing ([#0212], [#1187/C/C-only], [loader-and-scripts.md#default-moddata](../platform/loader-and-scripts.md#default-moddata)).
A malformed value on a known key fails loudly: it raises and aborts the load, so one bad value in one block is enough to stop it ([#1188/C/C-only]).
Each key parses as its own type, and the item model's key table says which keys are ints, floats, bools, lists and strings ([#0214], [#0215/C/snapshot], [food-item-model.md#script-keys](../facts/food-item-model.md#script-keys)).
A misspelled item name fails in a third way: the append arm is taken only when the loader already holds the name, so a block whose name matches nothing declares a new item from the keys it names instead of overriding one ([#1002], [#1020/M/n=1]).
Because a redefinition replaces rather than adds, a pass whose every block hits a held name leaves the base module's food count where vanilla has it, and any growth names a block that declares an item instead of overriding one ([#1010/M/n=3]).
The same arm makes the pass fragile across game updates in one direction: a block for an item a later patch renames or removes stops being an override and starts declaring a partial item of its own ([#1002]).

Against another mod that names the same item, the block wins only the keys it names and only when its body replays last, which the sort decides and `Mods=` does not ([#1055/M/n=2], [loader-and-scripts.md#sorted-replay](../platform/loader-and-scripts.md#sorted-replay)).
The jar names the stored script path as the string that sorts, and that path is spelled by the pass's own file names, but no boot has separated it from the mod id, the folder name or the display name ([#1051], [#1056/C/C-only/open]).
The intersection of two mods' keys on one item is the whole of their conflict, so the fewer keys the pass declares, the smaller the surface another rebalance can collide with.

Which keys the block names decides what moves downstream, and the keys are not equally coupled.
The four macros are the least coupled: `Eat` reads them as bare fields with no state modifier and adds each, times the eaten fraction, to the store ([#0036/M/one-fixture], [#0018/M/one-fixture]).
A food's raw and cooked forms share one set of macros, because cooking leaves stored nutrition untouched and burning is the one nutrition modifier on the eat path ([#0277/M/n=1], [#0019/M/one-fixture]).
A pass therefore sets one number per macro per item, not one per state.
`HungerChange` is the most coupled key a pass can name.
It is the fraction a non-custom-weight food's displayed weight derives from ([#1214/C/C-only]), the unit a recipe input is charged in ([#0701/M/n=3]), the gate on which partial portions the eat menu offers ([#0079]) and the full-portion value the eat fraction is rescaled against ([#0080]).
It also sets the payload of the rot sickness roll ([#0052]) and the magnitude the cancel guard tests ([#0112], [mp-model.md#ownership](../platform/mp-model.md#ownership)).
A pass that re-bases hunger moves weight, recipe costs, the portion menu, the rot roll and the cancel guard with it, where a pass that re-bases only the macros moves intake alone.
`ThirstChange` runs a ladder of its own, in the opposite precedence to hunger's, and rot leaves it alone ([#0033/M/one-fixture], [#0035/M/one-fixture], [eating-pipeline.md#modifiers](../facts/eating-pipeline.md#modifiers)).
A cooked food's thirst change also reaches a client halved once per server-to-client hop, a vanilla defect that any client-side reader of a re-based value inherits ([#1147/M/n=1]).
The shelf-life keys belong to spoilage rather than to nutrition, and a block that leaves them out keeps vanilla's rot window on the instance, which is the upstream spoilage tracking the minimal block protects ([#1016/M/one-side], [spoilage.md#formula](../facts/spoilage.md#formula)).
Whether a re-based food then sets `CustomWeight = true` is a decision the item model carries ([food-item-model.md#open](../facts/food-item-model.md#open)).

Every value the block carries is in script units, and an instance is not: `Item.InstanceItem` divides the script's hunger, thirst and endurance keys by a hundred and stores the four macros as written ([#0011/M/one-fixture], [eating-pipeline.md#script-scale](../facts/eating-pipeline.md#script-scale)).
A pass computed from instance reads has to undo that division before it writes, while one computed from the dataset writes the dataset's figures as they stand, which [the unit walls](#walls) spell out.

Reading a re-based value back needs an instance: the script object answers no macro getter on either side, so only an instance getter says whether a block took ([#1011/M/n=1], [lua-platform.md#java-members](../platform/lua-platform.md#java-members)).
The same holds for the vanilla figure a pass is computed against: `getScriptItem()` reaches no macro, and a fresh instance made through the `instanceItem` global reads all four ([#2679/C/C-only, #2680/C/C-only], [food-item-model.md#script-keys](../facts/food-item-model.md#script-keys)).
A pass can check itself with a handful of reads, each resting on a row above.
The load finishing at all says every value on a known key parsed, because one malformed value aborts it ([#1188/C/C-only]).
The base module's food count standing where vanilla left it says every block hit a held name ([#1010/M/n=3]).
An instance getter read on each side says the re-based value took, and the same getter on a key the block left out says the rest stayed upstream ([#1014/M/n=1]).
None of those sees a misspelled key, which lands in default modData without a sound, so only a census of a re-based item's modData against a vanilla control would, excluding the custom-name key a deserialised copy carries and the tooltip key a block's own `Tooltip` line writes ([#0212], [#1415/M/n=1], [#1044]).
Nothing about the block costs anything at run time, because both sides load it and no packet carries it, at the one price of the script checksum gate ([#1243/M/n=1], [mod-anatomy.md#checksum-gate](../platform/mod-anatomy.md#checksum-gate)).

<a id="scope"></a>
### What a `module Base` pass covers

A `module Base` pass reaches the base module's food items and, once drainables and fluid containers are counted, every record of the food dataset; the figures are the dataset page's ([#1228/M/n=1], [datasets.md#counts](../reference/datasets.md#counts)).
Those records are a scan of one build, and the dataset page names the scan each count rests on, so a pass generated from it reaches a later build's new foods only after a re-scan.
Reaching a record is not the same as re-basing it, because the records differ in where their nutrition lives.
Which bucket a record falls in is the dataset's kind rule ([datasets.md#kinds](../reference/datasets.md#kinds)), and the pass meets the three item kinds differently.

A food record carries its nutrition as its own script keys, which is the case the minimal block is built for.
Not every one does: a share of the dataset's rows name no nutrition source at all, foods among them, and a block for such an item adds macros where vanilla wrote none rather than re-basing any ([#0622/C/snapshot], [datasets.md#columns](../reference/datasets.md#columns)).

A drainable record is an `item` block parsed by the same method as a food's ([#0211/C/snapshot]).
A block naming one takes the same per-key path, though the merge is measured on a food alone ([#1180/M/n=1]).
Almost none of them carries a nutrition key to re-base, and the few calorie lines among them write zero ([#0612/C/snapshot], [datasets.md#kinds](../reference/datasets.md#kinds)).

The fluid-container records are not food blocks at all: the kind takes every item that owns a fluid-container component, in item files well beyond the food script, clothing and weapons among them ([#0613/C/snapshot]).
A fluid container carries no nutrition key of its own: its record's nutrition columns are joined from the first fluid it lists ([#0626/C/snapshot]).
The live game agrees, a container's instance answering none of the food nutrition getters, so a drink's nutrition is reachable only through its fluid ([#0604/M/n=2]).
A fluid's figures are per litre, and the container multiplies them by what it holds ([#0630], [eating-pipeline.md#fluid-path](../facts/eating-pipeline.md#fluid-path)).
Re-basing a drink is therefore a question about `fluid` blocks rather than `item` blocks, and every merge reading this page rests on is a reading of `item` blocks.
The loader page names fluids among the script types the library never read ([loader-and-scripts.md#walls](../platform/loader-and-scripts.md#walls)), so whether a repeated `fluid` block merges per key the way an `item` block does is outside the library, and a pass that means to reach drinks starts there.

Foods a mod declares in its own module are outside the pass.
A `module Base` item pass does not touch foods a mod declares in its own module, so on a server running both, `LongTermPreservation4220`'s 14 `module Skittles` foods keep their upstream numbers while vanilla's are re-based [#1030/M/n=1].
That is the normal shape of a content mod rather than an exception: a new item in the mod's own module collides with nothing and grows the pool by exactly what it declares ([#1020/M/n=1], [#1440/C/snapshot]).
The two sets still meet: some of that mod's foods feed vanilla evolved recipes and some vanilla items come out of its recipes, so a re-based vanilla ingredient flows into its dishes while its own foods stay where their author left them ([#1461/C/snapshot], [longtermpreservation.md#compat](../facts/other-mods/longtermpreservation.md#compat)).
The display-name cost the route table gives a new item is the client's; a dedicated server resolves no mod item's display name even with the translation file shipped ([#1167/M/n=1]).

Reaching such a food means a block in that mod's module, and the append arm that makes a block an override is taken only when the loader already holds the name ([#1002], [loader-and-scripts.md#bucket-append](../platform/loader-and-scripts.md#bucket-append)).
A block naming another mod's food is therefore an override only while that mod is loaded; without it, the same block declares a new item from nothing but the keys it names, a reading of the append arm that no run has exercised.
It also wins only the keys it names, and only if its body replays after that mod's own ([#1055/M/n=2]).

Recipe blocks are outside the pass too, and the numbers move without them.
A crafted output carries its own item's script macros, so re-basing an output's block re-bases what the craft yields with no recipe block touched ([#0708], [cooking-and-recipes.md#uses](../facts/cooking-and-recipes.md#uses)).
The exception is a split: an input flagged to pass its food on gives every output a share of the consumed instance's own macros, whatever the output's block says ([#0706/C/snapshot]).
An evolved dish is summed from its ingredients' macros at build time, and each ingredient's contribution is asked in hunger and clamped to the ingredient's own, so a re-based ingredient changes both what a dish gains and how much of the ingredient it takes ([#0283], [cooking-and-recipes.md#evolved](../facts/cooking-and-recipes.md#evolved)).
Some vanilla ingredient keys already ask for more hunger than their ingredient carries and sit on that clamp, so a pass that lowers an ingredient's hunger can move more of them onto it ([#0289/C/snapshot]).
A food whose script hides the eat option reaches a player only through what is made from it, so its own macros travel only through a recipe that splits it, while an ordinary output carries its own block's numbers instead ([#0215/C/snapshot], [#0706/C/snapshot], [#0708]).
A dish built before the pass loaded is a separate question this library never read, and it is named under [Walls and bounds](#walls).

## Options

<a id="route-options"></a>
### The routes into a vanilla food

A mod has more than one way into a vanilla item's numbers, and the ways differ in when the number is set and whether it has to cross the wire.
The inventory below is the route list the library measured, and the options table after it reads the routes that reach a vanilla item's own numbers.

A mod has five routes into a vanilla item's nutrition — a full restatement of the vanilla block in `module Base`, a partial block in `module Base`, a new item in the mod's own module, Lua hooks on the instance, and item modData with `syncItemFields()` — and the three script routes carry no sync cost while the two Lua routes do; the route inventory is dated 2026-09-11 [#1001/M/n=1].

| # | Route | What it does |
|---|---|---|
| R1 | **Full restatement** of a vanilla block in `module Base` | every script key of that item is re-declared; the item record count does not change |
| R2 | **Partial block** in `module Base` | only the named keys change; every omitted key stays at vanilla |
| R3 | **New item in the mod's own module** | no collision possible; costs the display name unless the mod ships `ItemName.json` |
| R4 | **Lua hooks on the instance** — `OnEat`, a wrapper of `ISEatFoodAction:complete`, `OnCooked` | per-instance edits at eat/cook time, bounded by what `ItemStatsPacket` carries |
| R5 | **Item modData** + `syncItemFields()` | arbitrary new fields (a custom nutrient) on one instance |

The script routes are free on both sides because item scripts load per side and never sync, so a script value is identical on the client and the server without a packet ([#1124/M/n=1]).
The Lua routes are per instance: the eat completes on the server, which is where a hook's intake numbers have to land ([#0110], [mp-model.md#ownership](../platform/mp-model.md#ownership)), and whatever a hook writes to an item reaches a client only through the item packet's fields ([#1144/M/n=1], [wire-packets.md#item-stats-packet](../facts/wire-packets.md#item-stats-packet)).
Item modData is the route for a field vanilla does not have rather than for a vanilla number: it carries a mod value beside the item's own macros, and it moves between the sides wholesale ([#1126/M/one-side]).
`OnEat` and `OnCooked` reach an item through a script key, one string per item with the last body winning, so a pass that attaches a hook through the key replaces the hook on every vanilla block that already names one ([#0215/C/snapshot], [#1006/M/n=1]).
Correcting from `OnEat` writes every value twice, once by vanilla and once by the correction, in a handler that runs on both sides ([#1130/M/n=1]).
The server-side wrapper sees the item before `Eat` touches it, and it can keep vanilla's numbers from landing only by skipping the original ([#1129/M/n=1]).

One design question only the Lua routes can answer is rot.
Aging never writes an item's hunger or macro fields ([#0254/M/n=1], [spoilage.md#formula](../facts/spoilage.md#formula)).
A mod that wants rot to cost calories has to change the eat path or the read-time getters, because an item's stored macros are a pure function of its script values and how much of it has been eaten, a consequence reasoned from the write set rather than measured [#0255/C/inference].
No script block, full or partial, can express that, and the hook routes are where it would live ([eat-and-cook-hooks.md](eat-and-cook-hooks.md)).
The new-item route of the inventory is the pass's boundary rather than one of its options, and it is read under [What a `module Base` pass covers](#scope).
The table below gives each of the other four its cost and the wall it hits, in the wall map's row order.

| option | what it costs | which wall it hits | tags |
|---|---|---|---|
| item modData on each instance, pushed with `syncItemFields()` | a Lua write on every instance of every item it covers and a sync call behind each write; it carries a new field beside the vanilla numbers rather than re-basing them | the table moves wholesale, the receiver wiping its copy before it takes the sender's keys, and only the client-to-server direction is measured | [#1126/M/one-side], [#1001/M/n=1] |
| an eat or cook Lua hook on the instance — `OnEat`, a server-side wrapper of `ISEatFoodAction.complete`, `OnCooked` | a hook that runs on every eat or cook of every item it covers, a second write of numbers vanilla has already written when it corrects after the fact, and a sync cost on every item write | intercepting before `Eat` needs the server-side wrapper, `OnEat` corrects only after every stat and nutrient write, whatever a hook writes reaches a client only through the item packet's field list, and the cook pipeline that calls `OnCooked` is read from the code, never driven end to end | [#1129/M/n=1], [#1130/M/n=1], [#1144/M/n=1], [#1154/M/n=1], [#1001/M/n=1] |
| a `module Base` re-declaration restating every key of the vanilla block | one block per item and nothing at run time; every key it copies is pinned at the copied value, so an upstream patch to that key no longer reaches the item, and every key is contested with any other mod that declares it | the same-relative-path drop, the per-key merge under a redefinition that replaces rather than adds, byte-identical script files on both sides, the replay order on every key another mod also declares, and the identity re-stamp on every appended body | [#1175/C/C-only], [#1180/M/n=1], [#1182/C/C-only], [#1183/M/n=2], [#1184/C/C-only], [#1001/M/n=1] |
| a per-item override block naming only the keys the pass re-bases | one block per item and nothing at run time; every key it omits follows upstream, a later patch included, and it contests only the keys another mod also declares | the same-relative-path drop, the per-key merge under a redefinition that replaces rather than adds, the workaround of one minimal block per item across every food, byte-identical script files on both sides, the replay order on a key two mods both declare, and the identity re-stamp on every appended body | [#1175/C/C-only], [#1180/M/n=1], [#1181/M/n=1], [#1182/C/C-only], [#1183/M/n=2], [#1184/C/C-only], [#1001/M/n=1] |

Which route carries each value the pass changes — a script block both sides load for free, a per-instance modData field, or a hook that rewrites the numbers where `Eat` runs?

## Walls and bounds
<a id="walls"></a>

A mod can run the per-key merge across every `base:food` item only with a workaround: one minimal `module Base` block per item, with every untouched key left at whatever upstream says, including whatever a later patch changes it to [#1181/M/n=1].
The merge under it is measured on one item for one float macro, and a redefinition replaces rather than adds [#1180/M/n=1].
List, string and bool keys, and a block that adds a key vanilla left absent, are code readings under that merge rather than measurements ([#1006/M/n=1]).
No block can remove a key vanilla wrote, only change its value, so a rebalance that needs a key absent has no script route to it ([#1005]).
The replay order is the pass's to live with rather than to set: bodies replay sorted by the stored script path with the last winning per key ([#1183/M/n=2]), so one block per item keeps the pass robust to the replay order for every key it does not touch and contested only on the keys two mods both declare [#1057/M/n=1].
Two mods at one relative script path lose one file's blocks entirely, so the pass's script files take a mod-unique basename — a code reading, the across-two-mods arm unmeasured ([#1175/C/C-only], [#1050/C/C-only], [loader-and-scripts.md#path-collisions](../platform/loader-and-scripts.md#path-collisions)).
A redefinition does not leave the item's identity alone: every appended body re-stamps the item's script file name and allocates a fresh net id, and whether a stale id ever reaches the wire is unread ([#1184/C/C-only], [loader-and-scripts.md#identity](../platform/loader-and-scripts.md#identity)).
Every script file the pass ships must be byte-identical on both sides, because the checksum gate hashes content and a mismatch disconnects: a client whose copy of one script file differed by one byte was disconnected within a second of the server's check, while a copy differing only in line endings joined ([#1182/C/C-only], [#1282/M/n=1], [#3138/M/n=1], [mod-anatomy.md#checksum-gate](../platform/mod-anatomy.md#checksum-gate)).
The approved modlist offers no vanilla food override to learn from, so the item-pass mechanism a nutrition overhaul needs has no local precedent and the nearest evidence is on the Workshop [#1674/C/snapshot].
At the 2026-09-10 17:47 corpus sweep, across the nine `script_nutrition` mods of the 230-mod inventory there is exactly one name collision against the 5 092 distinct `module Base` item names vanilla declares, `Horse` redefining `Base.Rope`; seven of the nine declare `module Base` and only two define an item under it, so a pass over every record of the food dataset ([the counts](../reference/datasets.md#counts)) has no shipped example to imitate [#1019/C/snapshot].
The corpus drifts under Steam, so that count holds for its sweep; the collision census behind it is the catalog's and the vanilla name count the dataset page's ([#1229/C/snapshot], [#1572/C/snapshot], [catalog.md#corpus-facts](../facts/other-mods/catalog.md#corpus-facts)).
The dataset stores hunger and thirst in script units on every row, so its figures go into a block as they stand while an instance read has to be scaled back up before it goes in ([#1893], [#0011/M/one-fixture], [datasets.md#columns](../reference/datasets.md#columns)).
A drink row's nutrition columns are its fluid's per-litre figures joined onto the container rather than keys on the container's block, so a pass that reads a drink row as an item's own values writes the wrong unit onto the wrong block ([#1881], [#0626/C/snapshot]).
A `fluid` block has no default arm: a mod key written into one is logged as an error, throws when `Core.debug` is set and is stored nowhere, so a drink's fluid has no script route for a value of the mod's own ([#2682/C/C-only], [food-item-model.md#fluid-blocks](../facts/food-item-model.md#fluid-blocks)).
An empty cell is an absent key and never a zero, and an absent key takes the engine's own default, so a generator that fills blanks with zeros changes items it meant to restate ([#0618], [#0619/M/n=1]).
Rewriting `HungerChange` is not weight-neutral: a non-custom-weight food's displayed weight derives from its remaining hunger fraction, and `CustomWeight = true` opts out ([#1214/C/C-only], [food-item-model.md#state-axes](../facts/food-item-model.md#state-axes)).
Opting out is not free for an item whose display name does not resolve: the flag routes the weight getter through the display-name guard, and a dedicated server resolves no mod item's display name, translation file or not ([#1443], [#1167/M/n=1]).
An item whose display name does not resolve reads an unmodded weight of zero, and the item packet fills the wire's weight field from that getter, so a nameless item ships a zero weight to every client ([#1166/C/C-only]).
A re-based hunger value can land under the cancel guard, and a cancelled eat of such an item applies nothing at all by the code, an arm no run has exercised ([#0112], [#1299/C/open], [open-questions.md#x33](open-questions.md#x33)).
The guard tests the state-modified getter, so a value above it fresh can fall under it once the ladder divides it for staleness, rot or burning ([#0003]).
A pass that names `OnEat` or `OnCooked` on a vanilla block replaces the hook vanilla gave that block, the home-canning cook hook among them ([#0312/C/snapshot], [#1006/M/n=1]).
The minimal block's `ItemType`-omitted arm and a second mod's partial block landing on an already-populated default modData table are each one boot of one item: the later body's string replaced the earlier one's, and the two mods sorted the same way under every candidate sort key ([#1018/M/n=1], [#1281/M/n=1], [loader-and-scripts.md#default-moddata](../platform/loader-and-scripts.md#default-moddata)).
Foods declared in a mod's own module sit outside a `module Base` pass, so a server running both carries two sets of numbers side by side ([#1030/M/n=1]).
Not covered: a script reload in a running session, the `fluid` blocks a drink's nutrition lives in, what a re-based block does to instances and dishes already in a save, the translation of a re-based item's name, and any single-player session — every reading here is of `item` blocks loaded once at boot on the dedicated-server path.

## Open
<a id="open"></a>

- Whether a partial block that omits `DisplayCategory` as well as `ItemType` still merges into a food — settled by the same partial block with both keys omitted, reading the base-module food count and the instance getters on both sides [#3136/C/open].
- Which string orders the replay — mod id, folder name, stored script path or display name — the jar naming the stored path and no boot separating the four — settled by four sort mods, each built to win under exactly one candidate key; -> X19 ([#1285/C/open], [#1056/C/C-only/open], [#0886/M/n=2/open], [open-questions.md#x19](open-questions.md#x19)).
- Whether two mods at one relative path both load, for a script file and for a Lua file, and whether a mod file at a vanilla relative script path is dropped entirely — settled by two mods shipping the same relative paths with different content and reading which item and which global survive, plus a boot that ships a mod file at a vanilla relative script path; -> X20 ([#1286/C/open], [open-questions.md#x20](open-questions.md#x20)).
- Whether the fresh net id each appended body allocates ever puts a stale id on the wire — settled by reading a multiply-redefined item's `getID` and full type on both sides, where the two sides agreeing bounds the risk and disagreeing is the finding; -> X27 ([#1293/C/open], [#1063/C/C-only/open], [open-questions.md#x27](open-questions.md#x27)).
- Whether a cancelled eat of an item whose state-modified hunger sits at or under the guard really applies nothing at all — settled by a completed eat, a cancelled eat of a normal item and a cancelled eat of an item driven under the guard, each read on the server; -> X33 ([#1299/C/open], [open-questions.md#x33](open-questions.md#x33)).
- Whether a vanilla food absent from the item-name table trips the display-name weight guard the way a mod item does is unverified: its one reading rests on a restricted artifact key, and its owner carries the re-measure ([#1427/M/n=1/unverified], [food-item-model.md#open](../facts/food-item-model.md#open)).
- Decision the rows force: whether the pass reaches foods other mods declare in their own modules or leaves them on upstream numbers — a `module Base` pass does not touch them, and a block naming one is an override only while that mod loads ([#1030/M/n=1], [#1002]).
- Decision the rows force: whether the pass re-bases drinks, whose nutrition lives on a fluid, per litre, rather than on any key of the container's own block ([#0626/C/snapshot], [#0604/M/n=2]).
- Decision the rows force: whether the pass names `HungerChange` at all or re-bases the macros alone — hunger drives weight, recipe cost, the portion menu and the cancel guard, where the macros move intake alone ([#1214/C/C-only], [#0701/M/n=3], [#0036/M/one-fixture]).
- Decision the rows force: which route carries each value the pass changes — a script block both sides load for free, or a per-instance Lua write that has to cross the wire ([#1001/M/n=1]).

## Worked examples

| shape | file:lines | what it shows |
|---|---|---|
| the minimal override block | `testing/experiments/TKX_ItemOverride/42.20/media/scripts/tkx_item_override.txt:24-29` | a partial `item Orange` in `module Base` naming the two header keys and one macro — the shape a pass ships once per item |
| a full restatement | `testing/experiments/TKX_ItemOverride/42.20/media/scripts/tkx_item_override.txt:3-22` | the vanilla `Apple` block copied into `module Base` with one macro changed — every key pinned at the copied value |
| a food in the mod's own module | `testing/experiments/TKX_ItemOverride/42.20/media/scripts/tkx_item_override.txt:55-71` | `item FibreBar` in `module TKX` — the route that adds rather than overrides, and the kind of record a `module Base` pass never reaches |

## See also

- [`../platform/loader-and-scripts.md`](../platform/loader-and-scripts.md#per-key-merge) — the per-key merge, the sorted replay, the file map and the identity re-stamp every reading here rests on.
- [`../facts/food-item-model.md`](../facts/food-item-model.md#script-keys) — the keys a block can name, what the loader does with each, and the weight arms a hunger rewrite moves.
- [`../facts/eating-pipeline.md`](../facts/eating-pipeline.md#modifiers) — what an eat does with a re-based value, and the scale between a script and an instance.
- [`../facts/cooking-and-recipes.md`](../facts/cooking-and-recipes.md#evolved) — how a re-based ingredient reaches a dish and a re-based hunger value a recipe's cost.
- [`../facts/other-mods/longtermpreservation.md`](../facts/other-mods/longtermpreservation.md#compat) — the corpus mod whose own-module foods sit outside the pass.
- [`../platform/mod-anatomy.md`](../platform/mod-anatomy.md#checksum-gate) — the script checksum gate every shipped block pays.
- [`../reference/datasets.md`](../reference/datasets.md#counts) — every count this page links, and the column authority for the units.
- [`../reference/wall-map.md`](../reference/wall-map.md) — the verdict rows the walls cite by id.
- [`eat-and-cook-hooks.md`](eat-and-cook-hooks.md) — the hook routes in full, where a rot cost or an intake correction would live.
- [`new-nutrients.md`](new-nutrients.md) — where a mod nutrient beside the vanilla numbers can live.
- [`open-questions.md`](open-questions.md) — the experiments that settle this page's open rows.
