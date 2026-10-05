# Other mods — the corpus catalog
Verified against 42.20.4 (b0bbce05d5) · 2026-10-01 · scope: what the installed workshop corpus and the public Workshop hold on the nutrition surface, as dated sweeps, per-candidate build status, the API surface the corpus uses and the corpus-level counts; the five torn-down mods have their own pages, the packet mechanisms are `platform/mp-model.md` and the dataset columns are `reference/datasets.md`.

## Key facts

- The locally installed workshop corpus at the 2026-09-10 17:47 sweep is 179 workshop items holding 230 mod folders, 229 of which declare an id the engine can index [#1551/C/snapshot].
- Nineteen of those 230 mod folders touch the nutrition surface: 11 call a nutrition API from Lua and 9 write a nutrition key in a shipped script, with exactly one mod on both lists [#1555/C/snapshot].
- Only two mods in the corpus write a nutrition macro and they write it on different objects, so nine of the eleven Lua-signalled mods never write one at all [#1581/C/snapshot].
- On `42.20.4` the installed corpus contains no vanilla food override at all: every nutrition-bearing script block in it adds a new item [#1595/C/snapshot].
- There is one item-name collision across the 230-mod installed corpus, so a `module Base` redefinition pass has no corpus precedent [#1229/C/snapshot].
- No mod in the installed corpus uses `loadstring` [#1222/C/snapshot, #1565/C/snapshot].
- No corpus row's layout is a flat `B41` one — all 230 resolve a `42[.x[.y]]/` or `common/` folder — while 153 rows still ship a bare root `media/` beside their live version folder that the scan does not read [#1566/C/snapshot].
- 177 of the 230 corpus rows ship a `common/media`, which the signal scan does not open, so any zero on such a row is a partial view [#1559/C/snapshot].
- The public Workshop sweep of 2026-09-10 16:26 returned 212 results over eight terms, collapsing to 180 distinct ids with 3 installed and 0 term failures, and 29 ids appear under more than one term [#1598/W/snapshot].
- None of the 30 results the `nutrition` term returned is installed locally [#1599/W/snapshot].
- The corpus-wide lint sweep returned 84 findings — 3 ERROR, 30 WARN and 51 INFO — across the 230 mod folders, dated 2026-09-10 13:47 [#1570/C/snapshot].
- Build status eliminates no candidate and only annotates one: all 19 nutrition-signalled mods resolve a version folder the `42.20.4` build reads and none lints ERROR [#1645/C/snapshot].
- The resident Girth stack carries 228 `sendClientCommand`, `OnClientCommand` and `sendServerCommand` sites across its six mods, 96 of them in the quest-system mod, dated 2026-09-10 [#1459/C/snapshot, #1567/C/snapshot].
- The corpus class distribution at that sweep is 175 light-lua systems, 31 other, 15 heavy-lua systems, 5 scripts-only content and 4 `content(3d+lua)` mods [#1552/C/snapshot].
- At the 2026-09-30 05:48 sweep the installed corpus is 182 workshop items holding 234 mod folders, and no live version folder in it references the stat hook [#2559/C/snapshot] [#2558/C/snapshot].

## How it works

<a id="sweep"></a>
### The dated sweeps

The catalog is four sweeps, each stamped with the minute it ran.
Three of them read the installed workshop corpus off disk; one reads public Workshop browse pages.
Every corpus sweep reads the live version folder only — the one folder the running build resolves — so that a mod shipping the same files in three version folders is not counted three times.
Every number below is therefore a reading of shipped files or of a page at a named minute, never a reading of what a mod does in play.
A sweep answers where a thing is and how often it appears; what it means is the reading that follows the table.

The first sweep counts Lua nutrition signals: hits of `getNutrition()`, `setCalories`, `setProteins`, `setLipids`, `setCarbohydrates` or `HungerChange` in any `.lua` file under the live version folder.

Sweep 1 is the Lua nutrition-signal table: 11 rows, one per mod with a `signals.food_nutrition` hit in its live version folder, carrying the hit count and the mod's `lua_kb`, `net`, `mod_data`, `monkey_patch`, `pcall`, sandbox and class columns, at the 2026-09-10 17:47 sweep [#1573/C/snapshot].

| Mod id | Item | Hits | `lua_kb` | net | `mod_data` | `monkey_patch` | `pcall` | Sandbox | Class |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| `simpleStatus` | `2867431511` | 12 | 46 | 0 | 4 | 0 | 0 | no | light-lua |
| `CleanUI` | `3437629766` | 11 | 1064 | 8 | 12 | 3 | 101 | no | heavy-lua |
| `SkillRecoveryJournal` | `2503622437` | 8 | 134 | 23 | 13 | 0 | 2 | yes | heavy-lua |
| `AutoCook` | `3388721641` | 4 | 41 | 0 | 9 | 0 | 0 | no | light-lua |
| `BeyondTen` | `3765241705` | 4 | 170 | 8 | 14 | 12 | 47 | no | light-lua |
| `Economy` | `3624538051` | 4 | 503 | 46 | 9 | 0 | 63 | yes | heavy-lua |
| `SKITTLE_LongTermPreservation4220` | `3774789651` | 4 | 3 | 0 | 0 | 0 | 0 | no | light-lua |
| `SomewhatTraitsCore` | `3498347699` | 3 | 44 | 4 | 0 | 66 | 0 | yes | light-lua |
| `CustomGamepadUI` | `3001154607` | 1 | 35 | 0 | 3 | 11 | 0 | no | light-lua |
| `MoodleFramework` | `3396446795` | 1 | 27 | 0 | 1 | 0 | 0 | no | light-lua |
| `QuestSystem` | `3624538051` | 1 | 718 | 96 | 28 | 12 | 13 | yes | heavy-lua |

`net` is `send_client_cmd` plus `on_client_cmd` plus `send_server_cmd`, and it is a floor, because the inventory carries no signal for `OnServerCommand`.
`monkey_patch` is the save-and-wrap idiom and is a different signal from the `global_write_vanilla` count the API-surface table carries.

Two independent counts of the eleven signalled mods' `food_nutrition` hits — the inventory's regex sweep and a file-by-file count of the same live version folders — agree on every one of the eleven totals [#1577/C/snapshot].

The Sweep 1 sites table is 11 rows, one per signalled mod, naming the side each mod's hits run on and the `file:line` of every `food_nutrition` hit in its live version folder; the sites are a hand reading of those folders rather than a dataset field, at the 2026-09-10 17:47 sweep [#1574/C/snapshot].

| Mod id | Side | Site(s) | What it does there |
|---|---|---|---|
| `simpleStatus` | client | `42.16/media/lua/client/ss.stats.lua:238,280,294,308,381,404-411` | all 12 hits, in one file: `getProteins` / `getCalories` / `getCarbohydrates` / `getLipids` / `getWeight` and the three weight-trend predicates, each wrapped in a `round(…, 1)` for a status bar |
| `CleanUI` | client | `42.19/media/lua/client/ISUI/ISInventoryPaneContextMenu.lua:806,2442,2444,2689,3571,4664,4665`, `…/ISUI/ISInventoryPane.lua:3503,5623`, `…/CleanUI/Vanilla/CleanUI_Vanilla_ISInventoryPane.lua:1111,2810` | 9 of the 11 are `item:getHungerChange()` in inventory tooltips and the eat-portion menu; the two `getNutrition()` hits (`ISInventoryPane.lua:3503`, `CleanUI_Vanilla_ISInventoryPane.lua:1111`) are inside commented-out vanilla lines. Every one of these files is a whole copy of a vanilla UI file |
| `SkillRecoveryJournal` | **shared** | `42.20.1/media/lua/shared/Skill Recovery Journal Main.lua:23,54,55` and `…XP.lua:134,139,140` | `canAddFitnessXp()` gates fitness XP, and `getProteins()` scales the exercise multiplier 1.5 / 1.0 / 0.7. `Main.lua:51` carries an upstream comment marking the `checkProteinLevelMulti` below it as not yet implemented |
| `AutoCook` | client | `42.13/media/lua/client/AutoCook.lua:214,329`, `…_AutoCraftRecipes.lua:39`, `…/ISCharacterCook.lua:71` | `getNutrition():getWeight()` + `isIncWeight` / `isDecWeight` choose whether to add spices, and `getLipids` / `getCarbohydrates` filter which food goes into a recipe; the fourth is `item:getHungerChange() < 0` selecting edible recipe outputs |
| `BeyondTen` | shared | `42/media/lua/shared/BeyondTen/ExtendedBonuses.lua:497-500` | four `{getter, setter}` name pairs in a reflection table, not four calls |
| `Economy` | shared | `42/media/lua/shared/Utilities/ShopkeepItemSerializer.lua:240-243` | the same shape: a serializer field map naming the four macro getters and setters so a shop item survives a round trip |
| `SKITTLE_LongTermPreservation4220` | **server** | `42.20/media/lua/server/recipe_meats.lua:45-48` | `setCarbohydrates` / `setLipids` / `setProteins` / `setCalories`, each `× 0.70`, on the crafted instance. `setHungChange(… × 0.70)` at `:49` is a fifth macro write the regex does not match |
| `SomewhatTraitsCore` | **server** | `42.15/media/lua/server/SWTraitsCore_server.lua:78,84,86` | the corpus's only **player** macro write: an `OnTick` handler gated on the `SWAdaptiveMetabolism` trait adds or subtracts `dayLengthMultiplier × 0.5` calories to hold body weight inside 77–83 kg |
| `CustomGamepadUI` | client | `42/media/lua/client/SWSelectAndStart.lua:57` | inside a commented-out line copied from vanilla — a false positive of the regex, and the honest reading of a 1 |
| `MoodleFramework` | client | `42.20/media/lua/client/MF_ISMoodle.lua:98` | a `print()` debug line that appends `proteins=…` to a moodle-level log |
| `QuestSystem` | shared | `42/media/lua/shared/Utilities/ItemDumpExport.lua:89` | `hungerChange = round4(item:getHungerChange())` in a developer item-dump exporter |

What each signalled mod does with its hits is the reading the count cannot carry, and it is one line per mod.

`simpleStatus`'s 12 nutrition hits are all client-side and all in one file, reading the four macros, the body weight and the three weight-trend predicates, each wrapped in a round to one decimal for a status bar [#1582].
Booted once beside a probe that copied its bar text, those bars equalled the client's own mirrored store rounded to one decimal at every read after a server write, following the client's mirror within one push rather than the server's value ([#2093/M/n=1], [simplestatus.md](simplestatus.md#mp)).
`CleanUI`'s 11 nutrition hits all sit in whole copies of vanilla UI files, and 9 of them are `item:getHungerChange()` in inventory tooltips and the eat-portion menu [#1583].
`SkillRecoveryJournal`'s 8 nutrition hits are in `lua/shared/`, so they run on both the client and the dedicated server: `canAddFitnessXp()` gates fitness XP, and a `getProteins()` ladder of 1.5 / 1.0 / 0.7 for the exercise multiplier is written there but not wired on the live tree, as the next sentence reads [#1584].
A dated re-read of the live `42.20.1/` tree on 2026-10-04 found that multiplier still unwired: `checkProteinLevelMulti` has no caller anywhere in the item and the protein branch of `fetchMultipliers` sits in a block comment, so the mod reads no protein value to scale a grant on either side [#2092/C/snapshot/unverified].
`AutoCook` chooses whether to add spices by reading the player's body weight and the two weight-trend predicates client-side [#1585].
`AutoCook` also filters which food enters a recipe from the player's nutrition client-side and selects edible recipe outputs with `item:getHungerChange() < 0` [#1586].
Long Term Preservation multiplies a crafted instance's four macros by 0.70 from an `OnCooked` script hook that runs in `lua/server/` [#1587].
The same handler pins `offAge` and `offAgeMax` to a non-perishable sentinel of 1 000 000 000 on the crafted instance, which are fields the item-stats packet does not carry ([wire-packets.md](../wire-packets.md#item-stats-packet)) [#1635].
`SomewhatTraitsCore` owns the corpus's only player macro write: an `OnTick` handler in `lua/server/`, gated on the `SWAdaptiveMetabolism` trait, adds or subtracts `dayLengthMultiplier × 0.5` calories to hold body weight inside 77 to 83 kg [#1588].
Measured under a co-boot, that write reaches the server's calorie store a third of a kilocalorie every five seconds below and above the band, and not at all inside it ([#2091/M/n=1], [#2762/M/n=1], [somewhattraitscore.md](somewhattraitscore.md#mp)).
That calorie write sticks because it is on the server; the same code in `lua/client/` would be a no-op with a visible flicker [#1633/C/inference].
`MoodleFramework`'s single nutrition hit is a `print` debug line that appends the player's proteins to a moodle-level log [#1589].
`QuestSystem`'s single nutrition hit is a rounded `getHungerChange` read inside a developer item-dump exporter [#1590].

The same file reading finds three paths in Long Term Preservation's server Lua that nothing shipped reaches.

`AdjustStates` and `AdjustStatesPemmican` are empty function bodies wired into two `craftRecipe` `onCreate` keys [#1669].
`TryMeatLard` and `TryMeatCanned` are referenced by no shipped recipe [#1670].
The live `onTest` `TryMeat` is a no-op guard rather than a dead one: its comment says only meats above a weight of 0.2 while its body returns actual weight greater than 0.0 and passes a non-`Food` input unconditionally [#1672].

The second sweep counts script nutrition definitions: `Calories`, `Carbohydrates`, `Lipids`, `Proteins`, `HungerChange`, `ThirstChange`, `DaysFresh`, `DaysTotallyRotten`, `FoodType` or `EvolvedRecipe` at the start of a line in a `.txt` under the live folder's `media/**/scripts`, read comment-stripped as the engine reads it.

Sweep 2 is the script nutrition-definition table: 9 rows, one per mod writing a nutrition key at the start of a line in a `.txt` under its live `media/**/scripts`, with the key count, the item-block count, the declared modules, the measured vanilla-name collision count and the live folder, at the 2026-09-10 17:47 sweep [#1591/C/snapshot].

| Mod id | Item | Keys | Items | Modules | Collide | Live folder |
|---|---|---:|---:|---|---:|---|
| `SKITTLE_LongTermPreservation4220` | `3774789651` | 117 | 15 | `Skittles` | 0 | `42.20` |
| `Horse` | `3661336777` | 116 | 288 | `Base`, `HorseMod` | **1** | `42` |
| `OCsPacking` | `3626823538` | 76 | 308 | `Base`, `OCP` | 0 | `42.15` |
| `ZVirusVaccine42BETA` | `3615135168` | 36 | 86 | `Base`, `LabBooks`, `LabItems`, `LabItems{`, `LabSounds` | 0 | `42.20` |
| `GirthsTweaks` | `3745960616` | 26 | 14 | `Base`, `GirthsTweaks`, `SDCaches`, `SDFoods`, `SDQuests`, `ST_Tweaks` | 0 | `42` |
| `JadePackingSD` | `3779653231` | 18 | 125 | `Packing` | 0 | `42` |
| `69mini` | `2937786633` | 7 | 32 | `Base` | 0 | `42.13` |
| `SDQuests` | `3745960616` | 6 | 12 | `Base`, `SDQuests` | 0 | `42` |
| `biogas` | `2925657627` | 1 | 1 | `Base`, `Biofuel` | 0 | `42` |

The `Items` column is every `item` definition in those files, clothing and vehicles included, and is not a food count.
Declaring a module is the capability to override, not an override: an override needs a name collision, which is why the table carries a measured collision count beside the module list.

`script_item_blocks` and the parser's own block count are identical on all nine script-signalled mods at 15, 288, 308, 86, 14, 125, 32, 12 and 1, at the 2026-09-10 17:47 sweep [#1596/C/snapshot].
Long Term Preservation's live tree holds 15 item definitions, 14 of them food and the fifteenth `SaltRock` at `ItemType base:normal`, and 117 nutrition key writes when read comment-stripped [#1647/C/snapshot].
The 135 to 117 key delta on that mod is 14 plus 4: a 36-line obsolete comment block contains two whole item definitions carrying 7 keys each, and each of the four two-line commented pairs costs only its `DaysTotallyRotten`, because the key regex anchors to the start of a line and the line above starts with the comment opener [#1648/C/arith.].
Reading comment-stripped rather than raw moves `ZVirusVaccine42BETA` from 102 item blocks to 86, the nine script-signalled mods' total from 899 to 881, and the corpus-wide key total from 6 648 to 6 630, two of that mod's script files being commented out whole [#1649/C/snapshot].

A not-installed row is a page reading and nothing more, so nothing about such a mod's code is readable from here.
The third sweep leaves the disk: it reads browse pages of the public Workshop's `Build 42`-tagged ready-to-use section, one page per term.

Sweep 3 is the public Workshop term table: 8 terms against the `Build 42`-tagged ready-to-use section, one browse page each, with the result count and the installed count per term, fetched 2026-09-10 16:26 [#1597/W/snapshot].

| Term | Results | Installed | Note |
|---|---:|---:|---|
| `nutrition` | 30 | **0** | a full page of third-party nutrition work, and not one item of it is installed here |
| `vitamin` | 30 | 0 | — |
| `malnutrition` | 2 | 0 | the only term that does not fill a page |
| `diet` | 30 | 1 | the hit is a car mod |
| `hydration` | 30 | 2 | a bottle-capacity tweak and BeyondTen |
| `food overhaul` | 30 | 0 | — |
| `cooking overhaul` | 30 | 0 | — |
| `spoilage` | 30 | 0 | — |

The Workshop sweep returned 212 results over 8 terms, collapsing to 180 distinct ids with 3 installed and 0 term failures, and 29 ids appear under more than one term [#1598/W/snapshot].
None of the 30 results the `nutrition` term returned is installed locally [#1599/W/snapshot].

The Sweep 3 load-bearing table is 9 Workshop rows, each with its id, title, installed flag, file size, page update stamp and the reason it is listed, fetched 2026-09-10 16:26; a row's three stat columns are quotable only where its details status reads fetched [#1601/W/snapshot].

| `workshop_id` | Title | Installed | Size | Updated | Why it is here |
|---|---|---|---|---|---|
| `2932547723` | '93 Lincoln Town Car + Limo | yes (`93townCar`) | 14.655 MB | Jul 2 @ 11:40am | matched `diet` on its page text; not a nutrition mod |
| `3759421894` | Big Bottles | yes (`BigBottles`) | 107.238 KB | Aug 1 @ 6:44am | matched `hydration`; a container-capacity tweak, no nutrition signal in the inventory |
| `3765241705` | Beyond Ten - Level 15 Skills [B41/B42] | yes (`BeyondTen`) | 348.184 KB | Sep 4 @ 1:25pm | the only installed hit with a nutrition signal, and its teardown is already done |
| `3736275816` | ApocalipseBR - Nutrition Sync Fix | no | 453.434 KB | May 31 @ 11:18am | **someone else hit the MP nutrition-sync problem this library exists to characterise** and shipped a fix. Subscribing is the only way to read how |
| `3796644824` | [NUTRITION LAUNDERING PATCH + FEATURES] Long Term Preservation | no | 471.224 KB | *never* | **a third-party patch to pick 1**, four days old, claiming the preservation mod launders nutrition — a claim about a mod we *can* read |
| `3690404044` | Nutrition Makes Sense | no | 1.042 MB | Aug 18 @ 5:01pm | the largest nutrition overhaul on the page, and the one with an add-on ecosystem |
| `3785515388` | Reasonable Nutrition | no | 145.008 KB | Aug 26 @ 3:49pm | the cheapest comparison read if only one of these is ever subscribed |
| `3782835400` | Realistic Nutrition | no | 636.708 KB | *never* | third of the three same-month nutrition overhauls |
| `3078272807` | Nutrition Tweaker Enhanced | no | 503.836 KB | Jul 22, 2025 @ 1:35pm | the B41-era ancestor still carrying the `Build 42` tag |

Workshop item `3736275816`, ApocalipseBR - Nutrition Sync Fix, is a 453.434 KB not-installed mod shipping a fix for the multiplayer nutrition-sync problem this library exists to characterise [#1605/W/snapshot].
Workshop item `3796644824`, a 471.224 KB not-installed patch to Long Term Preservation, claims the preservation mod launders nutrition — a claim about a mod that is installed and readable here [#1606/W/snapshot].
Three of the sweep's 180 distinct ids are installed locally: `2932547723` '93 Lincoln Town Car matched `diet` and is a car mod, `3759421894` Big Bottles matched `hydration` and is a container-capacity tweak with no nutrition signal, and `3765241705` BeyondTen is the only installed hit carrying one [#1607/C/snapshot].

#### The 2026-09-30 sweep

A fourth sweep re-reads the installed tree with the same live-folder scope and adds a surface census: for each vanilla surface a mod hooks, wraps or writes, the count of pattern hits in its live version folder and the first site.
A surface a mod ships only under `common/media` reads as absent in that census, so every such site on this page is cited from its file and never counted.
The census is a count of pattern hits and never a reading of behaviour; each sentence that names a hit was read off the file it names.

The installed corpus at the 2026-09-30 05:48 sweep is 182 workshop items holding 234 mod folders, against 179 and 230 at the 2026-09-10 17:47 sweep: four mods are new, named by mod id (`QualityCooking`, `NewMusic` in the folder `Talis New Music`, `SDMusic`, `SDMixtape`), none is gone, and four mods now resolve a `42.20` live folder (`isoContainers`, `simpleStatus`, `KI5campers`, `70chevelle`) [#2559/C/snapshot].
Workshop item `3624538051` holds six mod folders at the 2026-09-30 05:48 sweep — `BaseQuests`, `Economy`, `ItemQuality`, `QualityCooking`, `QualityEnhancements` and `QuestSystem` — and `QualityCooking` is the one absent at the 2026-09-10 17:47 sweep [#2560/C/snapshot].
`simpleStatus` resolves `42.20` as its live folder at the 2026-09-30 05:48 sweep, reading its `mod.info` from `42.20/mod.info`, so a line cite into its `42.16` tree names a folder the build no longer runs [#2561/C/snapshot].

<a id="status"></a>
### Build status per candidate

Build status answers one question per catalogued mod: which folder the running build resolves, where its `mod.info` sits, whether it lints clean, whether its declared dependencies are installed, and when its files and its Workshop page were last written.
The two stamps are different questions, and neither substitutes for the other: the folder stamp is a download, the page stamp is an update.
Nothing in this section was booted: each row pairs the mod's own tree, read off disk, with its Workshop item page, read at a named minute.

`tools/workshop_search.py --catalog-ids` read the nine catalogued mods' Workshop item pages directly in one pass, 9 fetched and 0 failed, on 2026-09-10 17:46 [#1610/W/snapshot].

The build-status table is 9 rows, one per catalogued mod, carrying its version folders, live folder, `mod.info` location, lint error, warn and info counts, declared dependencies and whether they are installed, folder bytes, download stamp and Workshop update stamp, at the 2026-09-10 17:47 sweep [#1609/C/snapshot].

| Mod id | Version folders | Live | `mod.info` at | Lint E/W/I | Deps | Deps installed | Bytes | Download stamp | Workshop updated |
|---|---|---|---|---|---|---|---:|---|---|
| `SKITTLE_LongTermPreservation4220` | `42.20` | `42.20` | `42.20/mod.info` | 0/0/1 | none | n/a | 239 131 | 2026-09-01 13:13 | **never** (posted Jul 30 @ 6:31pm) |
| `simpleStatus` | `42.16`, `42.15`, `42.14`, `42` | `42.16` | `42.16/mod.info` | 0/0/1 | none | n/a | 1 132 005 | 2026-08-12 00:03 | Apr 5 @ 5:37pm |
| `AutoCook` | `42.13`, `42` (+ `common/`) | `42.13` | **`common/mod.info`** | **0/1/0** | none | n/a | 129 161 | 2026-08-12 00:03 | Sep 6 @ 9:04pm |
| `SkillRecoveryJournal` | `42.20.1`, `42.19` | `42.20.1` | `42.20.1/mod.info` | 0/0/1 | `ChuckleberryFinnAlertSystem`, `errorMagnifier` | **both** (`3077900375`, `2896041179`) | 4 460 232 | 2026-08-12 00:03 | Sep 4 @ 8:57am |
| `MoodleFramework` | `42.20`, `42.13`, `42.0` (+ `common/`) | `42.20` | **`42.0/mod.info`** | **0/1/0** | none | n/a | 180 592 | 2026-08-12 00:03 | Sep 7 @ 5:15am |
| `SomewhatTraitsCore` | `42.15`, `42.13`, `42.12` | `42.15` | `42.15/mod.info` | 0/0/0 | none | n/a | 277 350 | 2026-08-12 00:03 | Aug 10 @ 3:03am (item: 3 mods) |
| `CleanUI` | `42.19` … `42.12` (6) | `42.19` | `42.19/mod.info` | 0/0/0 | `NeatUI_Framework` | **yes** (`3508537032`) | 11 300 184 | 2026-08-17 13:37 | Sep 7 @ 5:57am |
| `Economy` | `42` | `42` | `42/mod.info` | 0/0/0 across the item's **5** mods | `QuestSystem` | **yes** (same item) | 600 070 | 2026-08-12 00:03 | Sep 10 @ 4:53am (item: 5 mods) |
| `BeyondTen` | `42` | `42` | `42/mod.info` | 0/0/0 | none | n/a | 348 184 | 2026-08-12 00:03 | Sep 4 @ 1:25pm (read twice) |

The download stamp and the Workshop update stamp disagree in both directions: `3774789651` has never been updated since it was posted while its item folder was written 2026-09-01, and `3624538051` was updated on its page at 4:53am on the day of the read while its item folder still said 2026-08-12 [#1611/C/snapshot].
The Workshop page's File Size equalled the sum of bytes over the item's mod folders on all nine catalogued mods to the byte, including item `3498347699` at 1 737 473 bytes and item `3624538051` at 3 641 208, the two that ship several mods, whose page title and size are the item's rather than the named mod's [#1612/C/snapshot].

Three of the nine rows carry a layout finding rather than a clean bill.

`AutoCook`'s `mod.info` sits in `common/` rather than in the newest version folder `42.13/` that the build runs, which is one of the 6 corpus-wide mod-info-place warnings [#1613/C/snapshot].
`MoodleFramework`'s `mod.info` sits in its oldest folder `42.0/`, and its newest folder `42.20/media` ships exactly one file, `lua/client/MF_ISMoodle.lua`, while `MF_Config.lua` exists only in `42.0/media` and `common/media` [#1614].
MoodleFramework is whole on `42.20.4` under the same merge rule: it ships `MF_ISMoodle.lua` in `42.0/`, `42.13/`, `42.20/` and `common/` but `MF_Config.lua` in `42.0/` and `common/` only, so pass B overwrites only the moodle file and the config file, having no version-dir counterpart, survives and executes [#1319/C/snapshot].

Two more rows turn on identity rather than layout.

Long Term Preservation declares the id `SKITTLE_LongTermPreservation4220`, not its folder name `LongTermPreservation4220` [#1557].
`SKITTLE_LongTermPreservation4220` is the only nutrition candidate whose only version folder is `42.20`, with `media_at` reading `42.20/media` alone and no `common/`, and `Economy` is the only other mod on the catalog with an unambiguous live tree at `42/media` alone [#1615/C/snapshot].
Workshop item `3624538051` carries 5 mod folders at the 2026-09-10 sweep — the quest system, the economy, the base quests, the item quality module and a quality-enhancements module — rather than the four an older reading names [#1543/C/snapshot].

The teardown-readiness table is 6 rows, one per profilable candidate, carrying its `media_at` zero-guard, whether a profile can run it today and the one thing a probe must settle about it, at the 2026-09-10 17:47 sweep [#1616/C/snapshot].

| Mod id | `media_at` (the zero-guard) | Profilable today | The one thing a probe must settle |
|---|---|---|---|
| `SKITTLE_LongTermPreservation4220` | `42.20/media` only — **no `common/media`, so its zeros are trustworthy** | yes | does the ×0.70 on a crafted instance reach the client, and through which packet |
| `simpleStatus` | `42.14`, `42.15`, `42.16`, `42`, and a B41 root `media` — **no `common/media`** | yes | what the client's mirror shows against the server's store at the moment of a write |
| `AutoCook` | `42.13/media` **and `common/media`** — every zero on this row is suspect | yes, but the copy must carry `common/` | whether the live folder alone is a working mod at all |
| `SkillRecoveryJournal` | `42.19`, `42.20.1`, `common/media`, and a B41 root `media` | yes | its `sendClientCommand` / `OnClientCommand` bus under a second client |
| `MoodleFramework` | `42.0`, `42.13`, `42.20`, `common/media` | yes | whether `MF_Config` is present at runtime on `42.20.4` |
| `SomewhatTraitsCore` | `42.12`, `42.13`, `42.15`, and a B41 root `media` | yes — but the item ships **3** mods, so a profile must name the `id` | whether an `OnTick` server-side calorie write survives the 1 Hz push |

`AutoCook` is profilable only if the copy the harness makes carries `common/`, because every zero on its record is suspect while its `media_at` names both `42.13/media` and `common/media` [#1618/C/snapshot].
`simpleStatus` initialises in `OnCreatePlayer` and ships no server-side counterpart, so by construction it cannot be authoritative about anything [#1619].
`simpleStatus` can only ever draw the server's mirror, so its bars are correct to within one push and cannot be more correct than that ([wire-packets.md](../wire-packets.md#staircase)) [#1634/C/inference].
`AutoCook`'s client-side recipe filter can read a stale number, because a zero-valued item-stats field is written only when non-zero while the receiver applies it unconditionally from one cached packet per type [#1636/C/inference].

Build status never eliminates a candidate and only annotates one: all 19 nutrition-signalled mods resolve a version folder the `42.20.4` build reads and none lints ERROR [#1645/C/snapshot].

Three mods carry the catalog's teardown picks, and the reasons are readings of their records rather than preferences.
Each pick is a mod that writes or reads state the server owns, small enough to be read whole, and installed, which is what makes it measurable at all.

Teardown pick 1 is `SKITTLE_LongTermPreservation4220`, the domain twin: 15 live `module Skittles` item blocks with 14 of them food carrying a full macro set, plus a server-side `OnCooked` hook that multiplies all four macros and `HungerChange` by 0.70 on the crafted instance, in a 239 KB mod with no dependencies and a 0/0/1 lint [#1641/C/snapshot].
Teardown pick 2 is `simpleStatus`, the read side: 12 nutrition reads in one client file, 47 803 bytes over 7 files, one `transmitModData` call and one `ISPanel` derive, on a newest folder of `42.16` whose live tree has dropped the `lua/server/` file older folders carry and is 100 per cent client [#1642/C/snapshot].
Teardown pick 3 is `AutoCook`, the cooking-pipeline hook points: client-side nutrition reads that choose spices and filter ingredients, 9 `getModData` settings it never transmits, and a live version folder that ships no event registration and two unresolvable requires [#1643/C/snapshot].
A pure content mod scores zero on multiplayer behaviour worth measuring, which is what removes the eight script-only mods from the picks: `OCsPacking` is the sharpest case at 308 item blocks, 76 nutrition keys and 5 KB of Lua in a 230 KB folder, well inside a two-hour teardown, and is still out [#1644/C/inference].

#### The public Workshop on 2026-09-30

One catalog pass read the Workshop item pages below ([datasets.md](../../reference/datasets.md#workshop-rows)) [#2594/W/snapshot].
By their titles, the first group below is nutrition mods and the second is stat libraries, a trait system and a tooltip framework.
Each sentence below carries only what an item page holds — a title, a file size and two stamps quoted as the page writes them, the year omitted for the current one — and nothing about what the mod's code does.
The laundering patch to Long Term Preservation keeps its earlier dated page reading [#1606/W/snapshot].

Workshop item `3690404044`, `Nutrition Makes Sense [2.0]`, is 883.676 KB, posted `22 Mar @ 4:57pm` and updated `26 Sep @ 9:09am`, at the 2026-09-30 14:10 fetch [#2585/W/snapshot].
Workshop item `3785515388`, Reasonable Nutrition, is 145.008 KB, posted `17 Aug @ 7:44pm` and updated `26 Aug @ 3:49pm`, at the 2026-09-30 14:10 fetch [#2586/W/snapshot].
Workshop item `3782835400`, Realistic Nutrition, is 636.708 KB, posted `13 Aug @ 10:59am` and never updated, at the 2026-09-30 14:10 fetch [#2587/W/snapshot].
Workshop item `3078272807`, Nutrition Tweaker Enhanced, is 503.836 KB, posted `10 Nov, 2023 @ 2:19am` and updated `22 Jul, 2025 @ 1:35pm`, at the 2026-09-30 14:10 fetch [#2588/W/snapshot].
Workshop item `3736275816`, ApocalipseBR - Nutrition Sync Fix, is 453.434 KB, posted `31 May @ 7:55am` and updated `31 May @ 11:18am` at the 2026-09-30 14:10 fetch, and its page states — quoted faithful in substance, not byte-exact — that a client's calorie counter overwrites the server's on each eat, so players only gain weight [#2589/W/snapshot].
That stated mechanism is contradicted by the measured client write, which never reaches the server and is erased by the next player stats packet [#0119/M/n=1] [#0568/M/n=2], and public threads report the multiplayer weight drift in both directions on different builds [#2589/W/snapshot].
Workshop item `2997722072`, StatsAPI, is 133.814 KB, posted `2 Jul, 2023 @ 1:13am` and updated `18 Nov, 2024 @ 3:29pm`, at the 2026-09-30 14:11 fetch [#2590/W/snapshot].
Workshop item `3415375593`, Stat Tweaks Lib, is 87.724 KB, posted `26 Jan, 2025 @ 2:42pm` and updated `1 Feb, 2025 @ 6:55am`, at the 2026-09-30 14:11 fetch [#2591/W/snapshot].
Workshop item `2914075159`, Evolving Traits World (ETW) + More Traits continuation, is 7.285 MB, posted `7 Jan, 2023 @ 12:53am` and updated `28 Sep @ 9:17am`, at the 2026-09-30 14:11 fetch [#2592/W/snapshot].
Workshop item `3694097672`, Tooltiplib - Tooltip Framework for Modders, is 375.475 KB, posted `28 Mar @ 7:40am` and updated `26 Aug @ 4:40am`, at the 2026-09-30 14:11 fetch [#2593/W/snapshot].

<a id="api-surface"></a>
### The API surface the corpus uses

The API surface is one row per API class and candidate: what the mod reaches for, how many sites the inventory counts, and one real use read by hand out of the live version folder.
The counts and the citations come from two different readings on purpose, so a signal name that overstates what it matches is visible in the row beside it.
A count here names a signal rather than a capability, and the citation beside it is what decides which of the two a row supports.
Where a mod's live folder is not its whole tree, the row says so instead of reporting the absence as a zero.

The API surface table is 24 rows, one per API class and candidate pair, each carrying the inventory's signal count and the `file:line` of one real use in the mod's live version folder, at the 2026-09-10 17:47 sweep [#1621/C/snapshot].

| API class | Mod id | Count | One real use |
|---|---|---:|---|
| `Events.<X>.Add` | `SomewhatTraitsCore` | 37 (`OnTick` 24, `OnPlayerUpdate` 6) | `42.15/media/lua/server/SWTraitsCore_server.lua:89` `Events.OnTick.Add(SWAdaptiveMetabolism)` |
| `Events.<X>.Add` | `SkillRecoveryJournal` | 15 (`OnServerCommand` 3, `OnClientCommand` 2, `OnGameBoot` 2) | `42.20.1/media/lua/client/Skill Recovery Journal Client Events.lua:111` |
| `Events.<X>.Add` | `CleanUI` | 18 (`OnTick` 5, `OnGameBoot` 5, `OnGameStart` 5) | client only, all 18 |
| `Events.<X>.Add` | `simpleStatus` | 2 (`OnCreatePlayer`, `OnKeyPressed`) | `42.16/media/lua/client/ss.main.lua:82` `Events.OnCreatePlayer.Add(onCreatePlayer)` |
| `Events.<X>.Add` | `SKITTLE_LongTermPreservation4220` | 1 (`onAddForageDefs`) | `42.20/media/lua/shared/Foraging/forageable_items.lua:28` — its whole Lua event surface |
| `Events.<X>.Add` | `AutoCook` | **0 in the live folder** | the only registration, `Events.OnPreFillInventoryObjectContextMenu.Add`, is `common/media/lua/client/AutoCook_RISCookMenuInsertion.lua:117` — a file `42.13/` does not ship |
| `sendClientCommand` | `SkillRecoveryJournal` | 5 | `42.20.1/media/lua/client/Skill Recovery Journal Context.lua:138` |
| `sendClientCommand` | `SomewhatTraitsCore` | 3 | `42.15/media/lua/client/SWTraitsCore_client.lua:61` |
| `sendClientCommand` | `CleanUI` | 8 | `42.19/media/lua/client/ISUI/ISInventoryPane.lua:3069` — vanilla's own `'object'` module, carried over in a copied file |
| `OnClientCommand` | `SomewhatTraitsCore` | 1 | `42.15/media/lua/server/SWTraitsCore_server.lua:497` |
| `OnClientCommand` / `sendServerCommand` | `SkillRecoveryJournal` | 9 / 9 (plus 3 `OnServerCommand`, which the inventory has no signal for) | `42.20.1/media/lua/client/Skill Recovery Journal Admin Panel.lua:446` `Events.OnServerCommand.Add(onServerCommand)` — the client half of its own bus |
| `sendServerCommand` | `simpleStatus`, `AutoCook`, `SKITTLE_LongTermPreservation4220` | **0** | none of the three picks has a command bus of any kind |
| `getModData` | `AutoCook` | 9 | `42.13/media/lua/client/AutoCook.lua:35` and `…/ISCharacterCook.lua:238,258,339` — settings persisted per player |
| `getModData` | `simpleStatus` | 4 | `42.16/media/lua/client/ss.main.lua:59`, `…/ISSSBar.lua:33` |
| `transmitModData` | `simpleStatus` | **1** | `42.16/media/lua/client/ISSSBar.lua:35`, immediately after writing `md["SimpleStatusConfig"]` at `:34` — the only `transmitModData` among the three picks |
| `transmitModData` | `AutoCook`, `SKITTLE_LongTermPreservation4220` | 0 | AutoCook writes player modData on the client and never transmits it |
| monkey-patching (`global_write_vanilla`) | `CleanUI` | 287 | `42.19/media/lua/client/ISUI/InventoryWindow/ISInventoryWindowContainerControls.lua:24` — CleanUI ships whole *copies* of vanilla UI files, so the count is a file-replacement count |
| monkey-patching (`global_write_vanilla`) | `SomewhatTraitsCore` | 56 `function IS…:` + 66 `monkey_patch` | `42.15/media/lua/client/SWTraitsCoreOverrides_client.lua:8-9` — `local original_ISMedicalCheckAction = ISMedicalCheckAction.new` then `function ISMedicalCheckAction:new(...)`; the save-and-wrap idiom done 66 times |
| monkey-patching (`global_write_vanilla`) | `AutoCook` | 21 (`monkey_patch` 0) | **all 21 are `function ISCharacterCook:…` in `42.13/media/lua/client/ISCharacterCook.lua`, and `ISCharacterCook` is AutoCook's own class** — no such name exists in the game's `media/lua`. The signal name overstates it: this is a new `ISPanelJoypad` subclass, not 21 vanilla overrides |
| item / recipe script overrides | `SKITTLE_LongTermPreservation4220` | 15 live item blocks (= `script_item_blocks`), **8** `craftRecipe` blocks | `42.20/media/scripts/items/items_dried.txt:8` `item CuredPork` inside `module Skittles`; `42.20/media/scripts/recipes/recipe_cured.txt:8` `craftRecipe MakeCuredMeat` |
| item / recipe script overrides | `simpleStatus`, `AutoCook` | **0 script files** | neither ships a `scripts/` folder in any folder; they cannot change an item definition |
| script → Lua hooks | `SKITTLE_LongTermPreservation4220` | **12** `OnCooked`, 2 Lua `onCreate`, 1 `onTest`, plus 2 Java `RecipeCodeOnCreate` | `items_dried.txt:22` `OnCooked = OnCookedTest` (4 items) and `:160` `OnCooked = CannedFood_OnCooked` (8 items); `recipe_cured.txt:12-13` `onCreate = AdjustStates`, `onTest = TryMeat`; `:78` `OnCreate = RecipeCodeOnCreate.makeJar` and `:110` `…applyLidCondition` are the Java pair |
| sandbox options | `SkillRecoveryJournal` | 30 `SandboxVars.` reads, `sandbox-options.txt` present | `42.20.1/media/lua/client/Skill Recovery Journal SkillProgressBar.lua:26` |
| sandbox options | `SomewhatTraitsCore`, `Economy`, `QuestSystem` | present | the three picks ship **none** — nothing to configure, and nothing to mis-configure in a profile |

`AutoCook` registers no event at all in its live version folder: its only registration, an `OnPreFillInventoryObjectContextMenu` handler, is in a `common/` file that `42.13/` does not ship [#1622].
`AutoCook`'s real vanilla-facing patch lives in `common/media/lua/client/ISCharacterInfoWindow_AddTab.lua`, outside the scanned live version folder [#1653].
`AutoCook`'s 21 `global_write_vanilla` hits are all `function ISCharacterCook:…` definitions in the mod's own new `ISPanelJoypad` subclass, a name that exists nowhere in the game's `media/lua`, so the signal name overstates them as vanilla overrides [#1623/C/snapshot].
`SomewhatTraitsCore` carries both patching signals: 56 `function IS…:` headers and 66 save-and-wrap `monkey_patch` sites [#1624/C/snapshot].
None of the three teardown picks has a command bus of any kind: `sendServerCommand` is 0 for `simpleStatus`, `AutoCook` and `SKITTLE_LongTermPreservation4220`, at the 2026-09-10 17:47 sweep [#1625/C/snapshot].
`simpleStatus` is the only one of the three picks that calls `transmitModData`, and it does so immediately after writing its config key into player modData [#1626].
`AutoCook` keeps 9 `getModData` settings per player on the client and never transmits them, so its per-player settings live only on the client that set them [#1627/C/snapshot].
Long Term Preservation ships 15 live item blocks and 8 `craftRecipe` blocks [#1628/C/snapshot].
Its script-to-Lua hook surface is 12 `OnCooked` keys, 2 Lua `onCreate` keys, 1 `onTest` key and 2 Java `RecipeCodeOnCreate` keys [#1629].
`simpleStatus` and `AutoCook` ship no `scripts/` folder in any version folder, so neither can change an item definition [#1630/C/snapshot].
The three teardown picks ship no sandbox options at all, while `SkillRecoveryJournal` has 30 `SandboxVars` reads and a `sandbox-options.txt` [#1631/C/snapshot].

#### The surface census at the 2026-09-30 sweep

The census turns the API surface around: instead of asking what one candidate reaches for, it asks which mods reach each surface a nutrition mod must share.
Each line below is a census count with its stamp, and where the count names a site, the site was read off its file.

No `.lua` file in the live version folders of the 234 installed mod folders references `CalculateStats`, `Hook.CalculateStats`, `LuaHookManager` or `TriggerHook`, and the only `Hook.<name>.Add` or `.Remove` call in them is CleanUI's pair on `Hook.AutoDrink`, carried over from vanilla's context menu, at the 2026-09-30 05:48 sweep [#2558/C/snapshot].

Three mods hit the `ISEatFoodAction` method surface in the live version folders at the 2026-09-30 05:48 sweep and all three wrap it — `QualityCooking` (`complete` and `eat`, server), `EmergencyVomitB42` (`start`, `complete` and `eat`, client) and `SomewhatTraitsCore` (`getDuration`, shared) — and `EmergencyVomitB42`'s wraps alone sit behind an idempotency sentinel, a flag stored on the action class and tested before it redefines anything [#2566/C/snapshot].
No live version folder names `ISEatFoodAction.serverStop`, `ISEatFoodAction.isValid` or `updateEat` at the 2026-09-30 05:48 sweep: the eat-method and drink surfaces match those names, and every hit on them reads another method or the action's class name [#2567/C/snapshot].
The carry setters `setMaxWeightBase` and `setMaxWeightDelta` have 2 hits in the live version folders at the 2026-09-30 05:48 sweep, both `QualityCooking`'s `setMaxWeightBase` in its minute ticker, the second restoring a cached pre-buff base on expiry, so `setMaxWeightDelta` has none [#2565/C/snapshot].

`ISToolTipInv:render` is wrapped in five mods' live version folders at the 2026-09-30 05:48 sweep — `SkillRecoveryJournal`, `KATTAJ1_ClothesCore`, `ItemQuality`, `QuestSystem` and `GirthsTweaks`, the last in two files — and by `sd-teleporter` from `common/media`, each a save-and-replace with no idempotency sentinel, and `SkillRecoveryJournal`'s journal-tooltip path calls its own forked copy of vanilla's render instead of the saved chain [#2568/C/snapshot].
No live version folder references `ISCharacterInfoWindow` or `ISLayoutManager.RegisterWindow` at the 2026-09-30 05:48 sweep; `AutoCook` wraps the window's `createChildren`, `onTabTornOff` and `SaveLayout` and calls `RegisterWindow` on a `charinfowindow.<tab>` name from a `common/media` file, and vanilla's character info window registers six `charinfowindow` layout names in one file [#2569/C/snapshot].

Four mods' live version folders hit `sendSyncPlayerFields`, `syncPlayerStats` or `syncBodyPart` at the 2026-09-30 05:48 sweep, and the two `sendSyncPlayerFields` hits are `SkillRecoveryJournal`'s, sending bit `0x00000001` behind an `isServer()` test and a member nil-check, while vanilla's own Lua sends `0x00000001`, `0x00000007` and `0x00000010` [#2575/C/snapshot].
No live version folder calls `applyTraitFromWeight` or any `getNutrition():set` method at the 2026-09-30 05:48 sweep: the five mods hitting that trait surface all hit it on a `CharacterTrait` constant [#2570/C/snapshot].

39 mods' live version folders ship a `sandbox-options.txt` declaring prefixed options at the 2026-09-30 05:48 sweep, carrying 29 distinct option prefixes, `NR` not among them, and `GirthsTweaks` declares two prefixes (`GirthsTweaks` and `MPSleep`) in one file [#2576/C/snapshot].
`QualityCooking` scales its buffs by the vanilla `SandboxVars.StatsDecrease` and `SandboxVars.EndRegen` options, and `GirthsTweaks` branches its multiplayer sleep on the vanilla `SandboxVars.DayLength` [#2577/C/snapshot].
`SDQuests` declares `OnEat = SDQBoneHurtingJuice_OnEat` on an item in its live scripts, and the target is a bare global function in a `lua/shared/` file [#2579/C/snapshot].

<a id="corpus-facts"></a>
### Corpus-level facts

The corpus facts are the counts that hold over the whole installed set rather than over one mod.
They are what a design reads to learn what the server's approved modlist already does, what it never does, and where a zero in the dataset means absence rather than an unread folder.
Every one of them is dated, because the workshop tree is live and Steam rewrites a mod folder underneath a sweep.
Several of them are floors rather than totals, because the signal behind them is narrower than the question, and the sentence says so wherever that bites.
They are grouped here as the shape of the corpus, then its nutrition surface, then its script conventions, then its discipline, and last its size and its hooks.

The locally installed workshop corpus is 179 workshop items holding 230 mod folders, 229 of which declare an id the engine can index; `3782784855/Skill Recovery Journal` ships no `mod.info` anywhere and is invisible to the workshop index, at the 2026-09-10 17:47 sweep [#1551/C/snapshot].
The corpus class distribution at the 2026-09-10 17:47 sweep is 175 light-lua systems, 31 other, 15 heavy-lua systems, 5 scripts-only content and 4 `content(3d+lua)` mods [#1552/C/snapshot].
24 of the 31 other-class mods have no `media/` under the live version folder at all, so nothing was scanned rather than nothing shipped; all 24 ship a `common/media` and 12 of them also ship a `B41` root `media/` [#1553/C/snapshot].
`STA_PryOpen` ships `42.18/media` and `42.19/media` beside a live `42.20/` folder that holds none [#1554/C/snapshot].
177 of the 230 corpus rows ship a `common/media` [#1559/C/snapshot].
Every `common/media` in the corpus was swept twice on 2026-09-10 for the ten script-nutrition keys and not one carries a single key, so no nutrition candidate is hidden by the live-folder scope, though the scope still bites on architecture, where AutoCook's entry points are in `common/` and nowhere else [#1561/C/snapshot].
`3041122351/63Type2Van` writes its 7 nutrition keys only in a `B41` flat root `media/` the `42.20.4` build never reads, so its `B42` script signal is 0 and its `B41` signal is 7 [#1563/C/snapshot].

19 of the 230 installed mod folders touch the nutrition surface at the 2026-09-10 17:47 sweep: 11 call a nutrition API from Lua and 9 write a nutrition key in a shipped script, with exactly one mod on both lists [#1555/C/snapshot].
Of the 53 Lua nutrition hits across the corpus, 6 are writes, 8 are a getter or setter name in a reflection table rather than a call (BeyondTen 4, Economy 4), 3 sit inside comments (CleanUI 2, CustomGamepadUI 1) and the remaining 36 are live reads [#1579/C/snapshot].
Long Term Preservation's `setHungChange(... x 0.70)` is a seventh macro write in the corpus that the `food_nutrition` regex does not match at all [#1580].
Only two mods in the whole corpus write a nutrition macro and they write it on different objects — `SomewhatTraitsCore` on the player, Long Term Preservation on an item — so nine of the eleven Lua-signalled mods never write a macro at all [#1581/C/snapshot].

Seven of the nine script-signalled mods declare `module Base` at the 2026-09-10 17:47 sweep, only two of the seven define an item under it (`Horse` 1, `69mini` 32) and exactly one of those collides with a vanilla item name: `Horse` redefines `Base.Rope` [#1594/C/snapshot].
On `42.20.4` the installed corpus contains no vanilla food override at all: every nutrition-bearing script block in it adds a new item [#1595/C/snapshot].
There is one item-name collision across the 230-mod installed corpus, so a `module Base` redefinition pass has no corpus precedent ([../../platform/loader-and-scripts.md](../../platform/loader-and-scripts.md#per-key-merge)) [#1229/C/snapshot].

No mod in the 230-mod installed corpus uses `loadstring` at the 2026-09-10 17:47 sweep, and the whole corpus survived the `42.20.x` security purge intact [#1222/C/snapshot, #1565/C/snapshot].
No corpus row's layout is a flat `B41` one: all 230 resolve a `42[.x[.y]]/` or `common/` folder, while 153 rows still ship a bare root `media/` beside their live version folder that the scan does not read [#1566/C/snapshot].
51 installed workshop folders whose name differs from the declared id load anyway, measured on the dedicated-server path at the 2026-09-11 reading [#1221/M/snapshot].
154 installed mods declare `versionMin` and 13 declare `versionMax`, at the 2026-09-11 reading [#1223/C/snapshot].

The six resident mods of the Girth stack — `QuestSystem`, `Economy`, `BaseQuests`, `SDQuests`, `GirthsTweaks` and `ItemQuality` — carry 228 `sendClientCommand`, `OnClientCommand` and `sendServerCommand` sites between them, 96 of them in `QuestSystem` alone, dated 2026-09-10 [#1459/C/snapshot, #1567/C/snapshot].
CleanUI's live tree ships 54 Lua files — 51 under its client directory and 3 under its shared one — of which 33 sit at the same relative path as a vanilla Lua file and are therefore replacements [#1457/C/snapshot].

The corpus event census, dated 2026-09-10, reads `OnGameStart` 70 hooks over 25 mods, `OnTick` 70/15, `OnPlayerUpdate` 55/39, `OnClientCommand` 54/20, `OnServerCommand` 43/14, `OnGameBoot` 38/16, `OnInitGlobalModData` 33/14, `OnFillWorldObjectContextMenu` 28/12, `OnFillInventoryObjectContextMenu` 23/14, `EveryOneMinute` 22/10, `OnCreatePlayer` 17/14 and `OnServerStarted` 11/6, a floor rather than a total because it is summed over each record's top eight events [#1568/C/snapshot].

The heavy-lua landscape list ranks the corpus's 14 largest Lua mods by `lua_kb` at the 2026-09-10 sweep, from KnoxBuildworks at 1 389 KB down to BeyondTen at 170 KB, with each row's `net`, `mod_data`, `patch` or `pcall` count beside it [#1569/C/snapshot].

| Mod id | `lua_kb` | The signal that characterises it |
|---|---:|---|
| `KnoxBuildworks` | 1389 | `mod_data` 66 — definition-driven JSON architecture, already deeply known |
| `CleanUI` | 1064 | `pcall` 101 |
| `QuestSystem` | 718 | `net` 96 |
| `Economy` | 503 | `net` 46, `pcall` 63 |
| `Horse` | 476 | `patch` 22 — wrapper-heavy; `mod_id` is `Horse`, folder `HorseMod` |
| `BaseQuests` | 423 | pure lua-table content, zero API calls — the data-as-lua pattern |
| `GirthsTweaks` | 280 | `net` 45 |
| `ZVirusVaccine42BETA` | 240 | — |
| `ElyonLib` | 211 | — |
| `QualityEnhancements` | 201 | — |
| `damnlib` | 185 | — |
| `SDQuests` | 181 | — |
| `VVR` | 171 | — |
| `BeyondTen` | 170 | `pcall` 47 |

`net` in that table is `sendClientCommand` plus `OnClientCommand` plus `sendServerCommand` sites.

The corpus-wide mod-lint sweep returned 84 findings — 3 ERROR, 30 WARN and 51 INFO — across the 230 mod folders, dated 2026-09-10 13:47 and reproduced twice the same day [#1570/C/snapshot].

#### The corpus at the 2026-09-30 sweep

The newest resident, `QualityCooking`, sits on the eat seat, the stat writes and the carry base at once, and every one of its sites is a server file.

`QualityCooking` wraps both `ISEatFoodAction.complete` and `ISEatFoodAction.eat` in a `lua/server/` file, each by saving the original into a local and redefining the method unconditionally, with no idempotency sentinel [#2562/C/snapshot].
Inside that eat wrap `QualityCooking` reads the eaten food's four macros (`BuffMath.Macros(food, fraction)`) to allocate its buff points, so it consumes every value a vanilla-food re-base moves [#2563/C/snapshot].
Its `EveryOneMinute` handler, registered in a `lua/server/` file behind a not-`isClient()` test, adds to `CharacterStat.ENDURANCE`, `FATIGUE` and `HUNGER` through `stats:add` scaled by `ZomboidGlobals.ImobileEnduranceIncrease`, `FatigueIncrease` and `HungerIncrease`, and its live folder carries 10 `stat_write` surface hits at the 2026-09-30 05:48 sweep [#2564/C/snapshot].

`SomewhatTraitsCore`'s live `42.15` folder carries 34 `stat_write` surface hits at the 2026-09-30 05:48 sweep, every one in its server file, where `stats:add` and `stats:remove` write endurance, fatigue, stress, unhappiness, boredom and intoxication, and the same file writes player calories through `nutrition:setCalories` [#2582/C/snapshot].
Its shadowed `42.12` folder, which the build does not run, ships a larger client implementation writing `setPanic`, `setBoredomLevel`, `setUnhappynessLevel` and `setPanicReductionValue(0.0)` [#2583/C/snapshot].
`GirthsTweaks` sets `CharacterStat.FATIGUE` to zero on its multiplayer sleep path and later restores fatigue and endurance absolutely from values stashed in player modData, in a `lua/server/` file [#2584/C/snapshot].

Five mods' live version folders name `CharacterTrait.NIGHT_VISION`, `SHORT_SIGHTED`, `EAGLE_EYED`, `KEEN_HEARING` or `INSOMNIAC` at the 2026-09-30 05:48 sweep, and the only runtime trait add or remove among those hits is `GirthsTweaks` removing `INSOMNIAC` from a player in a server file and in a client file [#2573/C/snapshot].
`SWMisc_Patches` removes the `Perks.Fitness` XP boost from the vanilla Underweight and Overweight trait definitions at load, in a `lua/shared/` file [#2574/C/snapshot].
`ReduceGeneralHealth`, `setOverallBodyHealth`, `setCatchACold`, `setWoundInfectionLevel`, `setInfectionGrowthRate`, `setAimingDelay` and `CharacterStat.TEMPERATURE` have zero hits in the corpus's live version folders at the 2026-09-30 05:48 sweep [#2572/C/snapshot].
`1VCESTANDARD`'s live `42.19` script `VCEcontainers.txt` redefines the vanilla item `Bag_HydrationBackpack` under `module Base`, a fluid-container record it writes as `ItemType base:container` with no nutrition key [#2578/C/snapshot].

Summed over each record's eight most-registered events in the live version folders, the corpus registers `OnTick` 84 times over 17 mods, `OnPlayerUpdate` 55 over 39, `EveryOneMinute` 23 over 10 and `EveryTenMinutes` 5 over 3 at the 2026-09-30 05:48 sweep, a floor rather than a total, while the untruncated `OnPlayerUpdate` signal reads 61 over 43 [#2580/C/snapshot].
24 of those `OnTick` registrations are `SomewhatTraitsCore`'s at the 2026-09-30 05:48 sweep, every one in its `lua/server/SWTraitsCore_server.lua` [#2581/C/snapshot].

## Walls and bounds
<a id="walls"></a>

- A hit count is not a behaviour: every claim on this page is a file read or a count of regex hits over shipped files, and the Workshop sweep is a trend-sorted top-30-per-term slice rather than a census [#1564].
- A Workshop row that is not installed under the workshop root cannot be linted, profiled or measured from this repository, so everything recorded about it is a reading of its public page rather than of its files, and the only action that changes that is to subscribe to the id in Steam, let it download and re-run the mod-inventory tool [#1600].
- 176 of the 179 installed workshop items are returned by none of the eight terms, and `3774789651` Long Term Preservation — the one installed mod carrying both nutrition signals — appears in none of the eight pages while a third-party patch to it does, so absence from this dataset is not evidence about a mod, at the 2026-09-10 16:26 fetch [#1604/W/snapshot].
- The Workshop sweep's eight terms are the Workshop lead's own term list with realistic needs replaced by spoilage, seven of the eight original terms being swept as planned, at the same fetch [#1608/W/snapshot].
- Three of this page's multiplayer consequences are reasoning from the platform rows rather than measurements of the mod they are attached to: the server-side calorie write that sticks [#1633/C/inference], the client mirror a status bar can never beat [#1634/C/inference] and the stale zero under a client-side recipe filter [#1636/C/inference].
- The criterion that removes the script-only mods from the picks is a selection reading resting on script data being parsed identically on both sides and never synced, rather than a measurement [#1644/C/inference].
- The three teardown picks are chosen against the corpus as it stood at the 2026-09-10 17:47 sweep, and the corpus drifts under any later reading [#1641/C/snapshot, #1642/C/snapshot, #1643/C/snapshot].
- The class, signal and event columns of every row are computed over the live version folder alone, so a zero on a row whose `media_at` names a `common/media` is an unread folder rather than an absence ([../../reference/datasets.md](../../reference/datasets.md#mod-inventory)).
- The surface census reads the live version folder alone, like the signal columns before it, so a surface shipped only under `common/media` is cited from its file and never read as an absence ([../../reference/datasets.md](../../reference/datasets.md#mod-inventory)).

Not covered: no mod here was booted for this catalog — every reading is of a shipped file or of a Workshop page, so a mod's behaviour in play, its interaction with another mod at load, and everything the public Workshop holds outside the swept terms are all outside what the catalog ever opened.

## Open
<a id="open"></a>

- Whether AutoCook's per-player cooking settings survive a relog on a dedicated server is unmeasured, and it is the cheapest multiplayer question the catalog raises — settled by a profiled session that writes a setting, relogs the character and re-reads player modData on both sides [#1668/C/open].
- Whether the Kahlua dialect raises on `TryMeatCanned`'s chained comparison, which parses as a boolean compared to a number, is unreachable from anything shipped — settled by calling that function from the command bus [#1671/C/open].
- The design must decide whether to spend one Workshop subscription on a third-party nutrition overhaul, because the installed corpus holds no vanilla food override to learn from [#1595/C/snapshot].
- The design must decide how it reads a zero in the corpus dataset, because 177 of the 230 rows ship a `common/media` the signal scan never opened [#1559/C/snapshot].
- The design must decide whether it needs a command bus of its own, given that none of the three teardown picks has one [#1625/C/snapshot] while the resident stack it must coexist with already carries 228 sites [#1567/C/snapshot].
- The design must decide whether its own new foods sit in a module of their own or in `module Base`, because seven of the nine script-signalled mods declare `module Base` and only one of them ever collides with a vanilla name [#1594/C/snapshot].
- That SkillRecoveryJournal's protein-gated exercise multiplier is unwired, so that the mod reads no protein value to scale an experience grant, is unverified: it rests on a hand grep of the live `42.20.1/` tree on 2026-10-04 rather than a committed dataset; re-measure by a committed sweep of the item's Lua for a caller of `checkProteinLevelMulti` or an uncommented protein branch, and run [X43](../../reference/experiments.md)'s three protein arms only if one appears [#2092/C/snapshot/unverified].
- Whether QualityCooking and BeyondTen each load beside a probe mod on this server is open — settled by one co-boot reading each mod's own marker on both sides; -> [X45a](../../areas/open-questions.md#x45a) [#2094/C/open].
- That vanilla's `media/lua` calls `applyTraitFromWeight` nowhere is unverified: it rests on a hand scan of the install rather than a committed dataset; re-measure by a committed sweep of the install's Lua for that name [#2571/C/snapshot/unverified].
- The design must decide whether QualityCooking's code is read line by line before its own eat wrapper is written, because QualityCooking wraps the same eat completion on the server with no sentinel [#2562/C/snapshot] and reads the eaten macros inside that wrap [#2563/C/snapshot].
- The design must decide whether BeyondTen's code is read before any Strength or Fitness write, because BeyondTen extends every trainable skill past the native cap ([beyondten.md](beyondten.md#what-it-does)) [#1525/C/C-only].
- The design must decide whether Evolving Traits World's code is read before any runtime trait write, because the one runtime trait removal the census's trait names find runs on both sides [#2573/C/snapshot] and Evolving Traits World [#2592/W/snapshot] is a Workshop item this tree cannot read [#1600].
- The design must decide whether Tooltiplib's code is read before a tooltip wrap is written, because the tooltip render is already a sentinel-free wrap chain [#2568/C/snapshot] and Tooltiplib [#2593/W/snapshot] is a Workshop item this tree cannot read [#1600].
- The design must decide whether Nutrition Makes Sense, StatsAPI and Stat Tweaks Lib are read before release, because the stat hook is unclaimed only in the installed corpus [#2558/C/snapshot] and those three [#2585/W/snapshot] [#2590/W/snapshot] [#2591/W/snapshot] are Workshop items this tree cannot read [#1600].
- The design must decide whether the ApocalipseBR sync fix is read before release, because its page states a sync mechanism the library's measurements contradict [#2589/W/snapshot].

## See also

- [autocook.md](autocook.md#architecture) — the teardown of the corpus's sharpest `common/` against version-folder case, and the merge rule it settled.
- [longtermpreservation.md](longtermpreservation.md#what-it-does) — the domain twin: new foods with full macro sets plus a server-side cook hook.
- [simplestatus.md](simplestatus.md#mp) — what a pure client reader of the server's store can and cannot show.
- [somewhattraitscore.md](somewhattraitscore.md#mp) — the corpus's one player macro writer, measured writing the server's calorie store under a co-boot.
- [beyondten.md](beyondten.md#techniques) — the parallel-stat architecture behind this page's reflection-table reading.
- [itemquality.md](itemquality.md#pitfalls) — the unsynced-field failure this page's multiplayer consequences generalise.
- [../wire-packets.md](../wire-packets.md#item-stats-packet) — the item packet's field contract and the cadence a client mirror is bounded by.
- [../nutrition-core.md](../nutrition-core.md#macro-effects) — the macros every signalled mod reads or writes.
- [../food-item-model.md](../food-item-model.md#script-keys) — the script keys the script-nutrition sweep counts.
- [../../platform/mod-anatomy.md](../../platform/mod-anatomy.md#id-chain) — the declared id, the live `mod.info` chain and the folder-name question behind the status table.
- [../../platform/loader-and-scripts.md](../../platform/loader-and-scripts.md#per-key-merge) — the item-pass mechanism the corpus has no precedent for.
- [../../platform/mp-model.md](../../platform/mp-model.md#ownership) — which side owns what, which is what makes a client-side write a no-op.
- [../../platform/lessons.md](../../platform/lessons.md#corpus-drift) — why every count here carries its date.
- [../../reference/datasets.md](../../reference/datasets.md#mod-inventory) — the inventory columns, the partial-view caveat and the sweep stamp behind every number on this page.
- [../../reference/datasets.md](../../reference/datasets.md#workshop-rows) — the Workshop item-page snapshots behind every page reading here.
