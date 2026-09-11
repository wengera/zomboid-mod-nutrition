# Teardown: ItemQuality (Girth's Quest System module)

**Verified against: 42.20.4 (`b0bbce05d5`)** — read 2026-09-04 alongside a live bug
investigation on a 42.20.4 dedicated server; stamp and sources backfilled 2026-09-10 (slice 09
pass 1). This teardown was **read, not measured in this repo**: every claim below is **C**
(code reading, plus the pz-b42 investigation its § What it does names), and no run in
`testing/artifacts/` evidences any of it.

- Workshop ID: 3624538051 (bundle: QuestSystem, Economy, BaseQuests,
  **ItemQuality**) — one workshop item, four mod IDs.
- Build examined: 2026-09-04 files (mod updates ~daily; 465+ change notes).
- Origin of this teardown: live bug investigation on 42.20.4 dedicated MP
  (full detail: pz-b42 `findings/crafted-weapon-quality.md` + bug report).

## What it does

Rolls a quality tier on eligible crafted items (HandWeapon/Clothing), applies
point-bought stat buffs (damage %, reach, arc, sharpness %, +ConditionMax
"Durability"), shows tier in tooltips, preserves tier through
dismantle→reforge via "salvage markers".

## Architecture

- Entry: monkey-patches `ISHandcraftAction:performRecipe` (server/ lua) and
  hooks `Actions.addOrDropItem` during the wrapped call to intercept every
  output item at creation.
- Tier roll from **average of the recipe's required-skill levels**; carry-over
  chance from consumed ingredients' tiers; salvage markers stored on
  non-eligible intermediates (modData) to survive multi-step chains.
- Data: tier/mods/craftedBy/KnownCondition in item modData
  (`ItemQualityData`); numeric buffs applied to live item fields.
- Reapply layer (`QualityModifiers.Reapply`) restores non-persistent fields
  (e.g. ConditionMax) from modData on OnEquip/OnCreatePlayer/OnPlayerUpdate.

## MP handling — the case study

- **Root problem:** buffs write java item fields the engine does not
  serialize or sync. `SyncItemFieldsPacket` carries condition, headCondition,
  sharpness, modData... **not conditionMax** — and `setCondition` clamps to
  the receiver's max. Server copy (script max) clamps 18→13 and echoes.
- Mod's mitigation: mark fields `persistent = false` + client-side reapply on
  events. Works for fields only the client reads (damage/reach — combat
  resolves client-side); **fails for server-echoed fields** (condition).
- Found bugs: (1) durability on headless weapons originally reverted (later
  fixed via attribute for headed weapons — HeadConditionMax IS a persisted
  attribute); (2) **salvage-restore path passes `preserveCondition=true` to
  `Modifiers.Apply`, skipping the refill** → reforged weapons permanently at
  script-max/buffed-max (13/18), and `SetKnownCondition(current)` runs
  unconditionally, poisoning the one-shot recovery guard
  (`known > condition` never true). Reported upstream with patch.

## Techniques worth stealing

- addOrDropItem interception → clean per-output-item hook without touching
  java (`CraftQualityHandler.lua:150-203`).
- Salvage-marker pattern: stat continuity across multi-recipe chains via
  modData on intermediates.
- Config-table-driven stat system (`ItemQualityConfig.Categories`): fields,
  per-point values, eligibility predicates — declarative and extensible.

## Pitfalls → rules for our mod

1. **Never store authoritative mod state in unsynced java fields.** modData
   is synced and saved; live fields are cache derived from it.
2. Reapply must be idempotent and continuous, not one-shot; never let a
   tracker overwrite the source-of-truth with a clamped observation.
3. On dedicated MP, assume the server echoes item numerics — test every stat
   with a relog + a second client before shipping.

## Verdict

Not a dependency. Its config-driven stat table and creation-hook pattern are
directly reusable shapes for nutrient metadata on food items; its sync
failures define our MP test checklist.

## Sources

All **C** — a read of the installed mod plus the pz-b42 investigation named below; no run in
this repo measures any of it.

- The mod folder, read-only: workshop item `3624538051`, folder
  `3624538051/mods/ItemQuality`; `42/` is its only version folder. The three files this
  teardown names are `42/media/lua/server/EventHandlers/CraftQualityHandler.lua` (the
  `performRecipe` wrap and the `addOrDropItem` interception),
  `42/media/lua/shared/Utilities/ItemQualityConfig.lua` (the stat-category table) and
  `42/media/lua/shared/Utilities/QualityModifiers.lua` (`Apply` / `Reapply`), with the tier data
  in `.../ItemQualityData.lua` and the reapply hooks in
  `42/media/lua/shared/EventHandlers/Quality{Weapon,Clothing}Reapply.lua`.
- The live bug investigation this teardown grew out of, in the pz-b42 workspace:
  `findings/crafted-weapon-quality.md`, with the upstream report beside it
  (`findings/itemquality-reforge-bug-report.md`). That workspace is a **separate repo**, so
  those files are not checkable from a clone of this one — which is exactly why the MP case
  study stays **C** here.
- [`data/mod-inventory.json`](../../../data/mod-inventory.json) — the `ItemQuality` row
  (230 mod folders swept 2026-09-10 17:47; 82 963 B, 56 KB of Lua, `require []`, `media_at
  ["42/media"]`): `signals` `mod_data 13`, `monkey_patch 5`, `send_client_cmd 1`,
  `on_client_cmd 1`, `send_server_cmd 1`, `events_add 10`, `pcall 1`. Note the header bullet's
  "four mod IDs" is the bundle as read in September: the sweep finds **5** mod folders under
  item `3624538051` (`QuestSystem`, `Economy`, `BaseQuests`, `ItemQuality`,
  `QualityEnhancements`), which is the count
  [`../nutrition-mods.md`](../nutrition-mods.md) § B42 status uses.
- Distilled into [`../../modding/patterns.md`](../../modding/patterns.md) — KEEP 1 (modData as
  the only durable state), KEEP 6 (declarative config tables), FILTER 1 (unsynced-field
  authority) and FILTER 2 (one-shot repair logic) are this mod's rows. The same failure mode,
  measured end-to-end on a different mod, is in
  [`longtermpreservation4220.md`](longtermpreservation4220.md) § MP handling.
