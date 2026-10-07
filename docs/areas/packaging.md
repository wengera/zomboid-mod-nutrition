# Packaging
Verified against 42.20.4 (b0bbce05d5) · 2026-10-06 · scope: the nutrition-design reading of how this mod ships — its folder shape, what it does about the join checksum, the mods that will sit beside it on a live server and the seats it shares with them, the compatibility approaches open to it and how long any of this stays true; the id chain, the version dirs, the checksum gate and the missing-mod failure are `platform/mod-anatomy.md`, the file map and the path collisions `platform/loader-and-scripts.md`, and every corpus count `facts/other-mods/catalog.md`

## Rules
<a id="rules"></a>

- Declare one id per mod folder and put it in the build's version dir: the loader parses that one `mod.info` and never the folder name, so a second `mod.info` with another id is unaddressable [#0802/C/C-only, #0881/M].
- Ship `common/` beside the version dir and keep only the build-specific files in the version dir: the version dir's file wins a same-relative-path collision and `common/` supplies everything the version dir does not ship [#1318/M/n=1].
- Give a build-independent payload a version dir holding nothing but a `mod.info`: an empty version dir costs the mod nothing and the `common/` tree still runs [#0831/M/n=1].
- Treat a `common/` file the version folder shadows as unmaintained, deleting it or keeping it building against the same interface as the live copy: it is unexecuted code on that build, and nothing in the mod asserts the merge direction it depends on [#1086/M/n=1].
- Give every script file a mod-unique relative path: the file map holds one absolute path per relative path and the script walk drops a repeat, so the loser's blocks are never parsed — a code reading, since no session has shipped the same relative script path from two mods [#1046, #1047/C/C-only].
- Guard every `media/lua/server/` file with a runtime `isServer()` test rather than trusting the folder: a mod's `server/` files execute in the multiplayer client's Lua state too, so "only my server file writes this" is false until the guard is there, and the side test is itself nil-checked because the global may be absent [#0855/M/n=1, #1075/M/n=1].
- Use `require=` when one mod must load before another: it is the only load-order declaration the loader acts on, and `loadModBefore=` and `loadModAfter=` only arrange rows in the client's mod selector [#0811/C/C-only, #0814/C/C-only].
- Ship byte-identical script files on both sides of a multiplayer session: the gate hashes file content with every CR byte dropped, so a mismatch is a disconnect rather than a silent degrade [#1182/C/C-only, #1231/C/C-only].
- Treat every Workshop update that changes a shipped script file as a server event: a client holding the new bytes and a server still running the old ones fail the join checksum against each other, a reading no run has exercised [#1182/C/C-only, #2077/C/inference].
- Never rely on a checksum-bypass role to seat a client whose script files differ: the bypass clears the gate's flags but not the difference, and each side keeps the definitions it loaded with nothing reconciling them, so that client plays on item values the server does not hold [#1230/C/C-only, #0648/C/inference, #2073/C/inference].
- Keep every Lua file off the vanilla relative paths a resident mod already replaces: the file map keeps one file per relative path, so this mod and that neighbour would each lose the whole file to the other on load order [#1173/C/C-only, #1457/C/snapshot, #2074/C/inference].
- Give the mod's command-bus module a name no other mod on the server uses: the bus is one namespace shared with every other mod's command sites on that server [#1153/C/C-only, #2055/C/inference].
- Render through `MoodleFramework` or the mod's own panels rather than patching the widgets a resident interface mod already patches: `CleanUI` redraws the status surfaces on this server [#1083/C/snapshot].
- Do not derive body order from `Mods=`: bodies replay sorted by the stored script path, so a mod's position in `Mods=` decides nothing about which body wins a key [#1055/M/n=2].
- Declare `require=` on the mod whose item a shipped block names, in whichever mod ships the block: with that mod absent the append arm is never taken and the block declares a new partial item instead of overriding one — a code reading no run has exercised — while a failed `require=` leaves the requiring mod unloaded instead [#1002, #0811/C/C-only, #2076/C/inference].
- Name each version dir for the build its files were verified on and no later: the resolver takes the highest name at or below the running build, so a dir named for a later build is never read while one named for the verified build keeps running, unverified, on every later build until a newer-named dir ships [#0825/C/C-only, #2075/C/inference].
- Read a mod's `mod.info` rather than the loader's error text when a mod does not load: a failed `versionMin` or `versionMax` gate, a missing `require=` and a folder that is not there all print the same not-found line [#0872/C/C-only, #0812/C/C-only].
- Name in the mod's description every installed mod whose numbers its model makes inert or contradicts: a resident already writes the player's calories on the server once every five seconds per player, residents wrap the eat action on both sides, and a viewer drawing a re-based macro against hard-coded bands goes wrong silently, so the description is where an operator learns which of them this mod overrides [#1588, #2566/C/snapshot, #1522, #2091/M/n=1, #2715/C/inference].
- Print one self-report line at boot naming the mod's version and the optional frameworks it detected: an absent, a version-gated and an unsatisfied mod all print one not-found line and the server drops the id and boots clean, so no line the loader prints names the mod's own version or what it found beside it [#0871/C/C-only, #1793, #0872/C/C-only, #2547/C/inference, #2716/C/inference].
- Detect an optional framework with a type test on its global at `OnGameBoot` or later, never with `require`: the framework defines its global at file-load time and a test at the mod's own file scope can run before the framework's file, so a type test from `OnGameBoot` on reads its presence without going through the loader, while a `require` of its file goes through the loader and, with the framework absent, logs a warning and returns nothing on every server that runs without it [#2547/C/inference, #2717/C/inference].
- Stage a release from one command and never edit the staged bytes: the staged tree matched the repository byte for byte and every deployed copy matched it [#3315/M/n=1, #1182/C/C-only, #3321/C/inference].
- Diff the manifest before every Workshop update and treat any script file added, removed or changed as a server event: update the server first, then the clients, because the join checksum hashes every loaded script file [#1182/C/C-only, #2077/C/inference, #3322/C/inference].
- Read the mod's self-report line before any bug report: it names the version, the mode, the item pass, the legacy mirror and the framework the client found [#3312/M/n=1, #3313/M/n=1, #3323/C/inference].
- Run the layout lint before every boot: the harness does, and stops on an ERROR [#3311/C/inference, #3324/C/inference].

## How it works

A nutrition overhaul ships as one mod folder on the Workshop, and every mechanism that folder meets is owned by another page.
The id chain, the version dirs, the missing-mod failure and the checksum gate are [the anatomy page](../platform/mod-anatomy.md), and the file map and the path collisions are [the loader page](../platform/loader-and-scripts.md).
This page is the reading of those mechanisms for one mod that has to join a server it does not control, beside mods it did not write, on a build that will not stay current.
It owns its rules and no fact or number: every claim below is cited to the row that owns it, and the untagged sentences are this mod's reading of those rows.
It is in five parts — the folder, the checksum, the neighbours, the seats it shares with them and the shelf life — and the compatibility approaches the neighbours leave open are under [Options](#compat-options).
Every run it cites was taken on the dedicated-server path, and every corpus reading is a dated snapshot of an installed tree ([lessons.md#corpus-drift](../platform/lessons.md#corpus-drift)).

<a id="layout"></a>
### This mod's folder shape

The mod is one folder with one declared id, and the folder's name plays no part in it.
The loader reads exactly one `mod.info` per folder, the version dir's when it has one and `common/`'s otherwise, and never the folder name ([#0802/C/C-only], [mod-anatomy.md#id-chain](../platform/mod-anatomy.md#id-chain)).
A second `mod.info` with another id is therefore not a second mod but an unaddressable file, so the layout carries exactly one [#0881/M].
A Workshop folder whose name drifts from the id loads anyway, which is why nothing in this mod depends on its install path ([#1116/M/n=2], [mod-anatomy.md#folder-name](../platform/mod-anatomy.md#folder-name)).
Where that one `mod.info` sits is the choice the measured arms settle: a folder carrying `common/mod.info` alone is the shape the requested-id lookup has never been probed with, so this mod keeps its `mod.info` in the version dir until the probe lands ([#0823/C/C-only/open], [open-questions.md#x21](open-questions.md#x21)).
One corpus mod with that shape boots in normal play, which shows the shape works and does not probe the lookup ([#0821/M/n=1], [#1613/C/snapshot]).

The payload splits on one question: does a file differ between builds.
A file that does not goes in `common/`, and a file that does goes in the version dir, which wins a same-relative-path collision while `common/` supplies everything else ([#1318/M/n=1], [mod-anatomy.md#version-dirs](../platform/mod-anatomy.md#version-dirs)).
A version dir holding nothing but the `mod.info` is the arm measured to cost nothing, and it is the shape a payload with no per-build file takes [#0831/M/n=1].
Three arms are measured: that one, the colliding-files arm and a version dir shipping `media/sandbox-options.txt` that collides with nothing, whose option loaded [#3361/M/n=1]; whether a shadowed `common/` copy ever runs is unmeasured ([#1170/M/n=2], [#0835/M/n=2/open], [open-questions.md#x22](open-questions.md#x22)).
The layout therefore stays inside the measured shapes: a version dir that holds the manifest alone, one that ships only files shadowing a `common/` copy, or the shipped one, a version dir carrying the manifest and the options file beside a `common/` tree, which booted clean on both sides and, staged, on a two-client session ([#2746/M/n=1], [#3316/M/n=1]).
The day a build needs its own copy of a file, the `common/` copy it shadows becomes unexecuted code on that build, as read on one mod in one session, and the corpus mod that ships that shape carries shadowed copies calling members this build removed ([#1086/M/n=1], [lua-platform.md#removed-apis](../platform/lua-platform.md#removed-apis)).
Such a copy is deleted or kept building against the live copy's interface, because nothing in the mod would notice if the merge ever ran the other way.

As shipped, the mod's folder holds `42.20.4/`, which carries `mod.info` and `media/sandbox-options.txt`, and `common/`, which carries every Lua file and the translation files, with the four EN translation files sitting at vanilla Translate paths, where they merge key by key [#1318/M/n=1], and no other file at a vanilla relative path.
The version dir is named for the build its files were verified on, `42.20.4`, because the resolver scores a name as the major times 1000 plus the minor and ignores the third component, so that dir is read on this build and on every later one until a newer-named dir ships [#0826/C/C-only].
That shape, a version dir shipping a file that collides with nothing, booted clean on both sides in the acceptance session [#2746/M/n=1].
A mod option declared only in the version dir's `media/sandbox-options.txt`, a file colliding with nothing in `common/`, loaded: `NR.Severity` 1.5 set in the server's sandbox file read 1.5 as the mod's server option and as `SandboxVars.NR.Severity` on the server and both clients, against 1 on a control boot with no override. [#3361/M/n=1]
The staged 1.0.0 build, the folder `tools/release_pack.py stage` writes from this tree, matched the repository byte for byte: 65 files staged, each equal by sha256 to its repository twin and to its manifest entry, and the copies the harness placed for the server and both clients equal too [#3315/M/n=1].
Booted, that build printed one self-report line on the server, reading `itemPass=true`, `legacyMirror=on`, `hook=true`, `limitations=9` and `nutritionOn=false` at the options' defaults [#3312/M/n=1].
Each client printed one line of its own, reading `itemPass=true` and `frameworks=none` with no MoodleFramework installed [#3313/M/n=1].
Which files ship in the version dir is settled as that measured shape: the manifest and `media/sandbox-options.txt` in `42.20.4/`, everything else in `common/`, and no `common/` file shadowed by a version-dir file ([#3315/M/n=1], [#2746/M/n=1]).
The manifest declares `versionMin=42.20.4` and no `versionMax`, so a server older than the verified build drops the mod with the line an absent folder prints and the operator guide names that failure mode ([#0812/C/C-only], [#0872/C/C-only]).
The operator guide, the release notes and the compatibility table ship at the mod folder's root and travel with the item, the staged copy carrying them as it carries every other file [#3315/M/n=1].

The version dir's name is read as a build number, and the resolver's rules decide which dir a later build takes, which the [shelf-life reading](#shelf-life) below follows through ([#0825/C/C-only], [#0826/C/C-only]).
Two names the resolver scores alike have no declared winner, the tie going to the directory listing, so the layout never ships two version dirs that a third version component alone separates [#0880/C/C-only].

Inside `media/` the file map treats every file alike: one absolute path per relative path, and a script walk that drops a repeat ([#1046], [loader-and-scripts.md#file-map](../platform/loader-and-scripts.md#file-map)).
Every relative path this mod ships is therefore a claim on a slot another mod could also want, and the only defence the loader offers is a path nobody else uses.
The item pass's script files take mod-unique basenames with no `template_` prefix, for the reasons [the item pass](item-pass.md#walls) gives ([#1047/C/C-only], [#1233/C/C-only]).
No corpus mod keeps a nutrition key under `common/`, so a pass whose script files sit there has the loader's two-pass reading behind it and no shipped precedent ([#1561/C/snapshot], [#0827/C/C-only]).
The Lua tree takes the folder names the game uses, and the `server/` folder is no boundary: a `server/` file runs in the client's Lua state too, so every one carries a runtime side test ([#1174/M/n=1], [overview.md#two-lua-states](../platform/overview.md#two-lua-states)).
A script hook's target is a global defined in a `shared/` file for the same reason, which [the hook page](eat-and-cook-hooks.md) reads in full [#0927/C/C-only].
Item names ship in the B42 table layout, the only one this build reads, and they matter on the client alone, because a dedicated server resolves no mod item's display name ([#1025/M/n=1], [#1167/M/n=1], [#3206/M/n=2], [mod-anatomy.md#translations](../platform/mod-anatomy.md#translations)).
Every code path the mod runs is a file in this tree at load time, because no route on this build lets mod Lua compile a string into code ([#1172/C/C-only], [lua-platform.md#removed-apis](../platform/lua-platform.md#removed-apis)).
A per-item handler, or a formula a server operator writes, is therefore data read by a handler the mod ships and never code the mod generates.

The manifest declares what the loader acts on and nothing it ignores.
`require=` is the one load-order key a dedicated server honours, and a missing or gated requirement takes the requiring mod down with it ([#0811/C/C-only], [mod-anatomy.md#load-order-declarations](../platform/mod-anatomy.md#load-order-declarations)).
Every `require=` this mod declares is therefore a mod the server must run for this one to load at all, which makes a dependency a deployment requirement rather than a preference.
`loadModBefore=`, `loadModAfter=` and `incompatible=` change nothing on a dedicated server, so none of them is a compatibility tool ([#0814/C/C-only], [#0813/C/C-only]).
A version gate is a hard gate that reports exactly as an absent folder does, and whether to declare one is a question the [shelf life](#shelf-life) poses ([#0812/C/C-only], [#0872/C/C-only]).
A mod the server names and cannot find does not fail the boot: the server boots with zero errors and a client joins with the mod simply inactive ([#1817/M/n=1], [mod-anatomy.md#missing-mod](../platform/mod-anatomy.md#missing-mod)).
A gated mod and a mod missing a requirement take the same code path, because all three states print one not-found line and drop the id before any mod loads, so the clean boot measured for an absent folder carries over to them by that path rather than by a run of their own [#0871/C/C-only, #0872/C/C-only, #1817/M/n=1].
None of those states stops the server or a joining player, so a server that has lost this mod runs clean on vanilla numbers, and a mod whose requirement is absent is simply not there.
A joining client runs the server's list rather than its own, so a player's local enable of this mod proves nothing about what a session ran ([#0876/C/C-only], [mod-anatomy.md#join](../platform/mod-anatomy.md#join)).
Before any server boots, the layout lint checks the folder against these rules, its missing-version-dir error kept stricter than the engine on purpose for this project's own mods ([#0858/C/snapshot], [tools.md#mod-lint](../reference/tools.md#mod-lint)).

<a id="checksum-plan"></a>
### What this mod does about the checksum gate

Every script file this mod ships is hashed at load and compared at the join, so the item pass reaches a multiplayer server only on the gate's terms ([#1182/C/C-only], [mod-anatomy.md#checksum-gate](../platform/mod-anatomy.md#checksum-gate)).
What the gate hashes, the one difference it forgives, how each side acts on a mismatch and what a bypass role clears are the anatomy page's, and this section is the plan against them.
The gate has three arms, one per checksum flag a bypass role clears, and the anatomy page reads the script arm and leaves the Lua and animation arms outside its coverage ([#1230/C/C-only], [mod-anatomy.md#walls](../platform/mod-anatomy.md#walls)).
The plan is one answer applied to all three: the server and every client load the same bytes, from one build of the mod, so no arm has a difference to find.

The script arm is the one this mod is certain to meet, because the item pass is script data by design, and script data is free at run time only at the price of this gate ([#1243/M/n=1], [loader-and-scripts.md#per-side-load](../platform/loader-and-scripts.md#per-side-load)).
The pass's script files are generated once and published as they stand: a server's copy is never edited by hand and the generator is never re-run on one machine alone, because any byte the two copies disagree on is a disconnect rather than a degraded item [#1182/C/C-only].
A conversion of line endings between the repository and the published item is the one change the plan can ignore, because the gate's one tolerance covers it [#1182/C/C-only].
An editor that adds a byte-order mark or trims trailing space is not harmless in the same way, so the published files are the generator's output and nothing else.
The hash covers every script file the session loads rather than this mod's alone, and the set a joining client loads is the server's `Mods=` list rather than its own, so this mod keeps its own files identical and can do nothing about a neighbour's ([#1182/C/C-only], [#0876/C/C-only]).

A Workshop update is where the plan is most likely to fail, because an update is the one moment the bytes change legitimately.
Steam rewrites the tree inside a Workshop item underneath an install, so a client that has taken an update and a server still running the old files meet at the join with two different hashes ([#1841/C/snapshot], [#1182/C/C-only]).
Every update that touches a script file is therefore a server event, reaching players cleanly only once the server and its clients run the same version: a probe mod whose two copies differed by one byte disconnected its client without reaching the game, though no Workshop update itself has been run [#1282/M/n=1].
A mismatch surfaces as a disconnect, with the two sides' separate arms acting at their own times, which the anatomy page states [#1231/C/C-only].
A player who cannot stay connected after an update is therefore this section's failure mode before it is anyone else's.
How the script files reach every side as one set of bytes is settled as staging from one command: the staged tree is the only copy a server or a client is given, and the harness deployed it to the server and both clients with all 65 files equal ([#3315/M/n=1], [#3314/M/n=1]).
A release tool can hash every script file with the gate's own tolerance, every CR byte dropped, and name the files whose hash moved between two releases, so an update that will fail the join checksum is known before it ships [#3325/C/inference].

The bypass role is an operator's lever, and the plan never leans on it.
A role that clears the flags seats a client whose scripts differ, and because each side keeps the definitions it loaded with nothing reconciling them, that client plays on item values the server does not hold ([#1230/C/C-only], [#3139/M/n=1], [#0648/C/inference]).
The bypass turns a loud failure into a silent disagreement over exactly the numbers this mod exists to set.

The Lua and animation arms are unread, so the plan treats them as if they gated.
The mod's Lua ships under the same one-build discipline as its scripts, and a nutrition overhaul has no reason to ship an animation at all.
Whichever way the unread arms turn out, nothing this mod ships differs between the two sides.

The plan's premise is measured: a client whose copy of one script file differed by one byte was disconnected before it reached the game, while a copy differing only in line endings joined and stayed ([#1282/M/n=1], [#3138/M/n=1], [mod-anatomy.md#checksum-gate](../platform/mod-anatomy.md#checksum-gate)).
So the item pass reaches a multiplayer server exactly when the bytes agree, and the plan is a requirement a run has shown for one probe file rather than a precaution.
The staged 1.0.0 build met the gate on the two-client fixture: the release client `bob` reached ready 40.8 s after its launch and the mod's player adapter saw it, and neither the server log nor `bob`'s console carried a checksum line naming a mismatch, a kick or a disconnect, and `bob` sat in the server's player list when it was read [#3314/M/n=1].

<a id="resident-stack"></a>
### The mods beside it on a live server

The mods that will sit beside this one are the server's approved list, which is the installed corpus the catalog sweeps, and it offers no vanilla food override at all [#1674/C/snapshot].
Every nutrition-bearing script block in it adds a new item, so the item pass contests no food key with any resident mod, a census taken over the script-signalled mods only ([#1595/C/snapshot], [catalog.md#corpus-facts](../facts/other-mods/catalog.md#corpus-facts)).
What the residents touch instead is the ground around the pass: the vanilla Lua files, the command bus, the player's modData table, the calorie store, the status screens and the numbers the pass moves.
Build status rules none of the nutrition-signalled residents out: every one resolves a version folder this build reads and none lints at error level [#1645/C/snapshot].
Every reading below is a static read of shipped files on a dated sweep, and none of these mods was booted beside this one ([catalog.md#walls](../facts/other-mods/catalog.md#walls)).

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

The one resident this library knows to hold vanilla Lua paths wholesale is the interface mod, most of whose live tree replaces vanilla files [#1457/C/snapshot].
A file of this mod at a path it already holds would lose to it or displace it whole, decided by the load order, with the loader's `overrides` print the only witness ([#1173/C/C-only], [#1176/C/C-only], [loader-and-scripts.md#file-map](../platform/loader-and-scripts.md#file-map)).
Its fork of the inventory context-menu file also means a vanilla change to that menu never reaches a server running it, whatever this mod ships [#1371/C/snapshot].
With it resident, a raising listener on that menu's event shows as the interface mod's own printed failure line rather than a raw error, which is the form a driver's grep has to expect ([#1369/C/C-only], [autocook.md#compat](../facts/other-mods/autocook.md#compat)).

Four more surfaces are shared with residents, and packaging acts on none of them: the bus namespace, the player's modData table, the calorie store and the numbers a viewer draws.
The bus namespace is the cheapest to keep apart, with a module name nobody else uses ([#1153/C/C-only], [mp-sync.md#failure-modes](mp-sync.md#failure-modes)).
The player's modData table is not, because a client-only viewer rewrites the server's whole copy of it from its own input handlers, and the route that survives that is [the MP sync page's](mp-sync.md#sync-options) [#1482].
The calorie store is shared with a trait mod whose server handler runs every tick and writes each player once every five seconds outside its weight band, measured reaching the store under a co-boot, and whether this mod writes over it or registers with it is [the nutrient page's](new-nutrients.md) question ([#1588], [#2091/M/n=1], [#1070/C/snapshot]).
The viewers — a status bar and a cooking automation — define nothing this mod could contradict and read everything it moves, so a rebalance reaches them unannounced ([#1522], [#1377/C/snapshot]).
A skill mod's protein ladder would join them only once its author wires it, since the shipped ladder sits under a not-yet-implemented marker with its other copy block-commented, which a re-read of the live tree on 2026-10-04 found unchanged ([#1584], [#2092/C/snapshot/unverified]).

A neighbour's failure reaches this mod only as far as the dispatch that carries it.
An unguarded raise aborts the rest of the raising handler's body while the handlers behind it keep running, so this mod's own handlers on the same event survive a neighbour's raise, while a call this mod makes into a neighbour's code needs a protected call of its own — measured on the server's Lua state and, since x202, on a release client [#1179/M/n=1] [#3317/M/n=1].
Whether the interface mod's protected dispatch changes that inside its own event is a resident run-time question with a probe of its own ([#1292/C/open], [open-questions.md#x26](open-questions.md#x26)).

The residents' own foods are the item pass's boundary: a base-module pass does not touch a food another mod declares in its own module, and a block naming one is an override only while that mod loads ([#1030/M/n=1], [item-pass.md#scope](item-pass.md#scope)).
Whether this mod reaches them is an item-pass decision, and how it ships a block that does is the patch-mod row of [the options](#compat-options).
Two resident Workshop items ship several mods each, so a server names a mod by its id rather than by its item, and a second folder can ride one Workshop item beside the first ([#1543/C/snapshot], [#1617/C/snapshot]).

Three kinds of neighbour are absent from the installed tree altogether: a public fix for the multiplayer nutrition-sync problem, a third-party patch to the preservation mod, and the page of public nutrition overhauls the nutrition search term returns ([#1605/W/snapshot], [#1606/W/snapshot], [#1599/W/snapshot]).
A row that is not installed cannot be linted, profiled or measured, so what any of them replaces, shadows or transmits is unread until someone subscribes to it and re-runs the inventory [#1600].
The decisions they block are listed under [Open](#open).

<a id="sharing-a-server"></a>
### Sharing a server

Past files and ids, the residents meet this mod at seats the loader never arbitrates: the stat hook, the eat action, an optional framework and the sandbox option names.
The residents' readings below are static reads of the installed tree on its dated sweep, the engine's are reads of the bytecode, and none of it was booted beside this mod ([catalog.md#walls](../facts/other-mods/catalog.md#walls)).

The stat hook is unclaimed on the dated sweep: no live version folder in the installed corpus references it or the hook manager, and the corpus's only hook call is the interface mod's pair on the auto-drink hook, carried over from vanilla [#2558/C/snapshot].
That reading covers the installed tree alone, so a public item that claims the hook and is not installed stays unread, as [the catalog's open lines](../facts/other-mods/catalog.md#open) carry.

The eat action is already shared: every resident that touches its methods wraps them, `QualityCooking` on the server, `EmergencyVomitB42` on the client and `SomewhatTraitsCore` in shared code, and only `EmergencyVomitB42`'s wraps sit behind an idempotency sentinel [#2566/C/snapshot].
`QualityCooking`'s server wrap saves the original completion into a local and redefines the method unconditionally [#2562/C/snapshot].
A wrapper this mod adds to the same completion joins a chain whose order is the load order, and which seat in the eat it needs is [the hook page's](eat-and-cook-hooks.md#seat-in-the-order) reading.
None of those wraps is a file collision, so no packaging lever separates them, and the description is the one place that tells an operator they share a seat.

An optional framework is detected, never required.
`MoodleFramework` defines its global at file-load time, so a type test on that global and its creation function at `OnGameBoot` or later finds it, while a `require` of its file finds nothing when the framework is absent [#2547/C/inference].
A test at this mod's own file scope can run before the framework's file does, which is why the test waits for the event ([loader-and-scripts.md#lua-load-order](../platform/loader-and-scripts.md#lua-load-order)).
Detecting by type keeps the framework out of `require=`, so a server without it still loads this mod, and the self-report line the rules ask for is where an operator reads which way the detection went.

The mod's own sandbox options ship in one declaration file, in the version dir or in `common/`, and the loader reads exactly one of the two per mod [#2422/C/C-only].
A file at the mod root's own `media/` is never read on this build [#2423/C/C-only].
The declaration file therefore follows the layout's split: it sits in `common/` while it holds for every build, and moves whole into a version dir the day one build needs its own, because a version dir's copy is the only one that build reads.
Its option names are shared with every other mod on the server, and the engine does not reject a duplicate: two mods declaring the same prefix and short name collide silently [#2437/C/C-only].
The prefix is a namespace the mod picks as it picks its bus module name, one no resident uses ([sandbox-options.md#declaration](../platform/sandbox-options.md#declaration)).

<a id="shelf-life"></a>
### The stamp is a shelf life

The stamp at the head of this page names one build and one day, and it is a shelf life rather than a date of writing.
The game and the Workshop tree both move on, so a reading here holds for the build it names and for the corpus as it stood on its sweep ([lessons.md#corpus-drift](../platform/lessons.md#corpus-drift)).
Steam rewrites the tree inside a Workshop item without touching the item's own folder, so a folder's age is no check of how stale its contents are [#1841/C/snapshot].
Every corpus count this page leans on is dated for that reason, and a recount is a new reading rather than a confirmation of the old one [#1964/C/snapshot].
A line cite into a neighbour drifts the same way without becoming wrong, and it is re-located by content before it is quoted [#1466/C/snapshot].

A build bump does not stop this mod from loading, and that is the hazard.
The resolver picks the highest version dir at or below the running build, so the dir this mod ships for this build goes on being picked on every later build until a newer-named one exists [#0825/C/C-only].
The mod therefore keeps loading, unverified, on a build nobody tested it against, and nothing in the log says so.
A version dir named for a later build is the opposite trap: it is never read until that build ships, and then runs untested the moment it does [#0825/C/C-only].
The two manifest keys that pin availability close the first trap and open a failure mode of their own, because a build outside the declared range reports exactly as an absent folder, so an operator reads a gated mod as a missing one ([#0812/C/C-only], [#1177/C/C-only], [mod-anatomy.md#build-pinning](../platform/mod-anatomy.md#build-pinning)).
This library read no Lua route by which a mod learns the running build number, so no route it knows lets the mod check its own shelf life at run time ([mod-anatomy.md#walls](../platform/mod-anatomy.md#walls)).
The layout lint sees neither trap, because its model of the live version folder ignores the running build's ceiling ([#0864/C/snapshot], [tools.md#mod-lint](../reference/tools.md#mod-lint)).
Its agreement check exists for the same moment: a flagged `mod.info` becomes the authoritative one when the version dir's copy is removed or the build moves past that version dir [#0861/C/C-only].

What has to be re-read after a bump follows from what this mod rests on, in order of consequence.
The checksum gate comes first, because it was measured on one build and is otherwise a reading of that build's jar, and it decides whether the mod can join a server at all ([#1282/M/n=1], [#1231/C/C-only]).
The removed members come second: a member this mod calls that a build removes is a nil call that aborts the body it fires in, and this build already removed members the corpus still calls ([#0961/M/n=1], [#0962/M/n=1], [lua-platform.md#removed-apis](../platform/lua-platform.md#removed-apis)).
The per-key merge and the replay order come third, since the item pass stands on both and each was measured on this build alone ([#1180/M/n=1], [#1183/M/n=2]).
The packet field lists come fourth, because every desync the multiplayer page reads is a property of one build's field list ([mp-sync.md#failure-modes](mp-sync.md#failure-modes)).
The dataset comes last: the pass is generated from a scan of one build, so a later build's foods reach it only after a re-scan ([item-pass.md#scope](item-pass.md#scope)).
Each of those has a jar read, a named experiment or a scan behind it, which makes a build bump a known list of checks rather than an open-ended one.

## Options

<a id="compat-options"></a>
### The compatibility approaches

A resident that shares a file or a key with this mod leaves four approaches open, and they differ in who carries the cost and which wall they meet.
None of them changes a shared surface such as the bus, the player's table or the calorie store, because packaging acts on files and ids alone, and those surfaces are the routes of [the MP sync page](mp-sync.md#sync-options).
The rows follow the wall map's order.

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
- This mod survives its own or a neighbour's unguarded raise only with a workaround, a protected call at every boundary, measured on the server's Lua state and, since x202, on a release client [#1179/M/n=1] [#3317/M/n=1].
- A mod can rely on the replay order, which is the stored script path rather than `require=` or `Mods=`, so a patch mod wins a contested key only through its own file names [#1183/M/n=2].
- Every reading of the resident stack is a static read of a dated snapshot of an installed tree that drifts, and no two resident mods were booted together ([#1964/C/snapshot], [catalog.md#walls](../facts/other-mods/catalog.md#walls)).

Not covered: the Steam Workshop upload, subscription and update surface, including any version check the Workshop makes of its own; the Lua and animation arms of the checksum gate; a listen server and the client's own mod selector; any Lua route to the running build number; and every neighbour that is not installed — this library read none of them.

## Open
<a id="open"></a>

- Whether two mods at one relative path both load, for a script file and for a Lua file, and whether a mod file at a vanilla relative script path is dropped entirely — settled by two mods shipping the same relative paths with different content, reading which item and which global survive, plus a boot that ships a mod file at a vanilla relative script path; until then the shadow and do-nothing rows of the options rest on the loader's code; -> X20 ([#1286/C/open], [open-questions.md#x20](open-questions.md#x20)).
- Whether a folder whose only `mod.info` is `common/mod.info` resolves under the requested-id lookup, and whether the client's own mod-list call site agrees with the dedicated server's — settled by a purpose-built mod carrying `common/mod.info` and nothing else, its verify gate on the server side only, read on both sides; until then this mod keeps its `mod.info` in the version dir; -> X21 ([#1287/C/open, #0823/C/C-only/open, #0877/C/C-only/open], [open-questions.md#x21](open-questions.md#x21)).
- Whether a shadowed `common/` copy ever executes — settled by a mod whose `common/` and version dir each ship a colliding and a non-colliding file, with a sentinel only the shadowed copy can set; the other half of X22 is settled for the shipped shape, a version dir whose `media/` collides with nothing, whose options file loaded (the option read 1.5 on the server and both clients) [#3361/M/n=1]; until the shadow arm runs the layout keeps its version dir to the manifest, the options file and files that shadow a `common/` copy, the shapes a boot has covered; -> X22 ([#1288/C/open, #0835/M/n=2/open], [open-questions.md#x22](open-questions.md#x22)).
- Whether the interface mod's protected dispatch changes what an unguarded raise does inside it — settled by one session that drives the interface mod's context-menu entry through a harness addition, reading that mod's own printed failure line and whether the handlers behind the raiser ran; -> X26 ([#1292/C/open], [open-questions.md#x26](open-questions.md#x26)).
- Decision: which compatibility approach this mod takes toward each resident it shares a file or a key with — settled for the residents read, the five Workshop neighbours' code unread (3690404044, 2997722072, 3415375593, 3736275816, 3694097672; deferred on 2026-10-06: the item is not subscribed), and forced by the loader keeping one file per relative path and the replay deciding a contested key by the stored script path ([#1173/C/C-only], [#1183/M/n=2]).
- Decision: whether a patch mod, if one ships, rides this mod's Workshop item as a second folder or an item of its own — waits on the neighbour reads (3690404044, 2997722072, 3415375593, 3736275816, 3694097672; deferred on 2026-10-06: the item is not subscribed) and is forced by a server naming mods by id and resident items already shipping several mods each ([#1219/C/C-only], [#1543/C/snapshot]).
- Decision: whether this mod ships beside a public fix for the multiplayer nutrition-sync problem on one server — forced by that fix working on the same problem this mod's own state routes answer, and blocked by the fix being uninstalled, so what it replaces, shadows or transmits is unread until someone subscribes to it (3736275816; deferred on 2026-10-06: the item is not subscribed) and re-runs the inventory ([#1605/W/snapshot], [#1600], [catalog.md#walls](../facts/other-mods/catalog.md#walls)).
- Decision: whether a block of this mod naming the preservation mod's foods can coexist with the third-party patch that claims that mod launders nutrition — blocked by the patch being uninstalled (3796644824; deferred on 2026-10-06: the item is not subscribed), and forced by a block naming another mod's food being an override only while that mod loads ([#1606/W/snapshot], [#1030/M/n=1], [#1600]).
- Decision: whether this mod is built to share a server with any public nutrition overhaul — blocked by none of the nutrition term's results being installed (3690404044; deferred on 2026-10-06: the item is not subscribed), and forced by `incompatible=` stopping nothing on a server ([#1599/W/snapshot], [#0813/C/C-only]).
- The five subscribe-and-read code reads (Nutrition Makes Sense 3690404044, StatsAPI 2997722072, Stat Tweaks Lib 3415375593, ApocalipseBR Nutrition Sync Fix 3736275816, Tooltiplib 3694097672) are unrun: none is installed — settled by subscribing and reading each against its one question (spec § 4.9) ([#1599/W/snapshot]).

## Worked examples

| shape | file:lines | what it shows |
|---|---|---|
| a version dir holding only the manifest | `testing/experiments/TKX_CommonOnly/42.20/mod.info:1-5` | five keys and no `media/` beside them — the empty-version-dir arm this layout stays inside |
| the whole payload under `common/` | `testing/experiments/TKX_CommonOnly/common/media/lua/shared/TKX_CommonOnly.lua:1-4` | the one file of that mod, which still loads and resolves on both sides with the version dir empty |
| a script file under a mod-unique basename | `testing/experiments/TKX_ItemOverride/42.20/media/scripts/tkx_item_override.txt:24-29` | the partial `item Orange` block, in a file whose relative path no other mod ships |
| an item-name table in the B42 layout | `testing/experiments/TKX_ItemOverride/42.20/media/lua/shared/Translate/EN/ItemName.json:1-3` | a bare `Module.Name` key, the only item-name layout this build reads |

## See also

- [`../platform/mod-anatomy.md`](../platform/mod-anatomy.md#checksum-gate) — the id chain, the version dirs, the missing-mod failure, build pinning and the checksum gate every reading here cites.
- [`../platform/loader-and-scripts.md`](../platform/loader-and-scripts.md#file-map) — the file map, the path collisions and the per-side load the layout and the options rest on.
- [`../platform/lessons.md`](../platform/lessons.md#corpus-drift) — the layout rule, the shadowed-copy filter and why every corpus count carries a date.
- [`../facts/other-mods/catalog.md`](../facts/other-mods/catalog.md#corpus-facts) — the resident mods, what each touches, and the Workshop neighbours that are not installed.
- [`../facts/other-mods/autocook.md`](../facts/other-mods/autocook.md#compat) — the corpus's `common/` case and its collisions with the interface mod.
- [`../facts/other-mods/simplestatus.md`](../facts/other-mods/simplestatus.md#compat) — the client-only viewer a rebalance miscalibrates.
- [`../facts/other-mods/longtermpreservation.md`](../facts/other-mods/longtermpreservation.md#compat) — the resident whose own-module foods sit outside the pass.
- [`../reference/tools.md`](../reference/tools.md#mod-lint) — the layout lint that checks this mod's folder before any boot.
- [`../platform/sandbox-options.md`](../platform/sandbox-options.md#declaration) — the declaration file's location and the option names the mod shares with every other mod.
- [`../facts/other-mods/moodleframework.md`](../facts/other-mods/moodleframework.md#techniques) — the framework a type test detects.
- [`eat-and-cook-hooks.md`](eat-and-cook-hooks.md#seat-in-the-order) — the eat seat the residents' wraps already share.
- [`../reference/wall-map.md`](../reference/wall-map.md) — the verdict rows the walls cite by id.
- [`item-pass.md`](item-pass.md) — the script files this page packages, and the checksum they ship under.
- [`mp-sync.md`](mp-sync.md) — the shared surfaces packaging cannot separate: the bus, the player's table and the routes between them.
- [`ui-and-moodles.md`](ui-and-moodles.md) — the rendering route beside the resident interface mod.
- [`new-nutrients.md`](new-nutrients.md) — the calorie store a resident trait mod also writes.
- [`open-questions.md`](open-questions.md) — the experiments this page's open rows point at.
