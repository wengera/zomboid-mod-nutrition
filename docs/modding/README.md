# Modding platform reference

How B42 mods are built, what the platform allows, and where the walls are.
Sources: PZwiki pages (mirrored), TIS guides, and **evidence from the 159
installed workshop mods** — real shipped code beats documentation.

## Planned documents (P2)

| Doc | Covers |
|---|---|
| mod-anatomy.md | mod.info fields, version-folder resolution (`42/`, `42.x/`, `common/`, flat legacy — we've mapped this empirically across KATTAJ1/FS/KI5/ChuckleberryFinn mods), media/ layout, workshop packaging |
| lua-events.md | Event inventory relevant to nutrition (OnPlayerUpdate, EveryOneMinute, OnEat*, OnCreatePlayer, OnClientCommand...) with firing context (client/server/both) |
| moddability-walls.md | **Jar-locked vs moddable map.** Known walls: java classes (`Nutrition`, `setCondition` clamps) can't be extended — only wrapped/paralleled. Known doors: lua action wrapping (BeyondTen's `adjustMaxTime`), `Actions.addOrDropItem` hooks (ItemQuality), modData, item script overrides |
| parallel-stats.md | Architecture for mod-side nutrient stats: modData storage, save/load, sync commands, reapply-on-event patterns, UI (moodles — evaluate Moodle Framework vs own) |
| item-overrides.md | Overriding vanilla Food item values at scale (module Base re-declaration, load order, MP script checksum implications) — the item-pass mechanism |
| mp-networking.md | sendClientCommand/OnClientCommand, what modData syncs when, **TIS B42 networking-migration guide digested**, loadstring removal fallout |
| sandbox-options.md | Mod config surface (sandbox-options.txt — seen in KATTAJ1/KBW) |
| dev-loop.md | Debug mode, -debug, reloading, Umbrella/VSCode setup for collaborators, MP test loop |

## Hard-won platform facts (from prior sessions — cite before reuse)

- Version-folder resolution picks the highest `42.x` ≤ game build; `common/`
  shared; flat layout = legacy B41 (still loads for some mods). **How the two
  combine is measured** (slice 11, 2026-09-11, run `td3-20260911-001948`): the
  version folder's file **wins** a same-relative-path collision, `common/`
  supplies everything the version folder does not ship, and both end up in one
  Lua state — translations excepted, because `Translator` merges rather than
  resolving through `activeFileMap`. Outcome **M** (n = 1), mechanism **C**
  (four jar sites), bounded to a version dir that actually ships colliding
  files:
  [`../mods-survey/teardowns/autocook.md`](../mods-survey/teardowns/autocook.md)
  § Architecture.
- `ResourceLocation`-style ids are lowercased (case-insensitive registries).
- Item scripts: generated `.txt` DSL; recipes support mappers, Inherit* flags,
  OnCreate java handlers (`RecipeCodeOnCreate`) and lua-visible hooks.
- MP item sync (`SyncItemFieldsPacket`) carries condition/headCondition/
  sharpness/modData/favorite/etc. but **NOT conditionMax** → any per-instance
  stat outside the synced set silently reverts on the server round-trip
  (ItemQuality teardown is the case study).
- `getFileWriter` extension-limited (ini/cfg/txt/log/json); `getModFileWriter`
  not (42.20.x) — data export from in-game tooling remains possible.
