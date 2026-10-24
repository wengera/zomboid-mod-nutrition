# Packaging
Verified against 42.20.4 (b0bbce05d5) · 2026-10-06 · scope: the nutrition-design reading of how this mod ships — its folder shape, what it does about the join checksum, the mods that will sit beside it on a live server and the seats it shares with them, the compatibility approaches open to it and how long any of this stays true; the id chain, the version dirs, the checksum gate and the missing-mod failure are `platform/mod-anatomy.md`, the file map and the path collisions `platform/loader-and-scripts.md`, and every corpus count `facts/other-mods/catalog.md`

## Rules
<a id="rules"></a>

- Never rely on a checksum-bypass role to seat a client whose script files differ: the bypass clears the gate's flags but not the difference, and each side keeps the definitions it loaded with nothing reconciling them, so that client plays on item values the server does not hold [#1230/C/C-only, #0648/C/inference, #2073/C/inference].
- Do not derive body order from `Mods=`: bodies replay sorted by the stored script path, so a mod's position in `Mods=` decides nothing about which body wins a key [#1055/M/n=2].
- Declare one id per mod folder and put it in the build's version dir: the loader parses that one `mod.info` and never the folder name, so a second `mod.info` with another id is unaddressable [#0802/C/C-only, #0881/M].
- Ship `common/` beside the version dir and keep only the build-specific files in the version dir: the version dir's file wins a same-relative-path collision and `common/` supplies everything the version dir does not ship [#1318/M/n=1].
- Give a build-independent payload a version dir holding nothing but a `mod.info`: an empty version dir costs the mod nothing and the `common/` tree still runs [#0831/M/n=1].
- Treat a `common/` file the version folder shadows as unmaintained, deleting it or keeping it building against the same interface as the live copy: it is unexecuted code on that build, and nothing in the mod asserts the merge direction it depends on [#1086/M/n=1].
- Give every script file a mod-unique relative path: the file map holds one absolute path per relative path and the script walk drops a repeat, so the loser's blocks are never parsed — a code reading, since no session has shipped the same relative script path from two mods [#1046, #1047/C/C-only].
- Guard every `media/lua/server/` file with a runtime `isServer()` test rather than trusting the folder: a mod's `server/` files execute in the multiplayer client's Lua state too, so "only my server file writes this" is false until the guard is there, and the side test is itself nil-checked because the global may be absent [#0855/M/n=1, #1075/M/n=1].
- Use `require=` when one mod must load before another: it is the only load-order declaration the loader acts on, and `loadModBefore=` and `loadModAfter=` only arrange rows in the client's mod selector [#0811/C/C-only, #0814/C/C-only].
- Ship byte-identical script files on both sides of a multiplayer session: the gate hashes file content with every CR byte dropped, so a mismatch is a disconnect rather than a silent degrade [#1182/C/C-only, #1231/C/C-only].
- Treat every Workshop update that changes a shipped script file as a server event: a client holding the new bytes and a server still running the old ones fail the join checksum against each other, a reading no run has exercised [#1182/C/C-only, #2077/C/inference].
- Treat every Workshop update that changes any shipped `.lua` file, a comment or whitespace included, as a server event exactly as a script file: a user-role client whose copy of one Lua file differs by one byte is kicked at the join, and only a line-ending-only difference is forgiven [#3378/C/inference, #3374/M/n=1, #3376/M/n=1, #3377/C/C-only].
- Keep every Lua file off the vanilla relative paths a resident mod already replaces: the file map keeps one file per relative path, so this mod and that neighbour would each lose the whole file to the other on load order [#1173/C/C-only, #1457/C/snapshot, #2074/C/inference].
- Give the mod's command-bus module a name no other mod on the server uses: the bus is one namespace shared with every other mod's command sites on that server [#1153/C/C-only, #2055/C/inference].
- Render through `MoodleFramework` or the mod's own panels rather than patching the widgets a resident interface mod already patches: `CleanUI` redraws the status surfaces on this server [#1083/C/snapshot].
- Declare `require=` on the mod whose item a shipped block names, in whichever mod ships the block: with that mod absent the append arm is never taken and the block declares a new partial item instead of overriding one — a code reading no run has exercised — while a failed `require=` leaves the requiring mod unloaded instead [#1002, #0811/C/C-only, #2076/C/inference].
- Name each version dir for the build its files were verified on and no later: the resolver takes the highest name at or below the running build, so a dir named for a later build is never read while one named for the verified build keeps running, unverified, on every later build until a newer-named dir ships [#3505/C/C-only, #2075/C/inference].
- Read a mod's `mod.info` rather than the loader's error text when a mod does not load: a failed `versionMin` or `versionMax` gate, a missing `require=` and a folder that is not there all print the same not-found line [#0872/C/C-only, #0812/C/C-only].
- Name in the mod's description every installed mod whose numbers its model makes inert or contradicts: a resident already writes the player's calories on the server once every five seconds per player, residents wrap the eat action on both sides, and a viewer drawing a re-based macro against hard-coded bands goes wrong silently, so the description is where an operator learns which of them this mod overrides [#1588, #2566/C/snapshot, #1522, #2091/M/n=1, #2715/C/inference].
- Print one self-report line at boot naming the mod's version and the optional frameworks it detected: an absent, a version-gated and an unsatisfied mod all print one not-found line and the server drops the id and boots clean, so no line the loader prints names the mod's own version or what it found beside it [#0871/C/C-only, #1793, #0872/C/C-only, #2547/C/inference, #2716/C/inference].
- Detect an optional framework with a type test on its global at `OnGameBoot` or later, never with `require`: the framework defines its global at file-load time and a test at the mod's own file scope can run before the framework's file, so a type test from `OnGameBoot` on reads its presence without going through the loader, while a `require` of its file goes through the loader and, with the framework absent, logs a warning and returns nothing on every server that runs without it [#2547/C/inference, #2717/C/inference].
- Stage a release from one command and never edit the staged bytes: the staged tree matched the repository byte for byte and every deployed copy matched it [#3315/M/n=1, #1182/C/C-only, #3321/C/inference].
- Diff the manifest before every Workshop update and treat any script file added, removed or changed as a server event: update the server first, then the clients, because the join checksum hashes every loaded script file [#1182/C/C-only, #2077/C/inference, #3322/C/inference].
- Read the mod's self-report line before any bug report: it names the version, the mode, the item pass, the legacy mirror and the framework the client found [#3312/M/n=1, #3313/M/n=1, #3323/C/inference].
- Run the layout lint before every boot: the harness does, and stops on an ERROR [#3311/C/inference, #3324/C/inference].

## How it works

This section reads [the anatomy page](../platform/mod-anatomy.md) (the id chain, the version dirs, the missing-mod failure, the checksum gate) and [the loader page](../platform/loader-and-scripts.md) (the file map, the path collisions) for one mod that joins a server it does not control, beside mods it did not write.
Every run cited was taken on the dedicated-server path, and every corpus reading is a dated snapshot ([lessons.md#corpus-drift](../platform/lessons.md#corpus-drift)).

<a id="layout"></a>
### This mod's folder shape

The mod is one folder with one declared id: the loader reads one `mod.info`, the version dir's when there is one, and never the folder name, so a folder whose name drifts from the id loads anyway ([#0802/C/C-only], [#1116/M/n=2], [mod-anatomy.md#id-chain](../platform/mod-anatomy.md#id-chain)).
A folder carrying `common/mod.info` alone is a shape the requested-id lookup has never been probed with, so the `mod.info` stays in the version dir ([#0823/C/C-only/open], [open-questions.md#x21](open-questions.md#x21)); one corpus mod with that shape boots in normal play, which does not probe the lookup ([#0821/M/n=1], [#1613/C/snapshot]).

A file that does not differ between builds goes in `common/`, and one that does goes in the version dir, which wins a same-relative-path collision ([#1318/M/n=1], [mod-anatomy.md#version-dirs](../platform/mod-anatomy.md#version-dirs)).
Three version-dir arms are measured: the manifest alone [#0831/M/n=1], colliding files [#1170/M/n=2], and a `media/sandbox-options.txt` that collides with nothing, whose option loaded [#3361/M/n=1]; whether a shadowed `common/` copy ever runs is unmeasured ([#0835/M/n=2/open], [open-questions.md#x22](open-questions.md#x22)).
The shipped shape, the manifest and the options file in the version dir beside a `common/` tree, booted clean on both sides and, staged, on a two-client session ([#2746/M/n=1], [#3316/M/n=1]).
A `common/` copy a version-dir file shadows is unexecuted code on that build, read on one mod in one session [#1086/M/n=1].

As shipped, the folder holds `42.21/`, carrying `mod.info` and `media/sandbox-options.txt`, and `common/`, carrying every Lua file and the translation files; the four EN translation files sit at vanilla Translate paths, where they merge key by key [#1318/M/n=1], and no other file sits at a vanilla relative path.
The version dir is named for the verified build because the resolver scores a name as the major times 1000 plus the minor and ignores the third component, so `42.21` is read on this build and every later one until a newer-named dir ships [#0826/C/C-only].
Two names the resolver scores alike have no declared winner, so the layout never ships two version dirs that a third component alone separates [#0880/C/C-only].
The manifest declares `versionMin=42.21` and no `versionMax`, so an older server drops the mod with the line an absent folder prints ([#0812/C/C-only], [#0872/C/C-only]).
The release version is 1.0.0: `NR_Core.lua`'s version string and the version dir's `modversion` both read 1.0.0, and the release notes open with a 1.0.0 section [#3817/C/snapshot].
A row of the takeover era that names its build's version names the pre-release build its bound gives, never this release.
The operator guide, the release notes and the compatibility table ship at the mod folder's root and travel with the item, the staged copy carrying them as it carries every other file [#3315/M/n=1].

The options file in the version dir carries a set value to every side.
On 42.20.4, `NR.Severity` 1.5 set in the server's sandbox file read 1.5 as the mod's server option and as `SandboxVars.NR.Severity` on the server and both clients, against 1 on a control boot with no override. [#3361/M/n=1]
On 42.21 the staged 1.0.0 upload copy read `NR.VisibilityMode` 3, against its declared default 2, as `SandboxVars.NR.VisibilityMode` and as the mod's own option on the server, the -debug client `admin` and the release client `bob`, while the next boot with no override read the default 2 [#4001/M/n=1].
On 42.21.0 the final upload copy, staged from mod/ at 4ff68475, read `NR.DeathPace` 1 and `NR.HealthCombine` 1, off their declared defaults 3 and 2, as `SandboxVars.NR.DeathPace` and `SandboxVars.NR.HealthCombine` on the server, `admin` and `bob` after both clients were ready and again at the end, and on the server as the mod's polled `options.deathPace` 1 and `options.healthCombine` 1 and the drain's `K.drain.OPT.pace` 1 and `K.drain.OPT.combine` 1; each client's copy of the mod's server options table read the declared defaults 3 and 2 [#4054/M/n=1].
On 42.21.0 the upload copy staged from mod/ at 0b1b3f11 read `NR.DeathPace` 2 and `NR.HealthCombine` 1, off their declared defaults 3 and 2, as `SandboxVars.NR.DeathPace` and `SandboxVars.NR.HealthCombine` on the server and `admin`, and on the server as the mod's polled `options.deathPace` 2 and `options.healthCombine` 1 and the drain's `K.drain.OPT.pace` 2 and `K.drain.OPT.combine` 1; `NutritionRevamp.version` read `1.0.0` on both sides, and the server log carried no mod error line [#4172/M/n=1].

On 42.20.4 the staged pre-release build of 1a8e207, the folder `tools/release_pack.py stage` writes, matched the repository byte for byte: 65 files staged, each equal by sha256 to its repository twin and to its manifest entry, and the copies the harness placed for the server and both clients equal too [#3315/M/n=1].
Booted, it printed one self-report line on the server, reading `itemPass=true`, `legacyMirror=on`, `hook=true`, `limitations=9` and `nutritionOn=false` at the options' defaults [#3312/M/n=1], and one on each client, reading `itemPass=true` and `frameworks=none` with no MoodleFramework installed [#3313/M/n=1].

Inside `media/` the file map keeps one absolute path per relative path and the script walk drops a repeat, so every relative path this mod ships is a claim on a slot, defended only by a path nobody else uses ([#1046], [loader-and-scripts.md#file-map](../platform/loader-and-scripts.md#file-map)).
The item pass's script files take mod-unique basenames with no `template_` prefix, for the reasons [the item pass](item-pass.md#walls) gives ([#1047/C/C-only], [#1233/C/C-only]).
No corpus mod keeps a nutrition key under `common/`, so a pass whose script files sit there has the loader's two-pass reading behind it and no shipped precedent ([#1561/C/snapshot], [#0827/C/C-only]).
A `server/` file runs in the client's Lua state too, so every one carries a runtime side test ([#1174/M/n=1], [overview.md#two-lua-states](../platform/overview.md#two-lua-states)), and a script hook's target is a global in a `shared/` file for the same reason [#3510/C/inference].
Item names ship in the B42 table layout, the only one this build reads, and matter on the client alone, because a dedicated server resolves no mod item's display name ([#1025/M/n=1], [#1167/M/n=1], [#3206/M/n=2], [mod-anatomy.md#translations](../platform/mod-anatomy.md#translations)).
No route on this build lets mod Lua compile a string into code, so a per-item handler or an operator's formula is data read by a shipped handler ([#1172/C/C-only], [lua-platform.md#removed-apis](../platform/lua-platform.md#removed-apis)).

`require=` is the one load-order key a dedicated server honours, and a missing or gated requirement takes the requiring mod down, so every `require=` is a deployment requirement ([#0811/C/C-only], [mod-anatomy.md#load-order-declarations](../platform/mod-anatomy.md#load-order-declarations)); `loadModBefore=`, `loadModAfter=` and `incompatible=` change nothing on a dedicated server ([#0814/C/C-only], [#0813/C/C-only]).
A mod the server names and cannot find does not fail the boot: the server boots with zero errors and a client joins with the mod inactive ([#1817/M/n=1], [mod-anatomy.md#missing-mod](../platform/mod-anatomy.md#missing-mod)).
A gated mod and a mod missing a requirement take the same code path, all three states printing one not-found line and dropping the id before any mod loads, so the clean boot carries over to them by that path rather than by a run of their own [#0871/C/C-only, #0872/C/C-only, #1817/M/n=1].
A joining client runs the server's list rather than its own, so a player's local enable proves nothing about what a session ran ([#0876/C/C-only], [mod-anatomy.md#join](../platform/mod-anatomy.md#join)).
The layout lint checks the folder before any boot, its missing-version-dir error stricter than the engine on purpose ([#0858/C/snapshot], [tools.md#mod-lint](../reference/tools.md#mod-lint)).

<a id="checksum-plan"></a>
### What this mod does about the checksum gate

Every script file the session loads is hashed at load and compared at the join, so the item pass reaches a multiplayer server only on the gate's terms ([#1182/C/C-only], [mod-anatomy.md#checksum-gate](../platform/mod-anatomy.md#checksum-gate)).
The gate has three arms, one per flag a bypass role clears, and the anatomy page reads the script and Lua arms ([#1230/C/C-only], [#3374/M/n=1], [mod-anatomy.md#walls](../platform/mod-anatomy.md#walls)).
The plan is one answer to all three: the server and every client load the same bytes from one build of the mod.

The item pass is script data, free at run time only at the price of this gate ([#1243/M/n=1], [loader-and-scripts.md#per-side-load](../platform/loader-and-scripts.md#per-side-load)).
Its files are generated once and published as they stand, never edited on one machine, because any byte the copies disagree on is a disconnect, and a line-ending conversion is the one change the gate's tolerance covers [#1182/C/C-only].
An editor's byte-order mark or trimmed trailing space is not covered, so the published files are the generator's output and nothing else.
A joining client loads the server's `Mods=` list, so this mod keeps its own files identical and can do nothing about a neighbour's ([#1182/C/C-only], [#0876/C/C-only]).

Steam rewrites a Workshop item's tree underneath an install, so a client that took an update and a server on the old files meet with two different hashes ([#1841/C/snapshot], [#1182/C/C-only]).
A probe mod whose two copies differed by one byte disconnected its client without reaching the game, though no Workshop update itself has been run [#1282/M/n=1]; each side's arm acts at its own time [#1231/C/C-only].
The script files reach every side as one set of bytes by staging from one command: the staged tree is the only copy a server or a client is given [#3315/M/n=1].
A release tool can hash every script file with the gate's own tolerance, every CR byte dropped, and name the files whose hash moved between two releases, so an update that will fail the join checksum is known before it ships [#3325/C/inference].
In the worked example, the release tool hashes every script file under `media/scripts/` and every Lua file under `media/lua/` with every CR byte dropped, and against the previous release's manifest prints `SERVER EVENT` with the count of script or Lua files added, removed or whose hash moved. [#3814/C/C-only]

A bypass role seats a client whose scripts differ, and each side keeps the definitions it loaded with nothing reconciling them, so that client plays on item values the server does not hold ([#1230/C/C-only], [#3139/M/n=1], [#0648/C/inference]): a loud failure becomes a silent disagreement over the numbers this mod exists to set.

The Lua arm gates as the script arm does: one byte changed inside a comment of one of this mod's Lua files disconnected a `user`-role client at the join, while a copy differing only in line endings joined ([#3374/M/n=1], [#3376/M/n=1]), so an update touching any `.lua` file is a server event too [#3378/C/inference, #3374/M/n=1].
On 42.21 a `user`-role client holding a copy of the staged 1.0.0 `NR_Core.lua` one byte off inside its first comment line was kicked with the anti-cheat reason `Lua incorrect checksum` and never reached the game, while the admin client stayed connected [#4003/M/n=1].
The animation arm is unread, so the plan treats it as gating, and a nutrition overhaul ships no animation.

A client whose copy of one script file differed by one byte was disconnected before it reached the game, while a copy differing only in line endings joined and stayed ([#1282/M/n=1], [#3138/M/n=1]).
On build 42.21.0 the release client `bob` joined the server of the final 1.0.0 upload copy, staged from mod/ at 4ff68475, and stayed: `admin` and `bob` both reached ready, `NutritionRevamp.version` read `1.0.0` on the server, `admin` and `bob`, the server's user log recorded `bob` fully connected 31.624 s after its `attempting to join` line, the player list read `admin` and `bob` at the end, the server's user log carried no anti-cheat line, the server log and both client consoles no checksum-mismatch line, the server log no mod error line, and the -debug client `admin` never stopped in the debugger [#4055/M/n=1].

<a id="resident-stack"></a>
### The mods beside it on a live server

The neighbours are the server's approved list, the installed corpus the catalog sweeps, which offers no vanilla food override [#1674/C/snapshot]; every nutrition-bearing script block in it adds a new item, so the item pass contests no food key, a census over the script-signalled mods only ([#1595/C/snapshot], [catalog.md#corpus-facts](../facts/other-mods/catalog.md#corpus-facts)).
Build status rules none of the nutrition-signalled residents out: every one resolves a version folder this build reads and none lints at error level [#1645/C/snapshot].
Every reading below is a static read of shipped files on a dated sweep, none booted beside this mod ([catalog.md#walls](../facts/other-mods/catalog.md#walls)).

| resident mod | what it touches | what that asks of this mod | tags |
|---|---|---|---|
| `CleanUI` | most of its live Lua tree sits at vanilla relative paths and replaces those files whole, the inventory context-menu file among them, whose fork reverts any later vanilla change to that menu for every mod on the event | no Lua file at a path it already replaces, and no status widget patched on top of its redraw | [#1457/C/snapshot], [#1371/C/snapshot], [#1083/C/snapshot] |
| `QuestSystem`, `Economy`, `BaseQuests`, `SDQuests`, `GirthsTweaks`, `ItemQuality` | command-bus sites in the hundreds between them, the quest system's the most; two of the six write nutrition keys in scripts that declare the base module and collide with no vanilla name | a command-bus module name none of them uses; no contested script key | [#1567/C/snapshot], [#1591/C/snapshot] |
| `simpleStatus` | a client-only viewer of the macros and the weight trend that transmits the player's whole modData table from its input handlers and draws the numbers a rebalance moves against hard-coded bands | no server-only key in player modData; a re-based scale miscalibrates its bars silently, and its bars follow the client's mirrored store within one push, so they show whatever this mod's server writes, late by that push | [#1482], [#1522], [#2093/M/n=1] |
| `AutoCook` | client-side reads of the player's nutrition that choose spices and filter ingredients, and a `mod.info` in `common/` only | a rebalance changes what it chooses and nothing it defines; its manifest is the shape the id-chain probe targets | [#1585], [#1377/C/snapshot], [#1613/C/snapshot] |
| `SKITTLE_LongTermPreservation4220` | foods in its own module, some feeding vanilla evolved recipes, and a server-side cook hook that scales a crafted instance's macros | its foods sit outside a base-module pass, and a block naming one is an override only while it loads | [#1461/C/snapshot], [#1587], [#1030/M/n=1] |
| `SomewhatTraitsCore` | the corpus's only player macro write, a server-side per-tick calorie adjustment behind a trait | a second writer of the player's calories on the same side, which no packaging lever separates: measured adding or removing a third of a kilocalorie every five seconds per player outside its 77-to-83 kg band and nothing inside it ([somewhattraitscore.md](../facts/other-mods/somewhattraitscore.md#mp)) | [#1588], [#2091/M/n=1], [#2762/M/n=1] |
| `SkillRecoveryJournal` | a protein-scaled exercise multiplier shipped in `shared/` under an upstream not-yet-implemented marker, its other copy block-commented, so shipped rather than live; and a journal tooltip that calls its own fork of vanilla's render instead of the tooltip chain | nothing from the multiplier while it stays unwired, which a dated re-read of the live tree on 2026-10-04 confirmed; a tooltip wrap of this mod's is bypassed on the journal's tooltip | [#1584], [#2092/C/snapshot/unverified], [#2568/C/snapshot] |
| `MoodleFramework` | server-approved, and whole on this build under the merge rule | the rendering route [the UI page](ui-and-moodles.md) weighs | [#1070/C/snapshot], [#1319/C/snapshot] |
| `Horse` | the script-signalled set's one vanilla-name collision, a redefinition of a base item that is not a food | nothing: the pass and it name no item in common | [#1594/C/snapshot] |

A file of this mod at a path the interface mod already holds would lose to it or displace it whole by load order, with the loader's `overrides` print the only witness ([#1173/C/C-only], [#1176/C/C-only], [loader-and-scripts.md#file-map](../platform/loader-and-scripts.md#file-map)).
With it resident, a raising listener on the context-menu event shows as the interface mod's own printed failure line rather than a raw error, the form a driver's grep has to expect ([#1369/C/C-only], [autocook.md#compat](../facts/other-mods/autocook.md#compat)).

Four more surfaces are shared, and packaging acts on none of them:
- the bus namespace, kept apart by a module name nobody else uses ([#1153/C/C-only], [mp-sync.md#failure-modes](mp-sync.md#failure-modes));
- the player's modData table, whose server copy a client-only viewer rewrites whole from its input handlers, survived by [the MP sync page's routes](mp-sync.md#sync-options) [#1482];
- the calorie store, which a trait mod's server handler writes each player once every five seconds outside its weight band, measured reaching the store under a co-boot, a question for [the nutrient page](new-nutrients.md) ([#1588], [#2091/M/n=1], [#1070/C/snapshot]);
- the numbers the viewers draw: a status bar and a cooking automation define nothing this mod could contradict and read everything it moves ([#1522], [#1377/C/snapshot]); a skill mod's protein ladder joins them only once wired, the shipped ladder still under its not-yet-implemented marker on a 2026-10-04 re-read ([#1584], [#2092/C/snapshot/unverified]).

Booted beside a stand-in folder carrying only Nutrition Makes Sense's mod id, the release printed its compatibility warning once in the server log, `Nutrition Makes Sense is loaded. Both mods write hunger, the calorie store and body weight every minute and book each other's calorie writes as meals; run one of them (see COMPATIBILITY.md). Nutrition Revamp keeps running.`, set its writer's `nms` flag and kept running, the server answering its player list at the end. [#3780/M/n=1] [#3527/C/inference]

An unguarded raise aborts the rest of the raising handler's body while the handlers behind it keep running, so this mod's handlers survive a neighbour's raise, while a call into a neighbour's code needs a protected call of its own — measured on the server's Lua state and on a release client [#1179/M/n=1] [#3317/M/n=1]; whether the interface mod's protected dispatch changes that is open ([#1292/C/open], [open-questions.md#x26](open-questions.md#x26)).

A base-module pass does not touch a food another mod declares in its own module, and a block naming one is an override only while that mod loads ([#1030/M/n=1], [item-pass.md#scope](item-pass.md#scope)); how this mod ships such a block is the patch-mod row of [the options](#compat-options).
Two resident Workshop items ship several mods each, so a server names a mod by its id, and a second folder can ride one Workshop item ([#1543/C/snapshot], [#1617/C/snapshot]).
A public fix for the multiplayer nutrition-sync problem, a third-party patch to the preservation mod, and the public nutrition overhauls the search term returns are absent from the installed tree ([#1605/W/snapshot], [#1606/W/snapshot], [#1599/W/snapshot]), so what they replace or transmit is unread until someone subscribes and re-runs the inventory [#1600]; the decisions they block are under [Open](#open).

<a id="sharing-a-server"></a>
### Sharing a server

Past files and ids, the residents meet this mod at seats the loader never arbitrates, read statically on the dated sweep or off the bytecode, none booted beside this mod ([catalog.md#walls](../facts/other-mods/catalog.md#walls)).
- **The stat hook** is unclaimed: no live version folder in the installed corpus references it or the hook manager, and the corpus's only hook call is the interface mod's pair on the auto-drink hook, carried over from vanilla [#2558/C/snapshot]; an uninstalled public item stays unread ([catalog.md#open](../facts/other-mods/catalog.md#open)).
- **The eat action** is shared: `QualityCooking` wraps its methods on the server, `EmergencyVomitB42` on the client and `SomewhatTraitsCore` in shared code, and only `EmergencyVomitB42`'s wraps sit behind an idempotency sentinel [#2566/C/snapshot]; `QualityCooking` saves the original completion into a local and redefines the method unconditionally [#2562/C/snapshot]. A wrapper of this mod's joins that chain in load order, its seat [the hook page's](eat-and-cook-hooks.md#seat-in-the-order) reading, and only the description tells an operator they share it.
- **An optional framework** is detected, never required: `MoodleFramework` defines its global at file-load time, so a type test at `OnGameBoot` or later finds it, while a `require` of its file finds nothing when it is absent [#2547/C/inference]; a file-scope test can run before the framework's file ([loader-and-scripts.md#lua-load-order](../platform/loader-and-scripts.md#lua-load-order)).
- **The sandbox options** ship in one declaration file, in the version dir or in `common/`, and the loader reads exactly one of the two per mod [#2422/C/C-only]; a file at the mod root's own `media/` is never read [#2423/C/C-only]. Option names are shared server-wide and two mods declaring the same prefix and short name collide silently [#2437/C/C-only], so the prefix is picked like the bus module name ([sandbox-options.md#declaration](../platform/sandbox-options.md#declaration)).

<a id="shelf-life"></a>
### The stamp is a shelf life

A reading here holds for the build the stamp names and for the corpus as it stood on its sweep ([lessons.md#corpus-drift](../platform/lessons.md#corpus-drift)).
Steam rewrites a Workshop item's tree without touching its folder, so a folder's age is no check of staleness [#1841/C/snapshot]; every corpus count is dated and a recount is a new reading [#1964/C/snapshot], and a line cite into a neighbour is re-located by content before it is quoted [#1466/C/snapshot].

A build bump does not stop this mod from loading, and that is the hazard: the resolver picks the highest version dir at or below the running build, so this build's dir runs, unverified and silently, on every later build until a newer-named one exists, while a dir named for a later build is never read until that build ships [#3505/C/C-only].
The manifest keys that pin availability close the first trap and report a build outside the range exactly as an absent folder ([#0812/C/C-only], [#1177/C/C-only], [mod-anatomy.md#build-pinning](../platform/mod-anatomy.md#build-pinning)); no Lua route to the running build number is known ([mod-anatomy.md#walls](../platform/mod-anatomy.md#walls)).
The layout lint sees neither trap, its model of the live version folder ignoring the running build's ceiling [#0864/C/snapshot], and its agreement check makes a flagged `mod.info` authoritative once the version dir's copy goes or the build moves past it [#0861/C/C-only].

After a bump, re-read in order of consequence:
- the checksum gate, measured on one build, which decides whether the mod can join at all ([#1282/M/n=1], [#1231/C/C-only]);
- the removed members: a removed member this mod calls is a nil call that aborts the body it fires in, and this build already removed members the corpus still calls ([#0961/M/n=1], [#0962/M/n=1], [lua-platform.md#removed-apis](../platform/lua-platform.md#removed-apis));
- the per-key merge and the replay order, each measured on this build alone ([#1180/M/n=1], [#1183/M/n=2]);
- the packet field lists every desync reading rests on ([mp-sync.md#failure-modes](mp-sync.md#failure-modes));
- the dataset, since a later build's foods reach the pass only after a re-scan ([item-pass.md#scope](item-pass.md#scope)).

## Options

<a id="compat-options"></a>
### The compatibility approaches

A resident that shares a file or a key leaves four approaches open; none changes a shared surface such as the bus, the player's table or the calorie store, which are [the MP sync page's](mp-sync.md#sync-options).

| option | what it costs | which wall it hits | tags |
|---|---|---|---|
| shadow — ship this mod's own copy of a file at the relative path a vanilla file or a neighbour already holds | the whole file at that path: vanilla's later edits to it vanish, a neighbour at the same path loses its copy or takes this mod's on load order, and the replacement runs in vanilla's slot before every mod's own block | a shadow replaces the whole file and never part of it, two mods that both want one file cannot compose, and a script shadow drops the losing file's blocks entirely, which is why the rules keep every script path mod-unique and leave a shadow to Lua files | [#1168/C/C-only], [#1176/C/C-only], [#1175/C/C-only] |
| `common/` split — the build-independent payload in `common/`, with a version dir carrying only the files one build needs its own copy of, such as a file whose resident counterpart exists in some of that resident's version trees and not others | a version dir per build that diverges, and every `common/` file a version dir shadows turned into unexecuted code, as read on one mod in one session, that is deleted or kept building | the merge is measured only for a version dir that ships colliding files or none, and whether a non-colliding version dir loads or a shadowed copy runs is unmeasured | [#1170/M/n=2], [#1086/M/n=1], [#0835/M/n=2/open], [#1367/C/snapshot] |
| do nothing — ship the mod alone on mod-unique paths and names and leave the residents as they are | nothing to build or publish; every contested key goes to whichever body sorts last, and a neighbour that ever ships one of this mod's relative paths costs one of the two a whole file, with only the loader's `overrides` print to show it | coexistence with a mod shadowing the same Lua file holds only through a mod-unique path, two mods cannot load one relative script path, and the replay order decides a key both declare | [#1173/C/C-only], [#1175/C/C-only], [#1183/M/n=2] |
| a patch mod — a second, small mod that declares `require=` on this mod and on the neighbour and carries only the adaptation | a second id to publish and name in `Mods=`, which can ride this mod's Workshop item as a second folder; unavailable, on a boot that still reads clean, whenever either required mod is missing or gated; its script bodies win a contested key only when their stored path sorts last, whatever `require=` orders | a failed requirement or build gate prints the line an absent folder prints, and the replay follows the stored script path rather than the load order | [#1177/C/C-only], [#0811/C/C-only], [#1817/M/n=1], [#1183/M/n=2], [#1543/C/snapshot] |

Which approach does this mod take toward each resident it shares a file or a key with: a shadow, a `common/` split, doing nothing, or a patch mod?

## Walls and bounds
<a id="walls"></a>

- No mod survives a script mismatch between the server and a client: the join checksum disconnects the client, measured for a one-byte difference in one probe file under the `user` role, while the `admin` role bypasses it ([#1182/C/C-only], [#1282/M/n=1], [#3139/M/n=1]).
- A vanilla Lua file can be replaced at its own relative path, and `require` resolves across the merged map, which is a door and a trap at once: two mods that both want the file cannot compose [#1168/C/C-only].
- A mod can retune hunger and thirst through the globals table only with a workaround, and two mods that retune it still collide, per key at file scope rather than per file [#1169/C/C-only].
- A mod can ship `common/` beside a version folder, measured only for a version dir that ships colliding files or none at all ([#1170/M/n=2], [open-questions.md#x22](open-questions.md#x22)).
- A mod can rely on the `mod.info` id-read order and on a folder name that is not its id, measured on the dedicated-server `Mods=` path only ([#1171/M/n=1], [open-questions.md#x21](open-questions.md#x21)).
- No mod can use `loadstring`, so every code path this mod runs is a file in its folder at load time [#1172/C/C-only].
- A second mod shadowing the same Lua file coexists with this one only with a workaround, a mod-unique relative path, because the last write wins on load order [#1173/C/C-only].
- Server-only logic stays on the server only with a workaround, a runtime side test, because a mod's `server/` files run in the client's Lua state too [#1174/M/n=1].
- No two mods both load a file at one relative script path: one file wins and the other's blocks are never parsed ([#1175/C/C-only], [open-questions.md#x20](open-questions.md#x20)).
- No mod replaces part of a shadowed Lua file: the one entry at a relative path is the whole body that runs [#1176/C/C-only].
- No mod diagnoses a build gate from the loader's error text: a failed version gate prints the line an absent folder prints [#1177/C/C-only].
- This mod survives its own or a neighbour's unguarded raise only with a workaround, a protected call at every boundary, measured on the server's Lua state and on a release client [#1179/M/n=1] [#3317/M/n=1].
- A mod can rely on the replay order, which is the stored script path rather than `require=` or `Mods=`, so a patch mod wins a contested key only through its own file names [#1183/M/n=2].
- Every reading of the resident stack is a static read of a dated snapshot of an installed tree that drifts, and no two resident mods were booted together ([#1964/C/snapshot], [catalog.md#walls](../facts/other-mods/catalog.md#walls)).

Not covered: the Steam Workshop upload, subscription and update surface, including any version check the Workshop makes of its own; the animation arm of the checksum gate, and the Lua arm beyond one file, the `user` role and the two differences read; a listen server and the client's own mod selector; any Lua route to the running build number; and every neighbour that is not installed — this library read none of them.

## Open
<a id="open"></a>

- Whether two mods at one relative path both load, for a script file and for a Lua file, and whether a mod file at a vanilla relative script path is dropped entirely — settled by two mods shipping the same relative paths with different content, reading which item and which global survive, plus a boot that ships a mod file at a vanilla relative script path; until then the shadow and do-nothing rows of the options rest on the loader's code; -> X20 ([#1286/C/open], [open-questions.md#x20](open-questions.md#x20)).
- Whether a folder whose only `mod.info` is `common/mod.info` resolves under the requested-id lookup, and whether the client's own mod-list call site agrees with the dedicated server's — settled by a purpose-built mod carrying `common/mod.info` and nothing else, its verify gate on the server side only, read on both sides; until then this mod keeps its `mod.info` in the version dir; -> X21 ([#1287/C/open, #0823/C/C-only/open, #0877/C/C-only/open], [open-questions.md#x21](open-questions.md#x21)).
- Whether a shadowed `common/` copy ever executes — settled by a mod whose `common/` and version dir each ship a colliding and a non-colliding file, with a sentinel only the shadowed copy can set; the non-colliding half of X22 is settled for the shipped options file [#3361/M/n=1]; until the shadow arm runs the version dir holds only the manifest, the options file and files that shadow a `common/` copy; -> X22 ([#1288/C/open, #0835/M/n=2/open], [open-questions.md#x22](open-questions.md#x22)).
- Whether the interface mod's protected dispatch changes what an unguarded raise does inside it — settled by one session that drives the interface mod's context-menu entry through a harness addition, reading that mod's own printed failure line and whether the handlers behind the raiser ran; -> X26 ([#1292/C/open], [open-questions.md#x26](open-questions.md#x26)).
- Decision: whether a patch mod, if one ships, rides this mod's Workshop item as a second folder or an item of its own — the 2026-10-08 neighbour reads named no neighbour a patch must target: one is incompatible outright, two never run on a server and one composes [#3527/C/inference, #3534/C/inference, #3541/C/inference, #3551/C/inference]; forced by a server naming mods by id and resident items already shipping several mods each ([#1219/C/C-only], [#1543/C/snapshot]).
- Decision: whether a block of this mod naming the preservation mod's foods can coexist with the third-party patch that claims that mod launders nutrition — blocked by the patch being uninstalled (3796644824; deferred on 2026-10-06: the item is not subscribed), and forced by a block naming another mod's food being an override only while that mod loads ([#1606/W/snapshot], [#1030/M/n=1], [#1600]).
- Decision: whether this mod is built to share a server with any public nutrition overhaul — not blocked: Nutrition Makes Sense, read on 2026-10-08, writes the same stats each minute and re-bases 438 of the same foods [#3527/C/inference, #3526/C/arith.], and forced by `incompatible=` stopping nothing on a server ([#1599/W/snapshot], [#0813/C/C-only]).

## Worked examples

| shape | file:lines | what it shows |
|---|---|---|
| a version dir holding only the manifest | `testing/experiments/TKX_CommonOnly/42.20/mod.info:1-5` | five keys and no `media/` beside them — the empty-version-dir arm this layout stays inside |
| the whole payload under `common/` | `testing/experiments/TKX_CommonOnly/common/media/lua/shared/TKX_CommonOnly.lua:1-4` | the one file of that mod, which still loads and resolves on both sides with the version dir empty |
| a script file under a mod-unique basename | `testing/experiments/TKX_ItemOverride/42.20/media/scripts/tkx_item_override.txt:24-29` | the partial `item Orange` block, in a file whose relative path no other mod ships |
| an item-name table in the B42 layout | `testing/experiments/TKX_ItemOverride/42.20/media/lua/shared/Translate/EN/ItemName.json:1-3` | a bare `Module.Name` key, the only item-name layout this build reads |

## See also

- [`../platform/mod-anatomy.md`](../platform/mod-anatomy.md#checksum-gate) — the id chain, the version dirs, the missing-mod failure, build pinning and the checksum gate.
- [`../platform/loader-and-scripts.md`](../platform/loader-and-scripts.md#file-map) — the file map, the path collisions and the per-side load.
- [`../facts/other-mods/catalog.md`](../facts/other-mods/catalog.md#corpus-facts) — the resident mods, what each touches, and the Workshop neighbours that are not installed.
- [`../reference/tools.md`](../reference/tools.md#mod-lint) — the layout lint.
- [`../platform/sandbox-options.md`](../platform/sandbox-options.md#declaration) — the declaration file's location and the shared option names.
- [`eat-and-cook-hooks.md`](eat-and-cook-hooks.md#seat-in-the-order) — the eat seat the residents' wraps already share.
- [`item-pass.md`](item-pass.md) — the script files this page packages.
- [`mp-sync.md`](mp-sync.md) — the shared surfaces packaging cannot separate.
- [`open-questions.md`](open-questions.md) — the experiments this page's open rows point at.
