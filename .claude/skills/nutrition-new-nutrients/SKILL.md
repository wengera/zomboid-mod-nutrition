---
name: nutrition-new-nutrients
description: Adding a mod nutrient the vanilla macros lack (fibre, vitamins, a parallel diet stat) and choosing its store — character, item or global modData, `getModData`, `OnInitGlobalModData`, an unrecognised key in a `module Base` `item` block that lands in default modData — which route that store forces and what it survives, the vanilla macro clamps and drain it must stay out of, the `Nutrition` sandbox option, the consumer the mod writes for it, and its cadence on `EveryOneMinute`, `EveryTenMinutes`, `OnPlayerUpdate` or `OnTick`.
---
## Read first
- docs/areas/new-nutrients.md
- docs/platform/mp-model.md
- docs/facts/wire-packets.md

## Rules quoted
- Keep every durable mod value in character, item or global modData: live Java fields are unsynced cache, and only modData saves and syncs on engine paths [#1064/C/snapshot].
- Keep a mod nutrient out of the vanilla macro stores: every setter clamps its store silently and the hard-coded drain moves it every tick, so a value parked there is cut and moved by vanilla rather than held [#0023/M/n=2, #1193/C/C-only, #2056/C/inference].
- Reach a new nutrient on an item through an unrecognised key inside the vanilla `item` block, and on a drink's fluid through a Lua table keyed by the fluid's type string: the parser's default arm rawsets the key into the item's default modData and every instance receives a deep copy, while a `fluid` block has no default arm and stores no unrecognised key [#1089, #1187/C/C-only, #2676/C/C-only, #2682/C/C-only, #2684/C/C-only].
- Own every key on an item whose modData carries a mod nutrient: the item-field sync wipes the receiver's whole table before it copies the sender's keys, so a key the syncing side lacks is gone — a wipe measured in the client-to-server direction only [#1126/M/one-side, #2057/C/inference].
- Keep server-authoritative per-player state out of player modData, or guarantee the client's copy is complete before anything on that client transmits: one client transmit makes the server's copy of that player's table exactly the client's [#1042/M/n=2, #1496/M/n=1].
- Batch every key one side owns into a single transmit: the call moves the whole table rather than the changed key, so a second transmit cannot repair what the first one dropped [#1638/M/n=1, #1091].
- Give every mod nutrient a consumer the mod writes itself: the protein store has one vanilla consumer, the Strength experience grant, which raises Strength experience while the store is strictly between 50 and 300 and lowers it below −300, so a parallel protein store that leaves the vanilla store on its drain leaves that bonus and that penalty on vanilla's number, while the carbohydrate store as an energy pool and any notion of diet quality stay dead space [#2112/C/C-only, #1136/C/C-only, #1193/C/C-only, #2696/C/inference].
- Set the `Nutrition` sandbox option in the server's sandbox config: the nutrition update reads the option live every tick, a runtime flip from Lua is untried, and the Lua mirror of the option goes stale [#1127/C/C-only, #2058/C/inference].
- Put slow simulation such as nutrient decay on `EveryOneMinute` or `EveryTenMinutes`, use `OnPlayerUpdate` only for per-frame needs behind a cheap early-out, and avoid `OnTick`: 38 mods already share `OnPlayerUpdate` and `OnTick` is the expensive tier [#1071/C/snapshot].

## Also
- docs/facts/nutrition-core.md#clamps — the vanilla stores, their clamps and the weight model a nutrient's effect can reach.
- docs/areas/mp-sync.md — the route the nutrient's state travels (skill `nutrition-mp-sync`).
- docs/areas/ui-and-moodles.md#moodle-route — a moodle or a panel as the nutrient's display, and the registry route to avoid (skill `nutrition-ui-and-moodles`).
