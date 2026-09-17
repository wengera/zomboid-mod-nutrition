# Modding platform reference

How B42 mods are built, what the platform allows, and where the walls are.
Sources: PZwiki pages (mirrored), TIS guides, and **evidence from the 159
installed workshop mods** — real shipped code beats documentation.

## The P2 documents

**Four** of them are **written**: the three platform docs (slice 12, 2026-09-11), every mechanism
in which is **M** from one of the seven sessions `x121`–`x127` or **C** from the 42.20.4 jar,
and the **wall map** (slice 13, 2026-09-17), which classifies every capability against those three,
waves 1–3 and a fresh jar read. They are the authorities for what they own. Cite them by section;
nothing below restates them.

| Doc | Covers |
|---|---|
| [**anatomy.md**](anatomy.md) — written | `mod.info` keys and who acts on each, **where a `mod.info` may live and which one supplies the id** (one id per folder, the version dir's file; resolution by id, never by folder name), version dirs and `common/`, `Mods=` and the folder name, translations, `require` and Lua load order, what `mod_lint` checks — plus the `Mods=` chain re-derived from the jar and § Inputs for the wall map (slice 13) |
| [**lua-api.md**](lua-api.md) — written | the curated Lua surface a nutrition mod needs: events and their firing context (`OnEat*`, `EveryOneMinute`, `OnCooked`, `OnClientCommand`), Java members by owner, script-side hooks, the command-bus model, **what Kahlua cannot do** (including the corrected nil-call rule), and what 42.20.4 removed |
| [**item-overrides.md**](item-overrides.md) — written | the five routes into a vanilla item's nutrition — redefinition, the **partial block** (which merges per key), a new item in the mod's own module, Lua hooks on the instance, item modData — what a second `item` block actually does, and **load order between two mods**: the item-pass mechanism |
| [**wall-map.md**](wall-map.md) — written (slice 13; planned as `moddability-walls.md`) | **Jar-locked vs moddable map**, one row per capability over ten design areas: **64 rows** — 25 **CANNOT** · 22 **CAN** · 14 **CAN WITH A WORKAROUND** · 3 **UNKNOWN** — each with the mechanism that decides it (a named jar site on every `CANNOT`), the workaround, the residual risk and a graded citation; plus **26 named experiments** with an owner and a cost each, § What the library cannot yet measure, § Discrepancies and § Open questions. The walls this row used to sketch are now rows **A1** (`Nutrition` is a closed value object) and **D1** / **D2+D3** (moodles); the doors are **J1** (a second `item` block merges per key), **A5** (an unrecognised item-block key becomes default modData) and **B2** (a server-side wrapper of `ISEatFoodAction.complete` runs before `Eat`) |
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
- MP item sync is **two different packets, and this bullet stated them as one** (corrected
  2026-09-17, slice 13). *Previously stated:* "MP item sync (`SyncItemFieldsPacket` /
  `ItemStatsPacket`) carries condition / headCondition / sharpness / modData / favorite and 43
  fields in all, but **not** `conditionMax`". The **43 fields** and the missing `conditionMax`
  are `ItemStatsPacket`'s — seven members, server → client, and `sendItemStats` on a
  client is a silent no-op; the **modData** clause is `SyncItemFieldsPacket`'s — 15 members,
  the `syncItemFields()` route, which **wipes and replaces** the receiver's item modData. The
  consequence survives the split: any per-instance stat outside the synced set silently reverts
  on the server round-trip. The two wires side by side, with their member lists:
  [`wall-map.md`](wall-map.md) § Discrepancies (rows E1+E2, E8, A6). Owned by
  [`patterns.md`](patterns.md) § Measured MP sync facts (the field list, the halved
  `thirstChange`, the absent aging fields) — measured since this note was written, and no longer
  a bare packet read.
- `getFileWriter` extension-limited (ini/cfg/txt/log/json); `getModFileWriter` not (42.20.x) —
  data export from in-game tooling remains possible. **Not re-verified this phase**; the harness
  uses `getFileWriter` for every bus reply ([`../testing/README.md`](../testing/README.md)).
