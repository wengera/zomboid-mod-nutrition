# Item pass
Verified against 42.20.4 (b0bbce05d5) · 2026-10-06 · scope: the nutrition-design reading of overriding vanilla foods — the routes into a vanilla item's nutrition, the minimal override block, which records a `module Base` pass covers, what the pass's pipeline rests on in the game and the pass's own risks; the merge, the replay and the path collisions are `platform/loader-and-scripts.md`, the keys are `facts/food-item-model.md`, what an eat does with a value is `facts/eating-pipeline.md`, and every count is `reference/datasets.md`.

## Rules
<a id="rules"></a>

- Do not derive body order from `Mods=`: bodies replay sorted by the stored script path, so a mod's position in `Mods=` decides nothing about which body wins a key [#1055/M/n=2].
- Restate only the keys the pass re-bases in a partial item block: every key the block omits keeps its vanilla value, which is what lets a pass over every record of `data/food-items.json` ship minimal blocks and leave icons, models, evolved recipes and spoilage tracking upstream — measured on one float macro of one food [#1017/M/n=1].
- Ship one `module Base` block per item: per-key last-wins makes the pass robust to the replay order for every key it does not touch and contested only on the keys two mods both declare [#1057/M/n=1].
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
- Ship each block in the measured shape, `DisplayCategory` and the keys the pass re-bases with `ItemType` omitted: a partial block without `ItemType` still merged into the vanilla food on both sides with every key it left out at vanilla, and a whole pass of such blocks declared no item; whether `DisplayCategory` can go as well is unmeasured [#3153/C/inference, #1018/M/n=1, #1013/M/n=1, #1014/M/n=1, #1015/M/n=1, #3141/M/n=1, #3136/C/open].
- Re-base the four macros only and keep the vector's macros equal to the block's values: the block names `Calories`, `Carbohydrates`, `Proteins` and `Lipids` and leaves `HungerChange` and `ThirstChange` to the script, each re-based getter read the float32 of the block's two-decimal value on the server, the client's copy and a client-local spawn, and an eat landed the table's vector beside the item's own live macros [#3154/C/inference, #3143/M/n=2, #3145/M/n=1, #3148/M/n=1].
- Treat an absent nutrient as unknown in the data and as zero in the shipped table, never as a measured zero in the data: an absent source value is `null` and a written zero is `0`, and the table carries 0 for a key with no value, which an eaten Apple landed as 0 on iodine, null in its record, beside six keys its FDC entry wrote as 0 and a phytate 0 placed by the zero:fruit family judgement [#3155/C/inference, #3585/C/snapshot, #0618, #3145/M/n=1].
- Take the portion from the game's own macros where they agree with the food's Atwater value, from an FDC serving only where the game's energy is unusable, and never from `Weight`: the mapping's portion sources read `vanilla_implied` on 78 records, `fdc_portion` on 66 and `judgement` on 425, the kcal-implied mass being the judgement where the game's energy stands [#3586/C/inference, #3581/C/snapshot].
- Keep a drink's nutrition on its fluid, per litre, in the Lua table and never on the container's block: a fluid's properties are the effect of one litre and the container multiplies them by its litres, a `fluid` block stores no key of the mod's own, and 0.25 L of Coffee landed the fluid entry's per-litre vector times 0.25 [#3157/C/inference, #1881, #1891/C/C-only, #2682/C/C-only, #3149/M/n=1].
- Declare a mod food's vector through the `NR_Nutrients` script key, a `key:value;key:value` string in the food's own block: the loader parks an unrecognised key in the item's default modData as a string, a second mod's block wins it key by key, the string was carried on both sides and the eat landed it with source declared, and the pass puts the key on no vanilla food [#3158/C/inference, #1187/C/C-only, #1281/M/n=1, #3148/M/n=1, #3150/M/n=2].
- Present the inferred vector of an unmapped food as a labelled judgement and never as data: a food with no table entry and no `FoodType` took the default template's densities times the item's own energy, and was recorded as inferred [#3159/C/inference, #3147/M/n=1].
- Regenerate the generated files with the tool and never edit them by hand: a script copy one byte off the server's disconnected the client while a copy differing only in line endings connected, and the tool's `--check` compares every generated file with a fresh emission, so a generated file must be byte-identical on every side, which only regeneration guarantees [#3160/C/inference, #3176/C/C-only, #1282/M/n=1, #3138/M/n=1].

## How it works

An item pass is a rebalance of vanilla foods shipped as script: one block per item, naming the vanilla item and the keys the rebalance owns.
The merge, the replay and the file map are [the loader's](../platform/loader-and-scripts.md), the keys [the item model's](../facts/food-item-model.md#script-keys) and what an eat does with a value [the eating pipeline's](../facts/eating-pipeline.md#modifiers); every per-food value and count is [the dataset](../reference/datasets.md#counts).

<a id="minimal-block"></a>
### The minimal override block

The smallest block that changes a key is an `item` block inside `module Base` that names the vanilla item and restates only the keys the pass re-bases; the loader merges bodies per key, so every key the block omits keeps its vanilla value and a pass over every item record of the food dataset can leave icons, models, evolved recipes and spoilage tracking upstream [#1017/M/n=1, #2007/C/C-only] ([loader-and-scripts.md#per-key-merge](../platform/loader-and-scripts.md#per-key-merge)).
The merge is measured on one food and one float macro, so a list, string or bool key rests on the code reading alone ([#1006/M/n=1]).
The measured block is a partial `item Orange` naming `DisplayCategory`, `ItemType` and one re-based macro, every instance getter and script key it does not name reading vanilla on both sides ([#1013/M/n=1], [#1014/M/n=1], [#1015/M/n=1]); with `ItemType` omitted it still merged into a food on both sides, the base module's food count unmoved ([#1018/M/n=1]); whether `DisplayCategory` can go as well is [open](#open).
A whole pass of such blocks over the mapped foods declares no item: the base module's food count held at the baseline's 722 with the pass loaded [#3141/M/n=1, #3180/M/n=2], and each re-based macro reads back as the float32 of the block's two-decimal value on the server, the client's copy and a client-local spawn alike ([#3143/M/n=2], [loader-and-scripts.md#per-side-load](../platform/loader-and-scripts.md#per-side-load)).

A full restatement of a vanilla block works too: the key it changes reads the new value and the keys it copied read their vanilla values on both sides ([#1008/M/n=1], [#1009/M/n=1]), and neither shape grows the base module's food pool, because a redefinition replaces rather than adds ([#1010/M/n=3]).
Its cost is every key it copies: a copied key is pinned at the copied value, even one restated at vanilla's own value, so an upstream patch to it no longer reaches the item, and it is contested with every other mod that declares it; the pin holds against vanilla too, because a mod's body always replays after vanilla's ([#1051], [loader-and-scripts.md#sorted-replay](../platform/loader-and-scripts.md#sorted-replay)).
Two bodies for one item, in the pass's own files or another mod's, compose per key, the later body in stored-path order winning any key both name ([#1006/M/n=1], [#1055/M/n=2]).
Beside a test mod whose script path sorts after the pass's, the test mod's full apple won the calories and carbohydrates, the two bodies' lipids and proteins being equal (0.31 / 0.47 in both), and its one-key orange won only the calories ([#3144/M/n=2]).
Vanilla uses the same idiom on itself, its own scripts redefining some of their own item names, every one of them in the base module ([#1440/C/snapshot]).

A misspelled key fails quietly: the parser's default arm writes an unrecognised key into the item's default modData and re-bases nothing ([#0212], [#1187/C/C-only], [loader-and-scripts.md#default-moddata](../platform/loader-and-scripts.md#default-moddata)).
Each key parses as its own type, which the item model's key table gives ([#0214], [#0215/C/snapshot]).
A misspelled item name declares a new item from the keys the block names, because the append arm is taken only when the loader already holds the name ([#1002], [#1020/M/n=1], [loader-and-scripts.md#bucket-append](../platform/loader-and-scripts.md#bucket-append)); for the same reason a block for an item a later patch renames or removes stops being an override ([#1002]).
Against another mod that names the same item, the block wins only the keys it names and only when its body replays last; the jar names the stored script path as the string that sorts, but no boot has separated it from the mod id, the folder name or the display name ([#1051], [#1056/C/C-only/open]).
The intersection of two mods' keys on one item is the whole of their conflict, so the fewer keys the pass declares, the smaller that surface.

The keys are not equally coupled.
The four macros are the least coupled: `Eat` reads them as bare fields with no state modifier and adds each, times the eaten fraction, to the store ([#0036/M/one-fixture], [#0018/M/one-fixture]), and a food's raw and cooked forms share them, burning being the one nutrition modifier on the eat path ([#0277/M/n=1], [#0019/M/one-fixture]), so a pass sets one number per macro per item.
`HungerChange` is the most coupled: it is the fraction a non-custom-weight food's displayed weight derives from ([#1214/C/C-only]), the unit a recipe input is charged in ([#0701/M/n=3]), the gate on which partial portions the eat menu offers ([#0079]), the full-portion value the eat fraction is rescaled against ([#0080]), the payload of the rot sickness roll ([#0052]) and the magnitude the cancel guard tests ([#0112], [mp-model.md#ownership](../platform/mp-model.md#ownership)).
`ThirstChange` runs a ladder of its own, in the opposite precedence to hunger's, and rot leaves it alone ([#0033/M/one-fixture], [#0035/M/one-fixture]); a cooked food's thirst change reaches a client halved once per server-to-client hop, a vanilla defect any client-side reader inherits ([#1147/M/n=1]).
A block that leaves the shelf-life keys out keeps vanilla's rot window on the instance ([#1016/M/one-side], [spoilage.md#formula](../facts/spoilage.md#formula)); whether a re-based food sets `CustomWeight = true` is [the item model's open question](../facts/food-item-model.md#open).
Every value a block carries is in script units, and an instance is not: `Item.InstanceItem` divides the script's hunger, thirst and endurance keys by a hundred and stores the four macros as written ([#0011/M/one-fixture], [eating-pipeline.md#script-scale](../facts/eating-pipeline.md#script-scale)).

A pass checks itself with a handful of reads: the load finishing says every value on a known key parsed ([#1188/C/C-only]), the base module's food count standing where vanilla left it says every block hit a held name ([#1010/M/n=3]), and an instance getter read on each side says the re-based value took, the same getter on an unnamed key that the rest stayed upstream ([#1014/M/n=1]).
None of those sees a misspelled key; only a census of a re-based item's modData against a vanilla control would, excluding the custom-name key a deserialised copy carries and the tooltip key a block's own `Tooltip` line writes ([#0212], [#1415/M/n=1], [#1044]).
The block costs nothing at run time, because both sides load it and no packet carries it, at the one price of the script checksum gate ([#1243/M/n=1], [mod-anatomy.md#checksum-gate](../platform/mod-anatomy.md#checksum-gate)).

<a id="pipeline"></a>
### The pipeline

The tool and the mapping behind the generated files are [the tools page](../reference/tools.md#food-nutrients) and [the datasets page](../reference/datasets.md#food-nutrient-map); this section reads what the engine does with what they emit.
The script file is a set of partial `module Base` blocks, 522 of them, one per mapped food, each naming `DisplayCategory` and the four macros [#3174/C/snapshot].
It carries no mod key: `NR_Nutrients` read as missing on all thirteen foods read, on the server, the client's copy and a client-local spawn [#3150/M/n=2].
The getters answer the block's value as a float32 and the script value is identical on both sides with no packet ([#3133/M/n=1]); a second mod's block for one of the same foods composes per key in the stored path's order ([#1183/M/n=2]).
Foods the pass reasons out of the table have no block and read their own script values, and a mapped record that lives in the no-nutrition part file, Butter, is re-based like any other ([#3151/M/n=2]).
The same data classifies each food for the mod's food mood: a generated table, written by the kernel's own rule over each food's per-100 g record, reads Butter (0.643 % sodium by weight, fat 0.995 of its macro energy), Margarine and MayonnaiseFull as plain energy whatever their salt, Bacon, Pepperoni, Dip_Ranch and Pretzel as salt-paired and palatable, and Lard, the three oils, Sugar, Flour, dry Rice and dry Pasta as plain, 34 of the 522 classified food types plain ([#4157/C/inference], [the tools page](../reference/tools.md#food-hedonics)).

The live readings that follow ran on the item-pass build and its close-wave build, the ones their rows' bounds name; the declared string's grammar is [new-nutrients.md](new-nutrients.md#declared-nutrients).
The first boot loaded the 90 121-byte script file and the generated Lua tables without an error on either side, under the admin bypass ([#3140/M/n=1]), and its three 20 s tick-rate windows read 0.9949 to 0.9950 of the previous build's 10 s window ([#3142/M/n=1]).
Under the fixture's admin role both boots stayed connected with no checksum line [#3187/M/n=2], so they say the copies agreed and nothing about the checksum gate itself.
An eaten food on the table lands the table's vector with the four macros the live item delivered: a whole apple matched the table entry on every non-macro key, its macros those of the profile's restated test apple [#3145/M/n=1], and both boots landed it again key for key, as they did a whole loaf's 40.02 mg of phytate from the generated table [#3182/M/n=2, #3183/M/n=2].
A food outside the table with no FoodType lands the `_default` template times its calories [#3147/M/n=1], and a food declaring `NR_Nutrients` lands its declared keys ahead of the table, its B12 landing at half the declared 0.5 [#3148/M/n=1]; the second boot repeated both, the inferred choline following that build's new `_default` density [#3184/M/n=2, #3185/M/n=2].
A coffee lands the fluid table's per-litre vector times the litres drunk, its caffeine on the gut lane, while the cola arm took no reading [#3149/M/n=1], and the second boot read the same [#3186/M/n=2].

The pass is weighed against the craft recipes it feeds, because a crafted output carries its own block's numbers rather than its inputs' ([#0708]).
`tools/recipe_conservation.py` costs each recipe's lines with the recipe dataset's own accounting and classes it at the bounds 1.1 and 0.9 of its inputs' calories: on the 42.21.0 data 13 conserve, 1 creates, 7 destroy and 8 inherit [#3570/C/arith.].
The recipes it cannot weigh are counted under the first refusal: 231 multi-type, 285 tags-only, 296 not-in-dataset, 54 no-nutrition, 37 no-outputs, 33 variable-amount, 2 drainable, 1 fluid-sourced and 1 wildcard [#3571/C/arith.].
The splits, one input cut, sliced or opened into several items, class 8 conserves, 6 inherits, 2 destroys and 0 creates [#3572/C/arith.].
The mapping errors are fixed in the mapping: the hot-dog pack is four 52 g wieners on the wieners' own row, 208.0 g at 603.2 kcal, so opening it conserves at 1.0 [#3577/C/arith.]; the hot dog is the bun and the wiener it is assembled from, 63.4 g and 52 g of their own rows, 115.4 g at 327.686 kcal, so assembling one conserves at 1.0 [#3578/C/arith.]; and the meat patty is the whole tub of mince it is pressed from, 139.5 g at 299.925 kcal, so pressing it conserves [#3579/C/arith.].
`open_mac_and_cheese` reads as a creator on its output scripts alone, but its Java `OnCreate` leaves the macaroni a sixth of its own values [#3575/C/C-only], so it conserves at 0.99993 [#3576/C/arith.].
One creator is left as a vanilla design, `MakeTortillaChips` at 4.121831, whose recipe spends 1 of a tortilla's 5 uses, which the tool notes on its row [#3573/C/arith.].
Seven destroyers are left as vanilla designs: the two bird cuts at 0.867277 and 0.663005, the four corn grinds at 0.0, whose flour is an inedible spice with no macros, and `ScoopIceCream` at 0.857297 [#3574/C/arith.].

<a id="scope"></a>
### What a `module Base` pass covers

A `module Base` pass reaches the base module's food items and, once drainables and fluid containers are counted, every record of the food dataset ([#1228/M/n=1], [datasets.md#counts](../reference/datasets.md#counts)); the records are a scan of one build, so a pass generated from them reaches a later build's new foods only after a re-scan.
The records differ in where their nutrition lives, by the dataset's [kind rule](../reference/datasets.md#kinds).
A food record carries its nutrition as its own script keys, though a share of the dataset's rows name no nutrition source, foods among them, and a block for such an item adds macros where vanilla wrote none ([#0622/C/snapshot], [datasets.md#columns](../reference/datasets.md#columns)).
A drainable record is an `item` block parsed by the same method as a food's ([#0211/C/snapshot]) and takes the same per-key path, though the merge is measured on a food alone ([#1180/M/n=1]); almost none carries a nutrition key, and the few calorie lines among them write zero ([#0612/C/snapshot]).
The fluid-container records are not food blocks: the kind takes every item that owns a fluid-container component, clothing and weapons among them ([#0613/C/snapshot]), and its record's nutrition columns are joined from the first fluid it lists ([#0626/C/snapshot]).
A container's live instance answers none of the food nutrition getters, so a drink's nutrition is reachable only through its fluid ([#0604/M/n=2]), whose figures are per litre and multiplied by what the container holds ([#0630], [eating-pipeline.md#fluid-path](../facts/eating-pipeline.md#fluid-path)).
Every merge reading here is of `item` blocks; whether a repeated `fluid` block merges per key is outside the library ([loader-and-scripts.md#walls](../platform/loader-and-scripts.md#walls)).

A `module Base` item pass does not touch foods a mod declares in its own module, so on a server running both, `LongTermPreservation4220`'s 14 `module Skittles` foods keep their upstream numbers while vanilla's are re-based [#1030/M/n=1].
The two sets still meet: some of that mod's foods feed vanilla evolved recipes and some vanilla items come out of its recipes, so a re-based vanilla ingredient flows into its dishes ([#1461/C/snapshot], [longtermpreservation.md#compat](../facts/other-mods/longtermpreservation.md#compat)).
A new item in a mod's own module costs its display name on a dedicated server, which resolves no mod item's display name even with the translation file shipped ([#1167/M/n=1], [#3206/M/n=2]).
A block naming another mod's food is an override only while that mod is loaded (the append arm), and wins only the keys it names when its body replays after that mod's own ([#1055/M/n=2]); without the mod, the same block declares a new item, a reading no run has exercised.

Recipe blocks are outside the pass, and the numbers move without them: a crafted output carries its own item's script macros ([#0708], [cooking-and-recipes.md#uses](../facts/cooking-and-recipes.md#uses)), except in a split, where an input flagged to pass its food on gives every output a share of the consumed instance's macros ([#0706/C/snapshot]).
An evolved dish is summed from its ingredients' macros at build time, each contribution asked in hunger and clamped to the ingredient's own, so a re-based ingredient changes both what a dish gains and how much of the ingredient it takes ([#0283], [cooking-and-recipes.md#evolved](../facts/cooking-and-recipes.md#evolved)).
Some vanilla ingredient keys already ask for more hunger than their ingredient carries and sit on that clamp, so a pass that lowers an ingredient's hunger can move more of them onto it ([#0289/C/snapshot]).

## Options

<a id="route-options"></a>
### The routes into a vanilla food

A mod has five routes into a vanilla item's nutrition — a full restatement of the vanilla block in `module Base`, a partial block in `module Base`, a new item in the mod's own module, Lua hooks on the instance, and item modData with `syncItemFields()` — and the three script routes carry no sync cost while the two Lua routes do; the route inventory is dated 2026-09-11 [#1001/M/n=1].
The script routes are free on both sides because item scripts load per side and never sync ([#1124/M/n=1]); the new-item route is the pass's boundary, read under [What a `module Base` pass covers](#scope).
The Lua routes are per instance: the eat completes on the server ([#0110], [mp-model.md#ownership](../platform/mp-model.md#ownership)), and whatever a hook writes to an item reaches a client only through the item packet's fields ([#1144/M/n=1], [wire-packets.md#item-stats-packet](../facts/wire-packets.md#item-stats-packet)).
`OnEat` and `OnCooked` attach through a script key, one string per item with the last body winning, so a pass that names one replaces the hook vanilla gave that block ([#0215/C/snapshot], [#1006/M/n=1]), the home-canning cook hook among them ([#0312/C/snapshot]).
Rot is a Lua-route question: aging never writes an item's hunger or macro fields ([#0254/M/n=1], [spoilage.md#formula](../facts/spoilage.md#formula)), so rot that costs calories has to change the eat path or the read-time getters, because an item's stored macros are a pure function of its script values and how much of it has been eaten, a consequence reasoned from the write set [#0255/C/inference]; the hook routes are [eat-and-cook-hooks.md](eat-and-cook-hooks.md).

| option | what it costs | which wall it hits | tags |
|---|---|---|---|
| item modData on each instance, pushed with `syncItemFields()` | a Lua write and a sync call on every instance it covers; carries a new field beside the vanilla numbers rather than re-basing them | the table moves wholesale, the receiver wiping its copy first; only client-to-server is measured | [#1126/M/one-side], [#1001/M/n=1] |
| an eat or cook Lua hook — `OnEat`, a server-side wrapper of `ISEatFoodAction.complete`, `OnCooked` | a hook on every eat or cook it covers, and a second write of numbers vanilla already wrote when it corrects after the fact | only the server-side wrapper runs before `Eat`, and it keeps vanilla's numbers out only by skipping the original; `OnEat` corrects after every write, in a handler that runs on both sides; item writes reach a client only through the item packet; the `OnCooked` pipeline is read from the code, never driven end to end | [#1129/M/n=1], [#1130/M/n=1], [#1144/M/n=1], [#1154/M/n=1], [#1001/M/n=1] |
| a full `module Base` restatement | nothing at run time; every copied key pinned against upstream patches and contested with any mod that declares it | the same-relative-path drop, the per-key merge, byte-identical script files, the replay order on every key, the identity re-stamp | [#1175/C/C-only], [#1180/M/n=1], [#1182/C/C-only], [#1183/M/n=2], [#1184/C/C-only], [#1001/M/n=1] |
| a partial block naming only the re-based keys | nothing at run time; every omitted key follows upstream, a later patch included, and only shared keys are contested | as the full restatement, plus the one-minimal-block-per-item workaround, contested only on a key two mods both declare | [#1175/C/C-only], [#1180/M/n=1], [#1181/M/n=1], [#1182/C/C-only], [#1183/M/n=2], [#1184/C/C-only], [#1001/M/n=1] |

## Walls and bounds
<a id="walls"></a>

A mod can run the per-key merge across every `base:food` item only with a workaround: one minimal `module Base` block per item, with every untouched key left at whatever upstream says, including whatever a later patch changes it to [#1181/M/n=1]; the merge under it is measured on one item for one float macro [#1180/M/n=1].
No block can remove a key vanilla wrote, only change its value or add one vanilla left out, `CustomWeight` for instance ([#1005]), and absence is a value of its own: an item that writes no shelf-life key reads back the never-ages sentinel rather than a zero ([#0619/M/n=1]), and an empty dataset cell is an absent key, never a zero ([#0618]), so a generator that fills blanks with zeros changes items it meant to restate.
The replay order is the pass's to live with rather than to set: bodies replay sorted by the stored script path with the last winning per key ([#1183/M/n=2]), so one block per item keeps the pass robust to the replay order for every key it does not touch and contested only on the keys two mods both declare [#1057/M/n=1].
Two mods at one relative script path lose one file's blocks entirely, so the pass's script files take a mod-unique basename — a code reading, the across-two-mods arm unmeasured ([#1175/C/C-only], [#1050/C/C-only], [loader-and-scripts.md#path-collisions](../platform/loader-and-scripts.md#path-collisions)).
Every appended body re-stamps the item's script file name and allocates a fresh net id, and whether a stale id ever reaches the wire is unread ([#1184/C/C-only], [loader-and-scripts.md#identity](../platform/loader-and-scripts.md#identity)).
The approved modlist offers no vanilla food override to learn from, so the item-pass mechanism a nutrition overhaul needs has no local precedent and the nearest evidence is on the Workshop [#1674/C/snapshot].
At the 2026-09-10 17:47 corpus sweep, across the nine `script_nutrition` mods of the 230-mod inventory there is exactly one name collision against the 5 092 distinct `module Base` item names vanilla declares, `Horse` redefining `Base.Rope`; seven of the nine declare `module Base` and only two define an item under it, so a pass over every record of the food dataset ([the counts](../reference/datasets.md#counts)) has no shipped example to imitate [#1019/C/snapshot]; the corpus drifts, and the census is the catalog's and the name count the dataset page's ([#1229/C/snapshot], [#1572/C/snapshot], [catalog.md#corpus-facts](../facts/other-mods/catalog.md#corpus-facts)).
`CustomWeight = true` keeps a re-based hunger value off the weight, but the flag routes the weight getter through the display-name guard, which a dedicated server fails for every mod item ([#1443], [#1167/M/n=1]); such an item reads an unmodded weight of zero, which the item packet ships to every client ([#1166/C/C-only], [food-item-model.md#state-axes](../facts/food-item-model.md#state-axes)).
A re-based hunger value can land under the cancel guard, whose test is the state-modified getter, so a value above it fresh can fall under it with staleness, rot or burning ([#0003]); a cancelled guarded eat applies nothing by the code, and played live it left the item whole and landed nothing in the mod ([#0112], [#1299/M], [open-questions.md#x33](open-questions.md#x33)).
Not covered: a script reload in a running session, what a re-based block does to instances and dishes already in a save, the translation of a re-based item's name, a drink of the Cola fluid (the harness found no fluid type of that name, so its arm took no reading [#3149/M/n=1]), and any single-player session — every reading here is of `item` blocks loaded once at boot on the dedicated-server path.

## Open
<a id="open"></a>

- Whether a partial block that omits `DisplayCategory` as well as `ItemType` still merges into a food — settled by the same partial block with both keys omitted, reading the base-module food count and the instance getters on both sides [#3136/C/open].
- Which string orders the replay — mod id, folder name, stored script path or display name — settled by four sort mods, each built to win under exactly one candidate key; -> X19 ([#1285/C/open], [#1056/C/C-only/open], [#0886/M/n=2/open], [open-questions.md#x19](open-questions.md#x19)).
- Whether two mods at one relative path both load, for a script file and a Lua file, and whether a mod file at a vanilla relative script path is dropped entirely — settled by two mods shipping the same relative paths with different content, plus a boot that ships a mod file at a vanilla relative script path; -> X20 ([#1286/C/open], [open-questions.md#x20](open-questions.md#x20)).
- Whether the fresh net id each appended body allocates ever puts a stale id on the wire — settled by reading a multiply-redefined item's `getID` and full type on both sides; -> X27 ([#1293/C/open], [#1063/C/C-only/open], [open-questions.md#x27](open-questions.md#x27)).
- Whether a vanilla food absent from the item-name table trips the display-name weight guard the way a mod item does is unverified: its one reading rests on a restricted artifact key, and its owner carries the re-measure ([#1427/M/n=1/unverified], [food-item-model.md#open](../facts/food-item-model.md#open)).
- Whether the server's 60 s checksum arm acts on a mismatched client is unmeasured: the 157.806 s watched past the warning held no act, and the jar reads the act after the grace [#3178/C/open], [#1231/C/C-only] — settled by holding a mismatched client connected past the grace.
- Decision the rows force: whether the pass reaches foods other mods declare in their own modules, which a `module Base` pass leaves on upstream numbers ([#1030/M/n=1], [#1002]).
- Decision the rows force: whether the pass re-bases drinks, whose nutrition lives on a fluid, per litre ([#0626/C/snapshot], [#0604/M/n=2]).
- Decision the rows force: whether the pass names `HungerChange` at all — hunger drives weight, recipe cost, the portion menu and the cancel guard, where the macros move intake alone ([#1214/C/C-only], [#0701/M/n=3], [#0036/M/one-fixture]).
- Decision the rows force: which route carries each value the pass changes — a script block both sides load for free, or a per-instance Lua write that has to cross the wire ([#1001/M/n=1]).

## Worked examples

| shape | file:lines | what it shows |
|---|---|---|
| the minimal override block | `testing/experiments/TKX_ItemOverride/42.20/media/scripts/tkx_item_override.txt:24-29` | a partial `item Orange` in `module Base` naming the two header keys and one macro — the shape a pass ships once per item |
| a full restatement | `testing/experiments/TKX_ItemOverride/42.20/media/scripts/tkx_item_override.txt:3-22` | the vanilla `Apple` block copied into `module Base` with one macro changed — every key pinned at the copied value |
| a food in the mod's own module | `testing/experiments/TKX_ItemOverride/42.20/media/scripts/tkx_item_override.txt:55-71` | `item FibreBar` in `module TKX` — the route that adds rather than overrides, and the kind of record a `module Base` pass never reaches |

## See also

- [`../platform/loader-and-scripts.md`](../platform/loader-and-scripts.md#per-key-merge) — the per-key merge, the sorted replay, the file map and the identity re-stamp.
- [`../facts/food-item-model.md`](../facts/food-item-model.md#script-keys) — the keys a block can name and the weight arms a hunger rewrite moves.
- [`../facts/eating-pipeline.md`](../facts/eating-pipeline.md#modifiers) — what an eat does with a re-based value, and the script-to-instance scale.
- [`../facts/cooking-and-recipes.md`](../facts/cooking-and-recipes.md#evolved) — how a re-based ingredient reaches a dish and a recipe's cost.
- [`../platform/mod-anatomy.md`](../platform/mod-anatomy.md#checksum-gate) — the script checksum gate every shipped block pays.
- [`../reference/wall-map.md`](../reference/wall-map.md) — the verdict rows the walls cite by id.
- [`eat-and-cook-hooks.md`](eat-and-cook-hooks.md) and [`new-nutrients.md`](new-nutrients.md) — the hook routes, and where a mod nutrient beside the vanilla numbers lives.
- [`open-questions.md`](open-questions.md) — the experiments that settle this page's open rows.
