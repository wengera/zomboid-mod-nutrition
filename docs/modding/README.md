# Modding platform reference

How B42 mods are built, what the platform allows, and where the walls are.
Sources: PZwiki pages (mirrored), TIS guides, and **evidence from the 159
installed workshop mods** — real shipped code beats documentation.

## The P2 documents

Three of them are **written** (slice 12, 2026-09-11) and are the authorities for what they own —
every mechanism in them is **M** from one of the seven sessions `x121`–`x127` or **C** from the
42.20.4 jar. Cite them by section; nothing below restates them.

| Doc | Covers |
|---|---|
| [**anatomy.md**](anatomy.md) — written | `mod.info` keys and who acts on each, **where a `mod.info` may live and which one supplies the id** (one id per folder, the version dir's file; resolution by id, never by folder name), version dirs and `common/`, `Mods=` and the folder name, translations, `require` and Lua load order, what `mod_lint` checks — plus the `Mods=` chain re-derived from the jar and § Inputs for the wall map (slice 13) |
| [**lua-api.md**](lua-api.md) — written | the curated Lua surface a nutrition mod needs: events and their firing context (`OnEat*`, `EveryOneMinute`, `OnCooked`, `OnClientCommand`), Java members by owner, script-side hooks, the command-bus model, **what Kahlua cannot do** (including the corrected nil-call rule), and what 42.20.4 removed |
| [**item-overrides.md**](item-overrides.md) — written | the five routes into a vanilla item's nutrition — redefinition, the **partial block** (which merges per key), a new item in the mod's own module, Lua hooks on the instance, item modData — what a second `item` block actually does, and **load order between two mods**: the item-pass mechanism |
| moddability-walls.md → `wall-map.md` (slice 13) | **Jar-locked vs moddable map.** Known walls: java classes (`Nutrition`, `setCondition` clamps) can't be extended — only wrapped/paralleled. Known doors: lua action wrapping (BeyondTen's `adjustMaxTime`), `Actions.addOrDropItem` hooks (ItemQuality), modData, item script overrides |
| parallel-stats.md | Architecture for mod-side nutrient stats: modData storage, save/load, sync commands, reapply-on-event patterns, UI (moodles — evaluate Moodle Framework vs own) |
| mp-networking.md | sendClientCommand/OnClientCommand, what modData syncs when, **TIS B42 networking-migration guide digested**, loadstring removal fallout |
| sandbox-options.md | Mod config surface (sandbox-options.txt — seen in KATTAJ1/KBW) |
| dev-loop.md | Debug mode, -debug, reloading, Umbrella/VSCode setup for collaborators, MP test loop |

## Hard-won platform facts (from prior sessions — now mostly owned elsewhere)

Each bullet names the document that owns the graded statement. Cite **that** document, not this
list: these are pointers, kept so nothing learned before the P2 docs existed goes missing.

- Version-folder resolution picks the highest `42.x` ≤ game build; `common/` is shared; a flat
  layout is legacy B41 (still loads for some mods). **How the two combine is measured, now at
  n = 2** (`td3-20260911-001948`, a workshop mod, and `x122-20260911-032326`, a mod we wrote): the
  version folder's file **wins** a same-relative-path collision, `common/` supplies everything the
  version folder does not ship, and both end up in one Lua state — translations excepted, because
  `Translator` merges rather than resolving through `activeFileMap`. Outcome **M**, mechanism
  **C** (four jar sites). The bound has widened with the second subject: a version dir that ships
  colliding files **or none at all** (a version dir holding only a `mod.info` costs the mod
  nothing). Owned by [`patterns.md`](patterns.md) KEEP 10 and [`anatomy.md`](anatomy.md) § 3;
  the first subject's reading is
  [`../mods-survey/teardowns/autocook.md`](../mods-survey/teardowns/autocook.md) § Architecture.
- A mod folder's **name is irrelevant** and only the version dir's `mod.info` id is addressable —
  **M**, `x123-20260911-034426` / `x123b-20260911-034500`. Owned by [`anatomy.md`](anatomy.md)
  § 2 and § 4.
- `ResourceLocation`-style ids are lowercased (case-insensitive registries). **Not re-verified
  this phase**; the measured neighbour is the loader's `overrides` tail, which is a lower-cased
  relative path ([`anatomy.md`](anatomy.md) § 3).
- Item scripts: generated `.txt` DSL; recipes support mappers, Inherit* flags, OnCreate java
  handlers (`RecipeCodeOnCreate`) and lua-visible hooks. The item-side mechanism — a second
  `item` block **merges per key**, so restate only what you change — is
  [`item-overrides.md`](item-overrides.md) § What a second `item` block actually does; the recipe
  dataset is [`../vanilla/recipes-dataset-notes.md`](../vanilla/recipes-dataset-notes.md).
- MP item sync (`SyncItemFieldsPacket` / `ItemStatsPacket`) carries condition / headCondition /
  sharpness / modData / favorite and 43 fields in all, but **not** `conditionMax` → any
  per-instance stat outside the synced set silently reverts on the server round-trip. Owned by
  [`patterns.md`](patterns.md) § Measured MP sync facts (the field list, the halved
  `thirstChange`, the absent aging fields) — measured since this note was written, and no longer
  a bare packet read.
- `getFileWriter` extension-limited (ini/cfg/txt/log/json); `getModFileWriter` not (42.20.x) —
  data export from in-game tooling remains possible. **Not re-verified this phase**; the harness
  uses `getFileWriter` for every bus reply ([`../testing/README.md`](../testing/README.md)).
