# Long Term Preservation
Verified against 42.20.4 (b0bbce05d5) · 2026-09-22 · scope: what this workshop preservation mod adds, how its two cook hooks are built, and which of its techniques and failures a nutrition mod should copy or avoid; the item packet's field list and every cross-side reading belong to `facts/wire-packets.md`, the weight arms and the display-name guard to `facts/food-item-model.md`, and the cook block that calls its hooks to `facts/cooking-and-recipes.md`.

## Key facts
<a id="techniques"></a>

- Script-key dispatch into a mod's own Lua runs code at the moment the mod cares about without monkey-patching anything: this mod patches zero vanilla API surface, and all seven of its globals are new names checked one by one against the whole vanilla Lua tree with zero hits [#1436/C/snapshot].
- Consuming vanilla extension points costs nothing and inherits their behaviour: the forage-definition event plus the forage system's own add-item call register a new forageable, and two Java recipe statics called straight from script give the jarring recipes vanilla's exact behaviour for free [#1437].
- Re-basing an age fraction onto a new window by re-reading the setter's own result — compute the fraction against the old maximum, set the new maximum, then set the age from the new one — reads like a double-read bug and is the correct idiom [#1439].
- Declaring its own script module and importing the base one gives a content mod zero name collisions: vanilla declares 5 092 distinct item names across 5 105 item blocks, 13 of them redefinitions of a name declared earlier and every one of them in the base module, and the recipe dataset carries 969 recipes [#1440/C/snapshot].
- Pinning shelf life in the item script rather than in Lua needs no sync at all, because script values load identically on both sides: everything this mod expresses in Lua is what desyncs and everything it expresses in script is safe [#1441].

## How it works

<a id="what-it-does"></a>
### What it does in play

Long Term Preservation is a content mod: it adds preserved foods and the recipes that make them, and it changes nothing about vanilla's nutrition model, its eat path or its weight model.
Salting and drying turns one raw meat and five salt into a cured twin that keeps 53 days fresh and 60 days to totally rotten, against the 2 and 4 of its vanilla input [#1382].
The cured item is a separate item rather than a flag on the original, so the long shelf life is a property of the new script block and not of any state written at craft time.
The mod also jars four meats vanilla does not cover by cloning vanilla's own jar recipes with the same Java create statics and the same times, adds pemmican, rendered lard, mashed berries and jam, and adds a foraged salt rock plus a mortar-and-pestle recipe that crushes it into vanilla salt [#1383].
Cooking a cured meat makes it non-perishable and 30 per cent less nutritious, and cooking a jar re-bases its age onto a 180-day window with a 150-day fresh point [#1384].
Both changes fire at the cooking transition rather than at the craft, so a cured meat that is never cooked runs none of the mod's item-changing Lua.
The craft is script and the cook is Lua: the cooked-state changes are the only thing the mod expresses in Lua that changes an item, and nothing it adds touches a player — no nutrition read, no moodle, no stat write and no interface element.

<a id="architecture"></a>
### Architecture: where its code lives and what runs it

Long Term Preservation is workshop item `3774789651`, one mod, declaring the id `SKITTLE_LongTermPreservation4220` in a folder named `LongTermPreservation4220` — a whole-prefix drift — so the declared id is what a `Mods=` line must carry and the folder name resolves to nothing [#1379/C/snapshot].
Long Term Preservation ships a single version folder and no common tree, and all 52 of its files carry one mtime — a Steam download stamp, not an update history — over 239 131 bytes of which one poster and two art files are 188 245, or 79 per cent [#1380/C/snapshot].
The missing common tree is what makes the loader print this mod an empty override tail, a line whose cause is the folder search rather than a census of what the mod shadows ([#1450/M/n=2], [#1452], [`../../platform/loader-and-scripts.md#file-map`](../../platform/loader-and-scripts.md#file-map)).
The loader also logs a benign missing-file line for each animation-set and action-group folder the mod does not ship, which is a property of the probe rather than of the mod ([#1454/M/n=2], [`../../platform/mod-anatomy.md#mod-discovery`](../../platform/mod-anatomy.md#mod-discovery)).
Neither line is evidence about what this mod replaces.

The mod's architecture is a six-row file table dated 2026-09-10: 89 Lua lines over two files, three script files of 412, 186 and 16 lines, and three translation files in 13 language trees, with 36 of its 44 text files ending without a terminating newline [#1385/C/snapshot]:

| File | Lines | Side | Role |
|---|---:|---|---|
| `42.20/media/lua/server/recipe_meats.lua` | 61 | **server** (+ singleplayer) | all 7 Lua globals; every nutrition write in the mod |
| `42.20/media/lua/shared/Foraging/forageable_items.lua` | 28 | shared (both sides) | the mod's entire event surface |
| `42.20/media/scripts/items/items_dried.txt` | 412 | script (loaded per side, never synced) | 15 live `item` blocks |
| `42.20/media/scripts/recipes/recipe_cured.txt` | 186 | script | 8 `craftRecipe` + 3 `itemMapper` |
| `42.20/media/scripts/items/models_skittles.txt` | 16 | script | 2 `model` blocks |
| `42.20/media/lua/shared/Translate/EN/{ItemName,Recipes,Tooltip}_EN.txt` | 18 / 11 / 6 | shared | 15 item names, 8 recipe names, 3 tooltips; 13 language trees in all |

The line counts in that table are real last-line numbers, so a newline-counting tool reads one lower [#1385/C/snapshot].
All seven of the mod's Lua globals and every nutrition write it makes live in its server tree, its shared tree holds only the forage definition and the translations, and there is no client tree at all [#1386].
On a multiplayer client every name its item scripts dispatch to is an undefined global, while the item scripts themselves load identically on both sides ([#1393/M/n=1], [`../../platform/loader-and-scripts.md#per-side-load`](../../platform/loader-and-scripts.md#per-side-load)).
Every runtime difference between the two sides is therefore attributable to the packet and never to a script mismatch, which is what makes this mod a clean instrument for reading the packet.

The mod's entire event surface is one registration on the forage-definition event, made after requiring vanilla's own forage system, which registers one forageable with a snow chance of -50, 8 zones and 2 experience [#1387].
Everything else dispatches from script into Lua at 15 sites — a cook hook on 4 cured meats and 8 jar items plus three recipe create and test keys — while two further script keys call Java statics directly, and the mod has no timed action, no context menu, no derived action and no method on a vanilla class anywhere [#1388].
Its own item mapper collapses a whole input family into a single recipe block, and the engine's result lookup resolves the mapped outputs ([#1438/M/n=1], [`../../platform/loader-and-scripts.md#craft-recipe-grammar`](../../platform/loader-and-scripts.md#craft-recipe-grammar)).

Long Term Preservation keeps no mod state of the usual kind: zero modData reads or writes, zero sandbox references, zero command-bus sites and zero player-nutrition reads across the whole live tree, so all of its state lives in one inventory item's own Java fields, written by the two cook hooks [#1389/C/snapshot].
A census of one of its items is nevertheless not empty, because the script tooltip the item parser rawsets at instantiation is an item modData key on every side that builds the item ([#1044], [#1415/M/n=1], [`../../platform/loader-and-scripts.md#default-moddata`](../../platform/loader-and-scripts.md#default-moddata)); that key is not a Lua write of the mod's.
Keeping state in engine fields alone leaves the mod no place to put a value the packet refuses to carry.

The cured-meat cook hook is an 11-setter, four-print table dated 2026-09-10 in which the four macros and the raw hunger field are carried by the item packet, the actual weight is carried through the unmodded getter, and the cookable flag, the two age-window sentinels, the plain weight and the custom-weight flag are not [#1390/C/snapshot]:

| Line | Call | Carried by `ItemStatsPacket`? |
|---|---|---|
| `:36` | `setIsCookable(false)` | no |
| `:39` | `setOffAge(1000000000)` — the "never ages" sentinel | no |
| `:40` | `setOffAgeMax(1000000000)` | no |
| `:42` | `setActualWeight(getActualWeight() * 0.7)` | **yes** — `setData` fills `packet.actualWeight` from `Food.getActualWeightUnmodded()`; `applyItemStats` writes it back with `Food.setActualWeight` |
| `:43` | `setWeight(getActualWeight())` | no — `InventoryItem.weight` is not one of the 43 |
| `:44` | `setCustomWeight(true)` | no |
| `:45-:48` | `setCarbohydrates` / `setLipids` / `setProteins` / `setCalories`, each `× 0.70` | **yes** (all four) |
| `:49` | `setHungChange(× 0.70)` | **yes**, and as the **raw** field |
| `:35,37,41,52` | four `print()` calls (`changing da meat`, `post cookable`, `meat change days`, `meat done`) | server console only |

Both hooks are ordinary Lua functions taking the item as their only argument, with no container walk, no side test and no player reference in either of them.
The never-ages value the cured-meat hook writes is vanilla's sentinel rather than a number the mod invented, which is why a cured meat stops aging outright instead of aging slowly.
The jar cook hook writes only an age maximum of 180, an age-off point of 150 and an age derived from the new maximum, and not one of those three fields is in the item packet, so the jarring half of the mod writes nothing a client can ever learn [#1391].
The jar hook's double read of the age maximum is deliberate rather than a bug: computing the aged fraction against the old maximum, setting the new maximum, then setting the age from the new one preserves the fraction, so a jar at 10 per cent of its old life comes out at 18 days of a 180-day life, that 18 being the fraction applied to the new window rather than a measured value [#1392/C/arith.].

<a id="mp"></a>
### Multiplayer behaviour

It has no command bus, no modData and no push of its own, and the engine's server-guarded item-stats pushes inside the cook block are what carry its writes ([#1395], [`../../platform/mp-model.md#routes-server-to-client`](../../platform/mp-model.md#routes-server-to-client)).
Its whole multiplayer contract is therefore the item packet's field list, and anything it writes outside that list is server-only state ([#1396], [#1398], [`../wire-packets.md#item-stats-packet`](../wire-packets.md#item-stats-packet)).
Nothing about that contract is specific to this mod: it is what any mod that writes an item field from a server-side hook inherits.

What a client-side reader gets wrong on a cooked cured meat is the four uncarried fields plus the thirst getter, which reads half the server's value: the five macros are right, the plain weight is right, and the actual weight is the one field where the client holds the intended value and the server does not [#1463/M/n=1].
The four macros travel, and the raw hunger field travels as the raw field and is laddered once on each side ([#1399/M/n=1], [#1400/M/n=1]).
The two age-window fields, the cookable flag and the custom-weight flag desync whole ([#1401/M/n=1], [#1402/M/n=1], [#1403/M/n=1]).
The actual weight splits between the sides while the plain weight, equally uncarried, does not, which is what makes "uncarried" and "desynced" two different words ([#1404/M/n=2], [#1406/M/n=1]).
The zero the server reads for the actual weight is the display-name guard rather than a cook effect, and it is already there before any cooking ([#1405/M/n=2]).
The thirst halving is vanilla's rather than the mod's, and it settles at one halving per hop rather than compounding ([#1407/M/n=1], [#1408], [#1409/M/n=1]).
The cooked flag, the cooking time and the two minute fields stay synced throughout ([#1410/M/n=1]).
The desyncs are a change rather than a standing difference, because the snapshot taken before the transition is not desynced at all ([#1416/M/n=1]).
In this hook the fields that travel happen to be the ones it multiplies and the fields that do not are the ones it sets outright; membership of the packet is fixed by the engine, so a mod cannot tell from its own code which of its writes will arrive, and the packet's list has to be read before a hook is written.

The server ran the cook transition, and it granted the cooking experience for that transition on its own side ([#1417/M/n=1], [#1413/M/n=1]).
The scripted last-cook-minute flip is not a precondition of the transition ([#1418/M/n=2], [`../cooking-and-recipes.md#cook-block`](../cooking-and-recipes.md#cook-block)).
The client's copy of the same item did not advance at all across the observed window, and whether a client's copy advances is answered per arm rather than once ([#1411/M/n=1], [#1421/M/n=1], [#1423/M/n=1], [`../../platform/mp-model.md#what-a-client-copy-is`](../../platform/mp-model.md#what-a-client-copy-is)).
Age never reaches a client on any arm ([#1412/M/n=2], [`../spoilage.md#writes`](../spoilage.md#writes)).
The server's own item tick is slow relative to a frame, which is why a frozen client reading is legible at all rather than a sampling artefact ([#1419/M/n=2]).
Float rendering on the two sessions that measured this mod was rounded by the harness, so every difference recorded here is a whole-value one rather than a bit-level one ([#1435/M/n=1], [`../../platform/harness.md#artifacts-discipline`](../../platform/harness.md#artifacts-discipline)).

## Walls and bounds

<a id="pitfalls"></a>
### What it gets wrong

- Four of the mod's cook-hook writes are outside the item packet's field list, so the client's copy of a cured meat keeps its pre-cook shelf life and stays cookable forever and no amount of re-pushing fixes it [#1442].
- Flipping the custom-weight flag on an item whose display name does not resolve silently destroys the value just computed: the hook writes 0.35 and then moves the server onto the arm that reads it through the display-name guard, which returns 0, so the intended 30 per cent reduction is discarded on the authoritative side [#1443].
- The mod declares seven unqualified globals with generic names, and although a grep of every Lua file in the installed 230-mod corpus finds only this mod defining any of them, a recipe create key calling someone else's same-named function would fail silently and load-order-dependently [#1444/C/snapshot].
- Dead and defective code is wired into live script keys: two empty function bodies sit behind two live recipe create keys under a comment describing weight code that is not there, two further functions have zero reference sites, one line's chained comparison is unreachable, and the live recipe test is a no-op guard whose comment names a weight floor its body does not apply [#1445].
- The mod prints four lines per cooked meat to the server console from inside a shipped hook, with no way for an admin to turn them off [#1447].
- The jarring half of the mod is 8 of its 12 cook-hook sites and sets only three uncarried fields, so on a dedicated server a jarred food's client copy shows the pre-cook shelf life indefinitely and the feature is singleplayer-only whether or not that was meant [#1448].

Under the first two a value is computed correctly and then stored somewhere that cannot deliver it, and neither failure raises, logs or degrades visibly on either side.
The first and the last rest on the packet's omission list ([#1398], [`../wire-packets.md#item-stats-packet`](../wire-packets.md#item-stats-packet)).
The second rests on the pair of weight arms the custom-weight flag chooses between, and on the guard that returns nothing for an item whose display name equals its full type ([#1424/M/n=1], [#1425], [#1426/M/n=2], [`../food-item-model.md#state-axes`](../food-item-model.md#state-axes)).
The unreachable comparison in the fourth is a Lua expression that never ran, so nothing about it is a measurement of the engine's tolerance for such an expression.
Separately, the mod ships a brace-unbalanced item script that the engine loads anyway, which is tolerance rather than contract ([#1446/M/n=1], [`../../platform/loader-and-scripts.md#script-dsl`](../../platform/loader-and-scripts.md#script-dsl)).

<a id="compat"></a>
### What it collides with, and what a nutrition mod must do about it

- Load order is irrelevant to this mod: no monkey-patching, no vanilla script-block redefinition across its 15 item names, 8 recipe names and 2 model names, no dependency line in its `mod.info`, and its single require is vanilla's own forage system, whose event already serialises the one ordering-sensitive surface it has [#1449/C/snapshot].
- The mod adds 14 new food items with a full macro set in its own script module and makes 117 nutrition-key writes, so an item pass rewriting the base module will not touch them; five of the fourteen also feed vanilla evolved recipes, and two vanilla items are produced by its own recipes and inherit any change made to them [#1461/C/snapshot].
- The cured fish is the one item whose macros are not its input's: 420 calories, 3 lipids, 25 carbohydrates and 55 proteins against the fillet's 205, 1, 12 and 28.52, roughly a doubling, where the other three cured meats copy their inputs exactly [#1462].
- Long Term Preservation ships no licence or readme file and its fetched Workshop record carries no licence field, so its permissions posture is default Steam Workshop terms: read it, do not vendor it [#1381/W/snapshot].

A server running both this mod and a base-module rebalance has one set of foods on rebalanced numbers and this mod's own on upstream numbers; the two meet only through the evolved-recipe feed and the two vanilla outputs, where the rebalance flows into this mod's dishes and crafting.

It has no command bus and no interface surface at all, so it cannot collide with the command sites of the resident quest stack or with the client tree of the resident interface mod ([#1459/C/snapshot], [#1457/C/snapshot], [`catalog.md#corpus-facts`](catalog.md#corpus-facts)).
Looking one of its recipes up by name needs the module prefix, because a dot-less name resolves against neither spelling the shipped lookup tries ([#1455/M/n=1], [`../../platform/loader-and-scripts.md#name-resolution`](../../platform/loader-and-scripts.md#name-resolution)), so a bare recipe name of its own has to be resolved by scanning every craft recipe.
The live craft-recipe count with the mod loaded is the vanilla census plus its own blocks, which the dataset page carries ([#1456/C/snapshot], [`../../reference/datasets.md`](../../reference/datasets.md)).
The harness placed the mod under its declared id rather than under its folder name, and the rename is a convenience rather than a requirement: a folder whose name matches neither declared id loads unrenamed when the mod list names the version directory's id ([#1453/M/n=1], [#1832/M/n=1], [`../../platform/mod-anatomy.md#folder-name`](../../platform/mod-anatomy.md#folder-name)).

A mod cannot add a field to the item packet nor depend on a field it omits, cannot trust a cooked food's thirst change on a client, and cannot ship a food absent from the vanilla translation table without losing its unmodded weight to the display-name guard ([#1144/M/n=1], [#1147/M/n=1], [#1166/C/C-only]).
The one wall that opens for it is that a crafted instance can be rewritten from the cook hook at all, which is what makes its cured meats possible in the first place ([#1154/M/n=1]).
Its own translation files are in the older layout, which is the reason its item names never resolve and the reason its weight guard fires ([#1165/M/n=1]); a mod that adds foods and wants their unmodded weight to be non-zero has to ship them in the layout the current build reads.

Not covered: no single-player session was ever booted and no relog or save round-trip was ever read, so every statement here about the mod's runtime behaviour is the dedicated-server path with one live client; its art, models and non-English translation trees were counted but never opened; nothing was read about how it behaves beside another preservation mod; and its recipes were exercised only through the cook transition, never through an ordinary craft, a spoil transition or a container move.

## Open
<a id="open"></a>

- Two questions this mod raises are unanswered here: whether a relog or a save round-trip repairs a client's copy of the uncarried fields, and whether a client copy that still believes a cured meat is cookable would dispatch the mod's cook hook in the client's Lua state if it ever ticked; the first is carried on the packet page and the second on the Lua platform page ([#1434/C/inference/open], [#1394/C/C-only]).
- The design must decide whether it namespaces every Lua global it defines, because this mod's generic unqualified names are collision-free only against a dated sweep of the installed corpus [#1444/C/snapshot].

## See also

- [`../wire-packets.md`](../wire-packets.md) — the item packet's field list and every cross-side reading this mod produced.
- [`../food-item-model.md`](../food-item-model.md) — the weight arms and the display-name guard behind its weight defect.
- [`../spoilage.md`](../spoilage.md) — the age clock its cook hooks rewrite.
- [`../cooking-and-recipes.md`](../cooking-and-recipes.md) — the cook block that calls its hooks.
- [`../../platform/mp-model.md`](../../platform/mp-model.md) — who owns an item in multiplayer and what a client's copy is.
- [`../../platform/loader-and-scripts.md`](../../platform/loader-and-scripts.md) — script-key dispatch, the script grammar and the loader's file map.
- [`itemquality.md`](itemquality.md) — the same unsynced-field failure in a mod that meant to sync.
- [`catalog.md`](catalog.md) — the corpus counts this mod's empty command and interface surface is measured against.
