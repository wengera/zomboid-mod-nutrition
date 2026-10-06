# Mod anatomy
Verified against 42.20.4 (b0bbce05d5) · 2026-10-06 · scope: what a mod folder is on this build — `mod.info` and its keys, how the game finds a folder, which file supplies the id, the version dir against `common/`, translations, the missing-mod and version-gate failures, the join, the checksum gate and a one-sided mod; the block-level script merge and the Lua execution list are handed off to `loader-and-scripts.md`.

## Rules

- Declare one id per mod folder and put it in the build's version dir: the loader parses that one `mod.info` and never the folder name, so a second `mod.info` with another id is unaddressable [#0802/C/C-only, #0881/M].
- Ship `common/` beside the version dir and keep only the build-specific files in the version dir: the version dir's file wins a same-relative-path collision and `common/` supplies everything the version dir does not ship [#1318/M/n=1].
- Give a build-independent payload a version dir holding nothing but a `mod.info`: an empty version dir costs the mod nothing and the `common/` tree still runs [#0831/M/n=1].
- Address a mod by its declared id and never by its folder name: `Mods=` resolves ids in a pass that completes before any mod loads, and a folder whose name matches no id loads normally [#1219/C/C-only, #1116/M/n=2].
- Use `require=` when one mod must load before another: it is the only load-order declaration the loader acts on, and `loadModBefore=` and `loadModAfter=` only arrange rows in the client's mod selector [#0811/C/C-only, #0814/C/C-only].
- Spell every `mod.info` key exactly and keep another key's token out of a value: keys are case-sensitive and the parser tests `contains` and strips by replace, so a value carrying an earlier branch's token is eaten by that branch [#0807/C/C-only, #0806/C/C-only].
- Read a mod's `mod.info` rather than the loader's error text when a mod does not load: a failed `versionMin` or `versionMax` gate, a missing `require=` and a folder that is not there all print the same not-found line [#0872/C/C-only, #0812/C/C-only].
- Treat a not-found warning as a failed run rather than a warning: the server boots with zero errors and the client joins and spawns with the mod simply inactive, so every probe still answers and the run reads green [#1817/M/n=1].
- Ship a mod's item names in a B42 `ItemName.json` whose keys are the bare `Module.Name`: the B41 `ItemName_EN` table layout produces no name at all on this build [#1025/M/n=1].
- Never branch on an item's display name server-side or reach for one through `getText`: a dedicated server resolves no mod display name and the text router carries no item-name prefix [#1026/M/n=2].
- Expect a mod translation to add keys and to win for a key it redefines, without displacing vanilla's other keys: the reader merges into a shared map key by key and a non-empty mod value overwrites vanilla's [#3210/C/inference, #3201/M/n=1].
- Ship byte-identical script files on both sides of a multiplayer session: the gate hashes file content with every CR byte dropped, so a mismatch is a disconnect rather than a silent degrade [#1182/C/C-only, #1231/C/C-only].
- Give a client-only mod no server-side Lua rather than trusting a folder name: a dedicated server still installs the mod and loads its shared translation tree [#1504/C/snapshot, #1474/C/snapshot].
- Copy a mod into each cachedir's own `mods` folder for a no-Steam launch: the workshop and steam roots are resolved through calls gated on Steam mode, leaving one root [#1802/C/C-only].
- Keep one id to one installed folder: on a duplicate the loader keeps whichever folder comes earlier in the discovered list, so a local copy never beats a workshop copy [#0875/C/C-only].
- Seed the per-major-release marker file beside the enabled-mods list: the game writes that marker and wipes the list on a first launch that finds it missing [#1853].
- Date every count taken over the installed mod corpus: the key census is a dated snapshot of a tree Steam rewrites underneath it [#0805/C/snapshot].

## How it works

<a id="mod-info-keys"></a>
### `mod.info` and the keys the loader reads

`ChooseGameInfo.readModInfoAux` is a line scanner that tests whether each line contains `<key>=` in a fixed branch order, strips the token with a string replace and stores the rest; it recognises 17 keys plus `type=` nested inside a `pack=` block and silently ignores every other line [#0804/C/C-only].
Because the parser tests `contains` rather than a prefix and strips with a string replace rather than a prefix cut, a value carrying an earlier branch's token is eaten by that branch — `url=https://x/name=1` is parsed as a `name` — and every occurrence of the token disappears from the stored value [#0806/C/C-only].
`mod.info` keys are case-sensitive, which is why `modVersion=` is dropped [#0807/C/C-only].
An unrecognised line is neither an error nor a log entry, so a misspelled key is invisible until whatever it was meant to buy turns out to be missing [#0804/C/C-only].
Eight key spellings shipped by installed mods are not parsed at all because no branch tests them, in folder counts taken over the corpus on 2026-09-11: `authors` (11 folders), `modVersion` and `version` (2 each), `tags` (15), `pzversion` (10), `texts`, `supports` and `zoomX/Y/S` (1 each) [#0815/C/snapshot].
The `id` key is the only handle a mod has: `Mods=` entries, `require=` entries and `ChooseGameInfo.Mods` are all keyed on it, and `loadMod` prints `loading <id>` from it, with 229 of the 230 installed folders counted on 2026-09-11 declaring one [#0808/M/n=1].
Every experiment mod of this library ships exactly `name`, `id`, `description`, `modversion` and `versionMin` and nothing else, and across 8 mods declaring 9 ids every addressable id resolved and every mod loaded [#0816/M/n=1].

The `mod.info` key census over 230 installed mod folders is 17 recognised keys with their per-key folder counts and what the loader does with each, counting every `mod.info` found under each folder including out-of-chain copies, as of 2026-09-11 [#0805/C/snapshot].

| Key | Mods | What acts on it |
|---|---:|---|
| `id` | 229 | the only handle that exists. `Mods=` entries, `require=` entries and `ChooseGameInfo.Mods` are all keyed on it; `loadMod` prints `loading <id>` |
| `name` | 229 | display only (mod selector). `Translator.readModTranslation` lets a mod's own `Mod.json` translate it |
| `description` | 227 | display only; same translation path |
| `poster` | 224 | resolved against the version dir first, then `common/`; a path ending `poster.png` is gated out of the `overrides` print |
| `icon` | 203 | display only |
| `require` | 135 | **load order + availability.** `loadModAndRequired` loads every required id first; `Mod.isAvailableRequired` makes the *requiring* mod unavailable if any required id is missing or version-gated |
| `author` / `authors` | 176 / 11 | `author` is parsed and displayed; **`authors` is not a key** — 11 folders ship it and it is dropped |
| `versionMin` | 154 | **a hard gate, not a note.** `Mod.isAvailableSelf` returns false when `versionMin > build`, `getAvailableModDetails` then returns null, and the mod reports as `required mod "<id>" not found` |
| `versionMax` | 13 | same gate, other end |
| `category` | 108 | display only (mod selector filter) |
| `modversion` | 45 | display only. **`modVersion` and `version` are not keys** — 2 folders each, dropped |
| `pack` (+ `type=`) / `tiledef` | 16 / 12 | `addPack` / `addTileDef`; consumed by `loadModPackFiles` / `loadModTileDefs`, which warn `pack file "<f>" needed by <id> not found` |
| `incompatible` | 12 | **display only.** `getIncompatible` is called from exactly two places in the whole jar-plus-Lua tree, **both mod-selector UI**; no jar class but the declaring `ChooseGameInfo$Mod` so much as names it. A server's `Mods=` ignores it |
| `url` | 5 | display only |
| `loadModBefore` / `loadModAfter` | 1 / 1 | **advisory, client UI only.** `getLoadBefore` / `getLoadAfter` are read only by the mod selector's load-order panel and its order list box — they arrange the selector's list. The server loads in literal `Mods=` order |
| `tags`, `pzversion`, `texts`, `supports`, `zoomX/Y/S` | 15 / 10 / 1 / 1 / 1 | **not parsed at all.** No branch tests them |
| the keys this library declares | 8 mods, 9 ids | every experiment mod ships exactly `name` + `id` + `description` + `modversion` + `versionMin` and nothing else; every addressable id resolved and every mod loaded |

The census counts folders, not declarations, and it counts every `mod.info` under a folder including copies no resolver can reach, so a key's folder count is an upper bound on how many mods the loader actually reads it from.

<a id="load-order-declarations"></a>
### `Mods=` and `require=`: what each declaration guarantees

`Mods=` resolves ids, not paths, in a pass that completes before any mod loads [#1219/C/C-only].
On a dedicated server the load order is exactly the order of `Mods=`, with each entry's `require=` closure inserted ahead of it [#0817/C/C-only].
`require=` is the only load-order declaration the loader acts on: `loadModAndRequired` loads every required id first, and `Mod.isAvailableRequired` makes the requiring mod unavailable if any required id is missing or version-gated [#0811/C/C-only].
That second half is the one that bites: a `require=` naming an id the machine does not have takes the requiring mod down with it rather than degrading it.
`loadModBefore=` and `loadModAfter=` are advisory and client-UI only: `getLoadBefore` and `getLoadAfter` are read only by the mod selector's load-order panel and order list box, which arrange the selector's list, and a dedicated server loads in literal `Mods=` order [#0814/C/C-only].
`incompatible=` is display only: `getIncompatible` is called from exactly two places in the whole jar-plus-Lua tree, both mod-selector UI, no jar class but the declaring `ChooseGameInfo$Mod` so much as names it, and a server's `Mods=` ignores it [#0813/C/C-only].
So a dedicated server honours exactly one of the four ordering keys, and the three a mod author is most likely to reach for change nothing outside the client's list.
A mod that needs another mod's files to exist before its own run declares `require=`; a mod that merely prefers an order has no lever on a dedicated server at all.
The order the loader announces is not the order script bodies replay in: that sort is the stored script path and is independent of `Mods=` position, and it lives at [the sorted replay](loader-and-scripts.md#sorted-replay).

<a id="mod-discovery"></a>
### How the game finds a mod folder

Mod folders are discovered over a root order that defaults to workshop, then steam, then the local mods dir, each root walked recursively, and a directory counts as a mod folder if and only if it holds `common/mod.info`, tested first, or a `mod.info` in the version dir the name resolver picks — a discovery gate, not the id read [#0874/C/C-only].
The mod-folder acceptance test checks the `common/` copy first: `getAllModFoldersAux` accepts a folder as a mod when its `common/mod.info` exists or its version-dir `mod.info` does, and only then resolves the two media roots [#1373].
Testing `common/` first here and the version dir first at the id read is not a contradiction: one decides whether a directory is a mod at all, the other decides which file supplies its id.
Under a no-Steam launch exactly one mod root is searched, the cachedir's own `mods` folder, because the other two roots are resolved through calls gated on Steam mode; there is no server mod-folders argument, the string existing only in the main-menu state, and the workshop-items line needs Steam too [#1802/C/C-only].
Every process this library drives runs that way, so a mod reaches a run only by being copied into each side's cachedir.
The root order is a default and the resulting folder list is cached in the file system object, so what a session resolves ids against is fixed once it is built [#0874/C/C-only].
`ZomboidFileSystem.loadMods` runs two passes — a resolution pass calling `loadModAndRequired` for every requested id, then a load pass calling `loadMod` for everything the first pass accepted — so every `not found` warning precedes every `loading` line [#0870/C/C-only].
Reading a log therefore means reading the whole not-found block before the first load line, not scanning for the two interleaved.
The loader probes every mod for animation-set and action-group folders and logs a benign missing-file line per folder a mod does not ship — three for one measured mod — and a run carrying them still records zero errors [#1454/M/n=2].
Those lines are per-copied-mod baseline noise that every profile run carries, and a driver's log grep has to budget for them rather than treat them as findings.

<a id="id-chain"></a>
### The id chain: which `mod.info` supplies the id

A mod folder's id comes from exactly one file: `readModInfoAux` builds `<versionDir>/mod.info` and parses it if it exists, otherwise `<commonDir>/mod.info`, otherwise warns that it cannot find a `mod.info` in the mod dir and returns null — never the folder name, never the mod root, and never two files [#0802/C/C-only].
`ChooseGameInfo.getModDetails` resolves an id through a negative cache, then a positive cache, then the id-to-dir map; when the map has no entry it lists every mod folder and reads one `mod.info` per folder, registering one id per folder and returning as soon as the id matches [#0873/C/C-only].
On a duplicate id across two mod folders `ChooseGameInfo.readModInfo` keeps whichever folder comes earlier in the discovered folder list, so a local `mods/` copy never beats a workshop copy of the same id [#0875/C/C-only].
The two caches sitting in front of that scan remember a miss as well as a hit, so an id the negative cache already holds is answered from it rather than by another pass over the folder list [#0873/C/C-only].
Nothing anywhere in the chain consults the folder's name, which is why a folder whose name has drifted is still addressable and an id that has drifted is not.
Id resolution runs as a pass that completes before any mod loads: the failing boot's `not found` warning precedes the first `loading` line, and the succeeding boot's `loading` lines follow `Mods=` order exactly [#0820/M/n=2].
For the requested-id lookup only the version dir's `mod.info` id is addressable: with the same folder and `Mods=` naming the `common/mod.info` id the boot printed `required mod "TKX_LoaderCommon" not found`, zero `loading` and `overrides` lines, all three probe globals unresolved and no media tree walked [#0819/M/n=1].
That boot carried both `mod.info` files, so it measures addressability rather than the engine's id map, and a folder whose only `mod.info` is `common/mod.info` is untested as a purpose-built probe.
A mod folder whose only `mod.info` is `common/mod.info` does nonetheless boot in normal play: one corpus mod printed three `loading AutoCook` lines, one on the server and two on the client [#0821/M/n=1].
Four installed mods, counted over the corpus on 2026-09-11, carry `common/mod.info` as their only `mod.info`, and three of them rest on the jar fallback alone: their `versionDir` names a directory that ships no `mod.info`, so `readModInfoAux` takes `<commonDir>/mod.info` [#0822/C/snapshot].
`ZomboidFileSystem.searchForModInfo` is dead code, referenced by nothing but its own recursive call [#1220/C/C-only].
It is unreachable on `42.20.4`: a whole-jar scan finds its name only in `ZomboidFileSystem`'s constant pool, a per-method reference sweep finds the only call inside the method itself, and even its leaf branch delegates to `ChooseGameInfo.readModInfo` on the file's parent [#0803/C/C-only].
Its body, read for the record, returns the first `mod.info` whose id matches the requested id in directory-listing order rather than simply the first `mod.info` found, and every file it passes over is still registered into the id-to-directory map and appended to the caller's list [#1374].
Reading that body as the live chain is the commonest way to get this wrong: it searches several files and registers each one it meets, and the live chain from `loadMods` to `readModInfoAux` opens exactly one.

<a id="version-dirs"></a>
### The version dir against `common/`

`getModVersionDirName` lists the mod folder and keeps the entry name whose parsed version is at least `ChooseGameInfo.minRequiredVersion`, which is `GameVersion(42,0)`, and at most the running build, defaulting to `42` when nothing qualifies [#0825/C/C-only].
`getGameVersionIntFromName` parses a version folder name as major times 1000 plus the minor capped at 999, so the third component is ignored — `42.20.1` and `42.20` both score 42020 — and a non-numeric entry scores 0 and is skipped [#0826/C/C-only].
A tie in `getModVersionDirName` resolves by directory-listing order rather than by precision: the comparison keeps an entry whose score is greater than or equal to the best so far, so on a tie the last entry listed wins, and `42.20` and `42.20.1` score identically [#0880/C/C-only].
A mod that ships both names therefore has no declared winner, and on this machine's sorted listing the later name wins by accident of the file system rather than by design.
The resolver's ceiling is the running build, so a version dir named for a later build is never picked however precisely it is named [#0825/C/C-only].

`ZomboidFileSystem.loadMod` runs two passes in order — pass A over the mod's common dir, then pass B over its version dir — each ending in an unconditional `activeFileMap.put`, so the version dir's file wins a same-relative-path collision and `common/` supplies everything the version dir does not ship [#1310].
A `poster=` path is resolved against the version dir first and then `common/`, and a path ending `poster.png` is gated out of the loader's `overrides` print [#0810/C/C-only].
Measured, the version dir wins and `common/` still runs: the shadowed marker read `version` on both sides while both the `common/` and the version-dir tree markers resolved [#0828/M/n=2].
Inside one mod a same-relative-path collision resolves version-dir-wins, `common/` supplies everything the version folder does not ship, and both end up in one Lua state, translations excepted because the `Translator` merges rather than resolving through `activeFileMap` [#1048/M/n=2].
A live dedicated server printed exactly five `overrides` lines for one workshop mod — two translation JSONs shadowing vanilla in pass A, then three client Lua files shadowing `common/` in pass B — and no `.png` tail, so the mod's version dir resolved to `42.13/` rather than `42/` [#1315/M/n=1].
The client's Lua state names the winning copy: `acceptIngredient` and `baseAcceptsSpice` resolved as functions although they are defined only in the version tree, the common-only `selectPreferedFood` and `ISContinue` resolved too, and `_G.AutoCook` carried a key count of 49 — 23 file-scope scalars plus 15, 4 and 7 functions from three files — where a common-wins state reads 47 [#1316/M/n=1].
The console grep for a nil call, `HasTrait` or `getTypeString` returned 0 lines on the client and 0 on the server, and a common-wins state would have raised at three sites on the character-info window's build path, so the negative covers that whole path rather than one line [#1317/M/n=1].
A version dir holding only a `mod.info` and no `media/` costs the mod nothing: the mod announced `loading`, its payload global resolved on both sides off `common/media`, and no required-mod-not-found line was printed [#0831/M/n=1].
The same holds for a script: a mod whose only script sits under `common/media/scripts/`, beside a version dir holding only `mod.info`, had that script loaded on both sides, its `Calories = 400.0` reading 400 on an `Orange` spawned into the client's own inventory (the client reads its own script) and on the server's spawned `Base.Orange` [#3135/M/n=1].
For a mod shipping `common/` beside a version folder the version folder's file wins a same-relative-path collision, `common/` supplies everything the version folder does not ship, and both end up in one Lua state — with translations the exception, because the `Translator` merges rather than resolving through the file map [#1318/M/n=1].
The wiki's statement of the mod file order — `common/` first, then the closest versioning folder, overwriting — agrees with the measurement [#0833/W/one-side].

This is the file-level merge and it decides which absolute path a relative path names.
It is path-granular, so a file at a shared relative path replaces the whole file at that path and never part of one.
The map itself, and the `overrides` line the loader prints before each overwriting put — the only visible signal that a collision happened, and easy to misread — are [the file map](loader-and-scripts.md#file-map).
Which of two merged files executes, and in whose slot, is the execution list: that is [the Lua load order](loader-and-scripts.md#lua-load-order).
The second merge, inside a script file, where a repeated block appends and a partial block merges per key, is [the per-key merge](loader-and-scripts.md#per-key-merge) and is not restated here.

<a id="folder-name"></a>
### The folder name against the declared id

A mod folder's name is irrelevant and only the version directory's `mod.info` id is addressable [#1116/M/n=2].
The rename to the declared id is a convenience and not a requirement: a probe folder installed under a name matching neither of the two ids it declares loaded normally when the mod list named the version directory's id — the loader printed `loading TKX_LoaderVersion` and its `overrides` line, the version-dir probe global resolved, both tree markers resolved, and both media roots were walked under the renamed folder [#0818/M/n=1, #1832/M/n=1].
Both boots ran the dedicated-server path only, so the convenience reading is for `Mods=` resolution and not for the client's own mod selector.
The practical consequence is that a workshop folder whose name has drifted from its declared id is not a defect to repair; a folder whose `mod.info` id has drifted from what `Mods=` asks for is.

<a id="translations"></a>
### Translations

Only the B42 translation layout is read on this build: `Translator.tryFillMapFromFile` formats a path ending `Translate/<LANG>/<File>.json` and opens nothing else [#0839/C/C-only].
`Translator.tryFillMapFromMods` walks each mod's `common/` dir and then its version dir through the file reader [#0840/C/C-only].
It walks that pair through `tryFillMapFromFile`, which formats the translation path itself and fills one shared map key by key, so a mod's file does not replace vanilla's file and a key both define takes the later, mod's non-empty value [#3211].
Vanilla's keys survive and the mod's are added, which makes translations the one thing in a mod tree whose file does not shadow vanilla's [#3210/C/inference].
A mod may therefore add keys at a vanilla relative path without displacing vanilla's, which is the opposite of what the file map does to every other file in the tree.
A mod's value for a key vanilla already defines does displace vanilla's value: the map is filled from vanilla's folder first and from the mods after it, and the per-key fill puts any non-empty value over an existing key [#3205/C/C-only].
One session read exactly that on the client, a redefined interface key reading `TKX Type` against vanilla's `Item` and a redefined `Base.Apple` reading `TKX Apple` against `Apple` ([#3201/M/n=1], [#3202/M/n=1], [#1276/M/n=1]), beside a new interface key of the mod's that hit in the same run [#3200/M/n=1].
That exception is what the version-dir merge rule above is bounded against: everything else in a mod tree resolves through the file map, and translations do not.
A mod's own `Mod.json` can translate its displayed `name` and `description` through `Translator.readModTranslation` [#0809/C/C-only].

A B42 `ItemName.json` entry resolves on the client: the item's display name read back as its translated text against a full type of `TKX.FibreBarJson` [#0842/M/n=1].
An item whose module-qualified name has an entry in a B42 `ItemName.json`, whose keys are the bare `Module.Name` and whose filename supplies the `ItemName_` prefix, resolves its display name on the client and keeps `getActualWeightUnmodded` at its script weight of 0.3 — the display-name guard's reading rather than a weight fact [#1021/M/n=1].
A B41 `ItemName_EN.txt` entry is never loaded on this build: the item declared only there read its display name as its own full type on both sides, the untranslated signature, while the item declared in `ItemName.json` resolved on the client [#0843/M/n=1].
An item declared only in a B41 `ItemName_EN` table therefore produces no name at all, the client reading its display name equal to its full type and `getActualWeightUnmodded` 0, again the display-name guard rather than a weight fact [#1022/M/n=1].
An item with no translation entry anywhere reads the same way on the client, display name equal to full type and `getActualWeightUnmodded` 0 [#1023/M/n=1].
A dedicated server resolves no mod item's display name, JSON included: the server read the same mod item's display name as its full type on the same tick the client read the translated name ([#1024/M/n=1], [#3206/M/n=2]).
A vanilla item's name and a vanilla interface key do resolve on a dedicated server, to vanilla's strings: a server-instantiated `Base.Apple` read `Apple` and `IGUI_invpanel_Type` read vanilla's `Item` [#3203/M/n=1].
What the server lacks is the mods' values: in this run it missed the mod's new key and kept vanilla's values for the two it redefined, though its log carried the mod's `loading` line [#3204/M/n=1].
The server's `getText` route returned a hit for the vanilla interface key and a miss, the key itself, for the mod's new one [#3209/M/n=1].
`Translator.getTextInternal` is a prefix router over 25 key prefixes and `ItemName_` is not one of them; the item map is reached only by `getDisplayItemName`, which looks up the raw full type with spaces and hyphens folded to underscores [#0847/C/C-only, #1215/C/C-only].
That router is why a translation-only load probe has to be gated on a `UI_` or `IGUI_` key: those prefixes are routed, an item name is not.
Three items in one mod, one per translation state, is what makes those readings a discriminator rather than three unrelated observations, and each state was read once.
The item-name table is loaded and working on the client and is simply unreachable from the `getText` global, so a miss there says nothing about whether the table holds the key.

Ship a mod's item names in a B42 `ItemName.json` with bare `Module.Name` keys, because the B41 `ItemName_EN` table layout produces no name at all on this build [#1025/M/n=1].
Never branch on an item's display name server-side or reach for it through `getText`, because a dedicated server resolves no mod display name and neither the bare nor the prefixed `getText` key form reaches one on either side [#1026/M/n=2].
What the text route does and does not establish is bounded, and the bound is in [the open rows](#open) rather than here.

<a id="missing-mod"></a>
### A missing mod, and what the error text does not say

`loadModAndRequired` asks `ChooseGameInfo.getAvailableModDetails` for the id; on null it removes the id from the server's mod list and warns `required mod "<id>" not found`, and on success it recurses over the `require=` closure and then appends the id [#0871/C/C-only].
`getAvailableModDetails` requires `Mod.isAvailable()`, which is where a failed `versionMin` or `versionMax` gate and a missing `require=` all turn into the same `required mod "<id>" not found` text, so the error does not say which of them fired [#0872/C/C-only].
Four distinct conditions therefore share one line: an absent folder, an id nothing declares, a build outside the mod's declared range, and a dependency in either of those states.
The warning also removes the id from the server's mod list before the load pass begins, so nothing downstream of the resolution pass ever sees it [#0871/C/C-only].
The game does not fail on a mod it cannot find: the server logs a required-mod-not-found warning and boots normally with zero errors, and the client joins and spawns normally with the same warning and the mod simply inactive — which is what makes a mod-testing pipeline dangerous by default, since a profile whose mod never arrived produces a session where every probe answers and the run is green [#1817/M/n=1].
A run therefore has to assert on the loading lines it expects, not merely on the absence of errors.

<a id="build-pinning"></a>
### Pinning a mod to a build

`versionMin` and `versionMax` are hard gates, not notes: `Mod.isAvailableSelf` returns false when the build falls outside them, `getAvailableModDetails` then returns null, and the mod reports as `required mod "<id>" not found` [#0812/C/C-only].
Of the installed corpus 154 folders declare `versionMin` and 13 declare `versionMax`, counted 2026-09-11 [#0812/C/C-only].
Which end fired, and whether the mod was absent instead, the log does not distinguish — see [a missing mod](#missing-mod).
A mod declaring neither key is gated by nothing and is offered to every build, which is why a mod that must not run on an older one has to say so explicitly [#0812/C/C-only].
The build a mod pins against is the same build the version-dir resolver compares names to, so a mod pins its code by shipping a version dir per supported build and pins its availability with these two keys — the resolver is at [the version dir](#version-dirs).

<a id="join"></a>
### What a join does to the client's mod list

A running profile is a server-side decision the client inherits: the server's `Mods=` is authoritative on join and the client's own mod list is not consulted for what a joined session runs [#0876/C/C-only].
On first launch the game writes a per-major-release marker file and wipes the enabled-mods list when the marker is missing, so anything that seeds an enabled-mods list seeds the marker alongside it [#1853].
Those two together are why a client's own enabled list matters only up to the moment it connects, and why a list written without its marker is silently discarded before it is ever read.
A session is therefore only as good as the server's list, and a mod enabled locally proves nothing about what that session ran.
What the join does to the client's Lua states, and the reload that follows it, is [the two Lua states](overview.md#two-lua-states); the session shape around it is [the process model](overview.md#process-model).

<a id="checksum-gate"></a>
### The checksum gate

A mod cannot survive a multiplayer script mismatch: every loaded script file, mod files included, is fed to the checksummer, which drops every CR byte and folds the rest into one running MD5 that `ChecksumPacket.parseServer` compares, so the engine never inspects what a script says and a mismatch is a disconnect rather than a silent degrade [#1182/C/C-only].
A script-checksum mismatch disconnects the client through `NetChecksum$Comparer.update`, which calls `forceDisconnect`, `serverDisconnected` and `kickReason`, while the server arm `AntiCheatChecksumUpdate.update` acts after a 60 s grace set by `IsoWorld.LUA_CHECKSUM_TIMEOUT_MS` [#1231/C/C-only].
A role holding `Capability.BypassLuaChecksum` clears all three checksum flags [#1230/C/C-only].

Measured, a one-byte difference kicks: a `user`-role client whose copy of one script file read `Weight = 0.3` against the server's `Weight = 0.2` was warned by the server, flagged by its anti-cheat with the action `Kick`, and force-disconnected by its own arm with the reason `File doesn't match the one on the server`, naming the file, without ever reaching the game [#1282/M/n=1].
The kick is the client's arm and it is immediate: the client disconnected 0.290 s after the server's anti-cheat line, and no timeout line followed in the 157.806 s the session was watched past the warning, so the 60 s grace did not act in that window; the server recorded the kick as a `LuaChecksum` row in its user log [#3137/M/n=1].
A copy that differs only in line endings joins: the same file with every line ending CRLF connected, still answered the harness 90.437 s after its first read at ready, and left no checksum-mismatch line in either log (no `will be kicked ... checksums do not match` warning, no `Anti-cheat="ChecksumUpdate"` line, no `getReason` string) [#3138/M/n=1].
The admin role bypasses the gate in practice: the same one-byte mismatch under the fixture's `admin` role connected, still answered the harness 90.436 s after its first read at ready, and left no `user admin will be kicked in 60000ms because Lua/script checksums do not match` warning, no anti-cheat line and no user-log row [#3139/M/n=1].
The normalisation is the only tolerance the gate offers: line endings may differ between the two copies and nothing else may.
A generated script file keeps both copies identical by construction, the generator emitting one text for both and its `--check` gate comparing the file with a fresh emission [#3176/C/C-only].
The hash covers every loaded script file rather than only the mod's own, so a mod that ships no scripts at all still joins a session whose whole script set has to agree [#1182/C/C-only].
The two arms act at different times, and on a one-byte mismatch the client's arm acts first: the server's timed act is the code's backstop, which by inference a client running the shipped arm never lets it reach ([#1231/C/C-only], [#3137/M/n=1]).
Script data loads per side and never crosses the wire, which is what makes the gate necessary and is [the per-side load](loader-and-scripts.md#per-side-load).

<a id="client-only-mods"></a>
### A mod that loads on one side only

A client-only mod registers nothing and runs no code on a dedicated server: every global of one measured mod answered unresolved server-side with the failure naming its first segment, while the harness control answered on both sides in the same batch [#1331/M/n=1].
A mod can be 100 per cent client: one corpus mod has no server Lua in its live tree at all, so on a dedicated server it registers nothing and runs no code, and the only part of it the server loads is the shared translation tree [#1474/C/snapshot].
A dedicated server does install and load a client-only mod's shared translation tree, printing one `overrides` line per shipped translation file — 13 for that mod, one per language tree it ships — so the loader's word `overrides` is file-level and not a key collision, and no mod Lua runs on the server because there is none to run [#1504/C/snapshot].
The cost of being one-sided is therefore not zero on the server: the folder is still discovered, installed, walked and merged, and only the Lua is absent.
A translation tree is shared rather than client-side, which is why it is the one part of a client-only mod the server still merges.
Both readings are a snapshot of one mod tree on one sweep date, so they say what this shape costs and not how common the shape is.
The converse trap is the one that catches mods that believe a directory name is a boundary: a mod's `media/lua/server/` tree executes in the client's Lua state too, and that is [the two Lua states](overview.md#two-lua-states).

## Walls and bounds
<a id="walls"></a>

The drifted-folder boots cannot separate a folder that was never scanned from one that was scanned and rejected: the id-named folder was absent in both boots, and a mod that does not load already entails that its media roots were never mapped, so the reading is corroboration only [#0838/M/n=2].
The measured merge rule is bounded to a mod whose version directory resolves to a tree that ships colliding files; a version directory that is absent, empty or ships only files `common/` lacks is untested, and every prediction landed on its branch, so no falsifier was approached and the rule is validated as consistent with the mirror's rather than stress-tested [#1663/M/n=1].
The mirror says each version folder has its own `mod.info`, true as a permission and misleading as a plan: only one of a mod folder's `mod.info` files is ever read, so shipping two with different ids makes the other id unaddressable [#0881/M].
The mirror says the minor version is dropped, so `42.1.5` is treated as `42.1`; this repository's own `mod_lint.version_dirs` tuple-parses a three-part folder name and ranks `42.20.1` above `42.20` as itself [#1659].
Neither of those two readings is the engine's, which scores the two names identically — see [the version dir](#version-dirs).
The corpus holds two three-part version folders, both named `42.20.1` and both a Skill Recovery Journal copy, and on both the tool reading and the mirror reading choose the same folder, so nothing observable differs today [#1660/C/snapshot].
A mod shipping both `42.20` and `42.20.1` would separate those two readings and none does, so the disagreement is latent rather than live [#1660/C/snapshot].
Everything measured about the `mod.info` chain, the version dirs and the folder name was measured on the dedicated-server path, and the client's own mod-list call site, which reaches `getModDetails` from the selector rather than from `loadMods`, has never booted — the question that bound leaves is [an open row](#open) [#0877/C/C-only/open].
The checksum gate is measured on one script file of one probe mod, for a one-byte mismatch, a line-ending-only copy and the `admin` role, in one boot each on one fixture; the server's timed arm, the Lua and animation flags and any role but `user` and `admin` are code readings — see [the checksum gate](#checksum-gate) ([#1282/M/n=1], [#1231/C/C-only]).
Not covered: the mod selector's own resolution path in the client UI, the Steam subscription and upload surface, the `pack=` and `tiledef=` asset pipelines, the animation and Lua arms of the checksum gate beyond the flag count the bypass clears, and any Lua route by which a mod reads the running build number — this library read none of them.

## Open
<a id="open"></a>

- Whether the client's own mod-list call site agrees with the dedicated server's — everything measured about the `mod.info` chain, the version dirs and the folder name was measured on the dedicated-server path, and a client-side boot with a drifted folder has not been run — settled by booting the folder probe and reading the selector's own resolution; -> X21 [#0877/C/C-only/open].
- Which `mod.info` the live id chain reads when a folder holds several — the dead `searchForModInfo` body would take the first whose id matches in directory-listing order, and the live chain from `loadMods` to `readModInfoAux` has not been read for that ordering — settled by the same probe; -> X21 [#1664/C/open].
- Which `mod.info` supplies a mod's id when a mod ships more than one — the one `common/`-only corpus mod that has booted ships exactly one and cannot discriminate, so no id-read order may be stated on its strength — settled by a purpose-built folder whose only `mod.info` is `common/mod.info`; -> X21 [#1375/C/C-only/open].
- Whether `loadModAfter=` and `loadModBefore=` reach a dedicated server at all — the jar and the vanilla Lua tree say they do not, and nothing has booted a pair of mods that disagree about order — settled by booting such a pair and reading the loader's `loading` lines [#0882/C/C-only/open].
- What a duplicate id across two mod roots does in practice — the earlier-folder tie-break is a code reading only, and the id-to-dir map's put-if-absent and the mod map's replacement can in principle disagree about which folder a given id ends up pointing at — settled by installing one id in two roots and reading which folder the loader walks [#0883/C/C-only/open].
- The `getText` route's reach into the item-name table is unverified: every reply in the phase missed, so the run carries no in-run positive control and the route's soundness rests on an earlier session's client-side `IGUI_` hit; re-measure by re-running the key phase with an in-run positive control [#0845/M/n=2/unverified].
- That a mod's translation JSON at a vanilla relative path costs vanilla nothing is unverified: both of the measured mod's translation JSONs exist only in its `common/` tree, so no collision is being resolved; X5 (run `x182-20261006-152945`) read one vanilla key of each of two files and no other, so what a mod's same-path file costs the rest of vanilla's keys is still unread; re-measure with a mod that ships a JSON at a vanilla relative path and reads other vanilla keys of the same files [#1340/M/n=1/unverified].
- That a mod present only in the Steam workshop folder is not found under a no-Steam launch — the server booting with zero errors, the client showing the required-mod warning at 34.8 seconds with the mod inactive, and the same mod active on both sides once copied into both cachedirs — is unverified: the spike that measured it committed no artifact folder; re-measure by re-running its two variants under a committed artifact [#1864/M/uncommitted/unverified].
- Decision the rows force: whether this mod ships one version dir per supported build or one version dir beside `common/`, given that the version folder's file wins a same-relative-path collision and `common/` supplies the rest [#1318/M/n=1, #0825/C/C-only].
- Decision the rows force: whether this mod declares `versionMin` at all, given that a failed gate and an absent folder print the same line and a server operator reads that line [#0812/C/C-only, #0872/C/C-only].
- Decision the rows force: whether this mod ships any script file at all on a server it does not control, given that the checksum gate is a content hash over every loaded script file and a one-byte mismatch disconnected a `user`-role client [#1182/C/C-only, #1282/M/n=1].

## Worked examples

| shape | file:lines | what it shows |
|---|---|---|
| two `mod.info` files in one folder, the `common/` arm | `testing/experiments/tkx-loader-probe/common/mod.info:1-5` | the id the live chain does not take, `TKX_LoaderCommon`, beside the four other keys the probe declares |
| two `mod.info` files in one folder, the version arm | `testing/experiments/tkx-loader-probe/42.20/mod.info:1-5` | the id the chain does take: the version dir's file, parsed, and the only one `Mods=` can name |
| a colliding relative path, the `common/` copy | `testing/experiments/tkx-loader-probe/common/media/lua/shared/TKX_Loader_Which.lua:1-4` | one half of the merge discriminator — the same relative path in both trees, writing `"common"` |
| a colliding relative path, the version copy | `testing/experiments/tkx-loader-probe/42.20/media/lua/shared/TKX_Loader_Which.lua:1-4` | the other half, writing `"version"`, which is the value the boot read back on both sides |
| a version dir holding only a `mod.info` | `testing/experiments/TKX_CommonOnly/42.20/mod.info:1-5` | the empty-version-dir arm: five keys and no `media/` beside them |
| a `common/`-only payload | `testing/experiments/TKX_CommonOnly/common/media/lua/shared/TKX_CommonOnly.lua:1-4` | the whole payload of that mod, which still loads and resolves on both sides |
| a mod named but never placed | `testing/profiles/missing-mod.toml:6-11` | the missing-mod arm as a profile: a real mod beside an id nothing declares, copied by nothing |
| the folder-drift boots | `testing/experiments/x123_folder.py:246-254` | the two boots that separate the folder name from the id: one folder renamed away from both ids, `Mods=` naming the version dir's id and then `common/`'s |
| the empty-version-dir readings | `testing/experiments/x122_loader.py:190-195` | the two globals that arm reads back, and the `common/` file each is defined in |

## See also

- [`loader-and-scripts.md`](loader-and-scripts.md) — the file map, the Lua execution list and the block-level script merge this page hands off.
- [`overview.md`](overview.md) — the two Lua states, the join and the process model a mod loads inside.
- [`mp-model.md`](mp-model.md) — what crosses the wire, for the mod state a one-sided mod cannot share.
- [`harness.md`](harness.md) — the profile schema and the install that puts a mod folder where the loader will find it.
- [`lessons.md`](lessons.md) — corpus drift, and why every count over the installed tree carries a date.
- [`../facts/other-mods/autocook.md`](../facts/other-mods/autocook.md) — the `common/`-only corpus mod that supplies the measured merge rule.
- [`../facts/other-mods/simplestatus.md`](../facts/other-mods/simplestatus.md) — the client-only mod whose translation tree the server still loads.
- [`../areas/packaging.md`](../areas/packaging.md) — what this mod does about its own layout and the checksum gate.
- [`../reference/experiments.md`](../reference/experiments.md) — `X21`, the experiment the open rows name, and `X5`, the translation experiment the translations section reads.
- [`../reference/wall-map.md`](../reference/wall-map.md) — the verdict rows this page cites by id.
