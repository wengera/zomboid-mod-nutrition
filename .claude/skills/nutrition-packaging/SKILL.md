---
name: nutrition-packaging
description: Shipping the nutrition mod — its folder, `mod.info` (`id=`, `require=`, `loadModBefore=`, `loadModAfter=`, `versionMin`, `versionMax`), `common/` beside a version dir named for the verified build, script and Lua relative-path collisions, the join checksum and Workshop updates, `Mods=`, the resident stack (`CleanUI`, `MoodleFramework`, `AutoCook`, `simpleStatus`), a mod that does not load, and the layout lint `tools/mod_lint.py`.
---
## Read first
- docs/areas/packaging.md
- docs/platform/mod-anatomy.md
- docs/platform/loader-and-scripts.md

## Rules quoted
- Declare one id per mod folder and put it in the build's version dir: the loader parses that one `mod.info` and never the folder name, so a second `mod.info` with another id is unaddressable [#0802/C/C-only, #0881/M].
- Ship `common/` beside the version dir and keep only the build-specific files in the version dir: the version dir's file wins a same-relative-path collision and `common/` supplies everything the version dir does not ship [#1318/M/n=1].
- Name each version dir for the build its files were verified on and no later: the resolver takes the highest name at or below the running build, so a dir named for a later build is never read while one named for the verified build keeps running, unverified, on every later build until a newer-named dir ships [#0825/C/C-only, #2075/C/inference].
- Give every script file a mod-unique relative path: the file map holds one absolute path per relative path and the script walk drops a repeat, so the loser's blocks are never parsed — a code reading, since no session has shipped the same relative script path from two mods [#1046, #1047/C/C-only].
- Use `require=` when one mod must load before another: it is the only load-order declaration the loader acts on, and `loadModBefore=` and `loadModAfter=` only arrange rows in the client's mod selector [#0811/C/C-only, #0814/C/C-only].
- Ship byte-identical script files on both sides of a multiplayer session: the gate hashes file content with every CR byte dropped, so a mismatch is a disconnect rather than a silent degrade [#1182/C/C-only, #1231/C/C-only].
- Keep every Lua file off the vanilla relative paths a resident mod already replaces: the file map keeps one file per relative path, so this mod and that neighbour would each lose the whole file to the other on load order [#1173/C/C-only, #1457/C/snapshot, #2074/C/inference].
- Read a mod's `mod.info` rather than the loader's error text when a mod does not load: a failed `versionMin` or `versionMax` gate, a missing `require=` and a folder that is not there all print the same not-found line [#0872/C/C-only, #0812/C/C-only].
- Name in the mod's description every installed mod whose numbers its model makes inert or contradicts: a resident already writes the player's calories on the server every tick, residents wrap the eat action on both sides, and a viewer drawing a re-based macro against hard-coded bands goes wrong silently, so the description is where an operator learns which of them this mod overrides [#1588, #2566/C/snapshot, #1522, T25.2].
- Print one self-report line at boot naming the mod's version and the optional frameworks it detected: an absent, a version-gated and an unsatisfied mod all print one not-found line and the server drops the id and boots clean, so no line the loader prints names the mod's own version or what it found beside it [#0871/C/C-only, #1793, #0872/C/C-only, #2547/C/inference, T25.3].
- Detect an optional framework with a type test on its global at `OnGameBoot` or later, never with `require`: the framework defines its global at file-load time, so the type test reads its presence without going through the loader, while a `require` of its file goes through the loader and, with the framework absent, logs a warning and returns nothing on every server that runs without it [#2547/C/inference, T25.4].

## Also
- docs/facts/other-mods/catalog.md#corpus-facts — the resident mods, what each touches, and the Workshop neighbours that are not installed.
- docs/reference/tools.md#mod-lint — the layout lint that checks this mod's folder before any boot.
- docs/areas/item-pass.md — the script files this area packages (skill `nutrition-item-pass`).
