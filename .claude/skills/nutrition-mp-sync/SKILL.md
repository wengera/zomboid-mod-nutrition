---
name: nutrition-mp-sync
description: Syncing a nutrition mod's state between a dedicated server and its clients — who owns each stat, the command bus from `sendClientCommand` to `OnClientCommand` to `sendServerCommand`, player, item and global modData with `transmitModData` and its wipe-and-replace, the player-stats packet, `ItemStatsPacket`, `SyncItemFieldsPacket` and `syncItemFields()`, `isServer()` guards on `media/lua/server/` files, client prediction and mirrors, the band traits the player-stats packet does not carry, and addressing an item by id in a bus round trip.
---
## Read first
- docs/areas/mp-sync.md
- docs/platform/mp-model.md
- docs/facts/wire-packets.md

## Rules quoted
- Run anything that changes what eating delivers where `Eat` runs, on the server, and carry its state by server mutation over the command bus, a parallel player-modData store transmitted on change, or client-only semantics: a multiplayer client never reaches `Eat`, so nothing it computes lands in the vanilla store the eat writes [#0128/C/inference, #0109].
- Write every player stat on the server: a client-side write to hunger, thirst, endurance, fatigue, calories, the macros or weight is erased by the next player-stats packet, so every one of them has exactly one owner [#0568/M/n=2].
- Route every mod mutation through the command bus, from `sendClientCommand` to the server's `OnClientCommand` to validation to the mutation and back on `sendServerCommand`: the server validates and the client may at most predict [#1065/C/snapshot].
- Keep server-authoritative per-player state out of player modData, or guarantee the client's copy is complete before anything on that client transmits: one client transmit makes the server's copy of that player's table exactly the client's [#1042/M/n=2, #1496/M/n=1].
- Batch every key one side owns into a single transmit: the call moves the whole table rather than the changed key, so a second transmit cannot repair what the first one dropped [#1638/M/n=1, #1091].
- Never push an item stat field from a client: the item-stats send is the server's own call with no client-side counterpart, so on a client it does nothing at all — the one client-to-server item route is the item-fields sync, a different packet carrying modData and condition [#0330/C/C-only, #1240/C/C-only].
- Give the mod's command-bus module a name no other mod on the server uses: the bus is one namespace shared with every other mod's command sites on that server [#1153/C/C-only, #2055/C/inference].
- Guard every `media/lua/server/` file with a runtime `isServer()` test rather than trusting the folder: a mod's `server/` files execute in the multiplayer client's Lua state too, so "only my server file writes this" is false until the guard is there, and the side test is itself nil-checked because the global may be absent [#0855/M/n=1, #1075/M/n=1].
- Push the trait block with `sendSyncPlayerFields(player, 2)` after any server-side trait write, and expect only the affected player's own client to receive it: a trait write fires no event and sends no packet, the once-a-second experience push also refreshes that client's trait list so the mod's own push buys freshness within that second rather than being the only route, and every player-addressed server send reaches that player's connection alone, all read from the code and not exercised on a live server [#2693/C/inference] [#2601/C/C-only] [#2595/C/C-only] [#2608/C/C-only] [#2603/C/C-only].
- Re-read a client's copy of a server-written value only after the push that carries it has landed: the engine refreshes the stats, the experience object, and the injuries and damage on timed pushes of their own, the experience object on the stats snapshot's cadence and injuries and damage on a slower one, while `syncPlayerStats`, `syncBodyPart` and `sendSyncPlayerFields` push now to that player's own client, a value no timed push carries arrives only on such a call, and a call is no proof of delivery, so a read taken before the carrying push sees the previous value [#2694/C/inference] [#2608/C/C-only] [#2609/C/C-only] [#2607/C/C-only] [#2602/C/C-only] [#2603/C/C-only].
- Send a mod-owned value to the client over the mod's own command bus, never through a framework that has no transport: a client-side library such as `MoodleFramework` sends, receives and transmits nothing and keeps its values in a per-client table, so a server-authoritative value reaches it only when the mod's own `sendServerCommand` delivers it to a client handler that hands it over [#2695/C/inference] [#2540/C/inference] [#2537/C/C-only] [#2538/C/C-only] [#1153/C/C-only].

## Also
- docs/platform/lessons.md#anti-patterns — the sync rules and the authority filters that come with them.
- docs/platform/harness.md#experiment-contract — the client-first paired read, the only way a silent sync failure is seen (skill `pz-mod-testing`).
- docs/platform/server-lifecycle.md#global-moddata — the world-scoped store and its own rules.
- docs/areas/new-nutrients.md — where the nutrient store this page routes is chosen (skill `nutrition-new-nutrients`).
