# Teardown: ItemQuality (Girth's Quest System module)

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
