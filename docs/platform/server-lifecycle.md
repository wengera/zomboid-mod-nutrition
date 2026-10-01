# Server lifecycle
Verified against 42.20.4 (b0bbce05d5) · 2026-10-01 · scope: what a dedicated server does and fires when a player joins, is created, dies and leaves, how a player is addressed on the server, where per-player and world state is stored, and the order of the server's time events in a frame; the packets that carry state are `platform/mp-model.md`'s, their fields `facts/wire-packets.md`'s, and the stat updaters' place in the frame `facts/character-stats.md`'s.

## Rules

- Key a per-player store on `getUsername()`, never on `getOnlineID()`: the online id is a recycled slot number, while the server's own player store is keyed on the username, with world and player index [#2410/C/inference] [#2392/C/C-only] [#2393/C/C-only].
- Treat `OnNewGame` on the server as the hook for every new character, including the one a client creates when its stored character is dead, and seed a player's row there: it fires from the character-creation packet with the new `IsoPlayer`, before the character is handed to the store, and a client whose stored character is dead or absent sends that packet when its world loads [#2411/C/inference] [#2387/C/C-only] [#2404/C/C-only] [#2420/C/C-only].
- Detect a join and a departure with a client-sent command or by diffing the usernames of `getOnlinePlayers()` on a sweep: the server fires no Lua event when a character joins or disconnects [#2412/C/inference] [#2386/C/C-only] [#2403/C/C-only] [#2391/C/C-only].
- Never read a player's death on the server from `OnPlayerDeath`, and treat `OnCharacterDeath`, checked for an `IsoPlayer`, as the only death event the server can fire: `OnPlayerDeath` sits behind a server return and a local-player gate, while `OnCharacterDeath` fires from a death chain the server has entries into, though which causes of death reach that chain on the server is unread [#2413/C/inference] [#2388/C/C-only] [#2389/C/C-only] [#2408/C/C-only] [#2409/C/C-only].
- Never carry an online id across a reconnect: a disconnect sets the slot's id to `-1`, and the next connection takes the first free slot [#2414/C/inference] [#2403/C/C-only] [#2392/C/C-only].
- Look a player up on the server by scanning `getOnlinePlayers()`, never with `getPlayerFromUsername`: the latter delegates to the client instance with no server branch [#2415/C/inference] [#2390/C/C-only] [#2391/C/C-only].
- Keep one player's values out of any global modData table the server transmits: a server-side transmit sends the whole named table to every connection, with no per-player target [#2416/C/inference] [#2398/C/C-only].
- Create a mod's world-scoped table whenever it is missing, with `ModData.getOrCreate`, rather than only when `OnInitGlobalModData`'s Boolean says the world is new: that argument says the world is new and not the table, and the event fires after the load of `global_mod_data.bin`, which restores only the tables the file holds [#2417/C/inference] [#2396/C/C-only] [#2397/C/C-only].
- Install the table `OnReceiveGlobalModData` hands over yourself, and treat a `false` second argument as no table: the event passes a freshly loaded table, or `false` when the packet carries none, and merges nothing into the receiver's copy [#2418/C/inference] [#2399/C/C-only].
- Count connected players with `getOnlinePlayers():size()`, never `getNumActivePlayers()`: the latter returns the local split-screen count [#2419/C/inference] [#2407/C/C-only] [#2391/C/C-only].

## How it works

This page follows one player through a dedicated server: the join, the creation of a new character, death, addressing, the two stores a mod can use, the order of the server's time events, and the disconnect.
The Lua events a dedicated server fires at boot, and the client-only events it never fires, are [lua-platform.md](lua-platform.md#events)'s.
Which side owns each value, and the routes a value can take between the sides, are [mp-model.md](mp-model.md#ownership)'s.
Every row this page owns is read from the bytecode; none of them was exercised on a live server.

<a id="join"></a>
### Join: a returning character arrives with no event

A dedicated server fires no Lua event when an existing character joins: `GameServer.receivePlayerConnect`, which loads the character from the server's store and registers it, contains no `LuaEventManager.triggerEvent` call from its first instruction to its last [#2386/C/C-only].
A `serverLoadNetworkCharacter` that finds no row returns `null`, and `receivePlayerConnect` then kicks the client with `UI_LoadPlayerProfileError` and force-disconnects it [#2395/C/C-only].
So a character passes through `receivePlayerConnect` only once it has a row, and a brand-new character gets its row through [the creation path](#creation), not here [#2395/C/C-only] [#2404/C/C-only].
A client can announce itself over the command bus, whose server-side handler receives the sending player [#0932]; the bus is [mp-model.md](mp-model.md#command-bus)'s.
The server's own sweep of the online list, which [the addressing section](#ids) describes, finds a player whether or not its client ever sends that command.

<a id="creation"></a>
### Creation: `OnNewGame` on the server

`OnNewGame` fires on a dedicated server with the arguments `(IsoPlayer, nil)` when a client creates a character, from `CreatePlayerPacket.processServer` after it has built the `IsoPlayer`, applied its traits and set its username, the square argument being a hard null on this path [#2387/C/C-only].
A new character is handed to the server's store at creation: `CreatePlayerPacket.processServer` calls `serverUpdateNetworkCharacter` and then `ServerPlayerDB.process()` after the `OnNewGame` trigger and before it writes its reply [#2404/C/C-only].
A handler on `OnNewGame` therefore runs on a character that already has its username and traits and has not yet been queued for the store, so whatever the handler writes onto the character is in the first copy the store receives [#2387/C/C-only] [#2404/C/C-only].
On a client, `IsoWorld.init` takes the load path only when `ClientPlayerDB.clientLoadNetworkPlayer()` finds a network player and `isAliveMainNetworkPlayer()` says it is alive, and otherwise calls `GameClient.sendCreatePlayer`, which sends the `CreatePlayer` packet, so a client whose stored character is dead or absent creates a new one through `CreatePlayerPacket` when its world loads [#2420/C/C-only].
The same event is therefore the hook for the character a client creates after a death, while a returning character with a living stored character never passes this way [#2411/C/inference].

<a id="death"></a>
### Death: the event the server sees

`OnPlayerDeath` never fires on a dedicated server: `IsoPlayer.OnDeath` returns at its `GameServer.server` gate before the trigger, and the trigger is further gated on `isLocalPlayer()` [#2388/C/C-only].
`OnCharacterDeath` is triggered with the dying character as its one argument by the first instruction of `IsoGameCharacter.OnDeath`, with no side gate, and `IsoPlayer.OnDeath` calls that body through `super` before its own server return [#2389/C/C-only].
So on the server a player's death fires `OnCharacterDeath` and nothing after it in `IsoPlayer.OnDeath`, provided the server reaches `OnDeath` at all [#2388/C/C-only] [#2389/C/C-only].
`IsoGameCharacter.DoDeath` is the only caller of `OnDeath` in the jar, and a player's `die()` reaches it through `Kill` and `IsoPlayer.onKilled`: `die()` calls `Kill(getAttackedBy())` while the kill is not yet done, `Kill` calls `onKilled`, `IsoPlayer.onKilled` calls `DoDeath` with or without an attacker, and `DoDeath`'s first instruction is the `OnDeath` call that fires `OnCharacterDeath` [#2408/C/C-only].
The dedicated server has entries into that death chain for a player: `IsoGameCharacter.updateInternal` calls `die()` under `GameServer.server` for a dead character no longer on its square's moving-object list, `PlayerOnGroundState.execute` calls `die()` for any dead character with no side gate, `IsoPlayer.onKilled` counts the death in the server's statistics under `GameServer.server` before it calls `DoDeath`, and `DoDeath` writes the user-log death line and the `announceDeath` chat line only under `GameServer.server` [#2409/C/C-only].
The chain, as the bytecode lays it out [#2408/C/C-only]:

```
die()                         kill not yet done -> Kill(getAttackedBy())
  Kill(attacker)              -> Kill(attacker, null, true, null)
    Kill(4 args)              health 0, overall body health 0; kill not yet done -> onKilled
      IsoPlayer.onKilled      server: statistics counters; -> DoDeath(weapon or null, attacker, flag)
        DoDeath               first instruction: OnDeath()
          IsoPlayer.OnDeath   first instruction: super.OnDeath()
            IsoGameCharacter.OnDeath   triggerEvent("OnCharacterDeath", this)
          IsoPlayer.OnDeath   GameServer.server -> return   (OnPlayerDeath below is never reached)
```

The event's argument is whatever character died, not only a player, so a handler that wants players tests the argument [#2389/C/C-only].
`PlayerHealthPacket` runs from server to client: its one sender, `NetworkPlayerAI.syncHealth`, is gated on `GameServer.server` and sends to the player's own fully connected connection, its `@PacketSetting` annotation carries `handlingType 2`, the bit `PacketSetting$HandlingType.getType` sets for a packet type that has a client-side process and no server-side one, and its `parse` writes each body part's health and then recomputes the overall value on the receiving client [#2405/C/C-only].
`PlayerHealthPacket` therefore does not write the server's body health; the client's copy is the one it writes [#2405/C/C-only].
The code establishes server-side entries into the chain, not that every cause of death, starvation included, reaches one of them on the server; [the open section](#open) carries the decision that forces [#2409/C/C-only].

<a id="ids"></a>
### Addressing a player on the server

`getOnlinePlayers()` on a dedicated server returns a freshly allocated `ArrayList` on every call, filled from each connection's four player slots, skipping an empty slot and a player whose online id is `-1` [#2391/C/C-only].
The list is a snapshot: a player who connects or leaves after the call is not in it, so a handler that keeps the list across ticks keeps a stale one [#2391/C/C-only].
Up to four players can share one connection on a split-screen client, so a connection is not a player [#2391/C/C-only].
A Java list is walked from Lua with `size()` and `get(i)`; the Kahlua limits behind that are [lua-platform.md](lua-platform.md#kahlua-limits)'s.
A player's online id on a dedicated server is `slot * 4 + playerIndex`, where the slot is the first free index of `SlotToConnection`, so the id is recycled and is not stable across a reconnect [#2392/C/C-only].
A reconnect after someone else has taken the slot gets a different id, and a reconnect into the same free slot gets the id the departed player had [#2392/C/C-only].
The username is the identifier the server itself keys its store on, as [the player store](#player-store) shows.
`getPlayerFromUsername` is client-only and unguarded: its whole body delegates to `GameClient.instance`, with no `GameServer.server` branch [#2390/C/C-only].
The server-side lookup by name is therefore a scan of `getOnlinePlayers()` comparing `getUsername()` [#2390/C/C-only] [#2391/C/C-only].
`getNumActivePlayers()` returns `IsoPlayer.numPlayers`, the local split-screen count, not the number of connected players [#2407/C/C-only].

<a id="player-store"></a>
### The server's player store

The dedicated server's own player store is the SQLite table `networkPlayers`, read by username, world and player index, or by Steam id in the username's place when the server is a co-op host in Steam mode [#2393/C/C-only].
The query reads back the character's position, its death flag and one serialised blob of the character [#2393/C/C-only].
Character modData is saved in the blob the server stores in `networkPlayers`: `NetworkCharacterData` fills that blob through `IsoObject.save(ByteBuffer)`, which dispatches to `IsoPlayer.save`, whose chain through `IsoGameCharacter.save` reaches `IsoMovingObject.save`, which writes a presence byte and then the object's modData table, the field `getModData` returns, whenever that table is non-empty, and `IsoMovingObject.load` reads it back [#2394/C/C-only].
The blob is filled when the row is queued, so it holds whatever the server's `IsoPlayer`, modData table included, holds at that moment [#2394/C/C-only].
That table is also a channel the client writes: one client transmit makes the server's copy exactly the client's [#1042/M/n=2], and the rule that follows is [mp-model.md](mp-model.md#player-moddata)'s.
When the server rewrites a connected player's row after creation, and whether a client's own upload can overwrite it, lie outside the rows here; [the walls](#walls) name them.
A mod's own table in global modData, keyed on the username, sits outside this blob altogether; the next section reads that store.

<a id="global-moddata"></a>
### Global modData: the world's own store

`OnInitGlobalModData` fires with one argument, the Boolean `WorldDictionary.isIsNewGame()`, after `GlobalModData.init` has run `reset()` and `load()` [#2396/C/C-only].
A handler that reads `false` finds only the tables the file held when the load ran, so a mod added to an existing world finds its own table absent [#2396/C/C-only] [#2397/C/C-only].
Where a mod initialises its world-scoped tables is [lessons.md](lessons.md#rules)'s standing rule.
Global modData lives in one file per save, `global_mod_data.bin` in the current save's folder, and `GlobalModData.save()` returns without writing under `Core.isNoSave()` [#2397/C/C-only].
On a dedicated server one save is one world, so the file is per world and outlives every connection [#2397/C/C-only].
When the server calls `save()`, and so when a write reaches the disk, is open; [the open section](#open) carries it.
`ModData.transmit(name)` on a dedicated server sends the whole named table to every entry of `GameServer.udpEngine.connections`, with no per-player target and no `isFullyConnected` filter [#2398/C/C-only].
A table keyed by username and transmitted from the server is therefore every player's values on every client [#2398/C/C-only].
The per-player push a mod controls is the command bus's server send, which [mp-model.md](mp-model.md#command-bus) owns.
`OnReceiveGlobalModData` fires on the receiving side with `(name, table)`, the table freshly allocated and loaded from the packet, or with `(name, false)` when the packet carries no table, and the parse installs nothing itself [#2399/C/C-only].
A handler that does nothing with the table leaves the receiver's copy exactly as it was [#2399/C/C-only].
`GetModDataPacket.processServer` is exactly `triggerEvent("SendCustomModData")`, a server-side Lua event with no arguments [#2406/C/C-only].
That event names no player, so a handler cannot tell which client's request fired it [#2406/C/C-only].

<a id="tick-order"></a>
### The order of the server's time events

`EveryTenMinutes` fires before `EveryOneMinute` within one `GameTime.update` call, both argument-free and neither gated by side, the one-minute event guarded only by the minute stamp having changed [#2400/C/C-only].
On the minute that closes a ten-minute block, the ten-minute handlers therefore run first [#2400/C/C-only].
`OnTick` is triggered with `IngameState.numberTicks` as a double from `IngameState.onTick`, which `IngameState.updateInternal` calls outside any `GameServer.server` gate and after `UpdateStuff`, whose `GameTime.update` call is itself ungated, and the dedicated server constructs and drives an `IngameState` [#2401/C/C-only].
On a dedicated server `IngameState.update()`, and with it `GameTime.update` and `OnTick`, runs before `NetworkPlayerManager.update()` in the same pass of the server loop [#2402/C/C-only].
One pass of the server loop, in order [#2402/C/C-only] [#2401/C/C-only] [#2400/C/C-only]:

```
GameServer.main loop
  IngameState.update()
    updateInternal
      UpdateStuff -> GameTime.update     EveryTenMinutes, then EveryOneMinute
      onTick()                           OnTick(numberTicks)
  ...
  NetworkPlayerManager.update()          the player-stats push
```

A value a handler writes on `EveryOneMinute` or `OnTick` is therefore in place before the same pass's stats push runs [#2402/C/C-only]; the push and its cadence are [mp-model.md](mp-model.md#packets)'s.
Where the stat updaters and the `CalculateStats` hook sit inside the player update is [character-stats.md](../facts/character-stats.md#tick-order)'s.

<a id="disconnect"></a>
### Disconnect: the player leaves with no event

`GameServer.disconnectPlayer` triggers no Lua event and writes nothing to `ServerPlayerDB`; it removes the player from `IDToPlayerMap`, `UserNameToPlayerMap` and `GameServer.Players` and sets the connection's player id for that slot to `-1` [#2403/C/C-only].
From that point the player is absent from `getOnlinePlayers()`, which skips that id [#2403/C/C-only] [#2391/C/C-only].
A mod learns of the departure only by the player's absence from its next sweep of the online list [#2403/C/C-only].
A per-player table keyed on the username keeps its row across the gap, and the returning character is found again by the same key under whatever online id its new slot gives it [#2392/C/C-only].

## Walls and bounds
<a id="walls"></a>

The engine has no Lua event for a returning character's join and none for a disconnect: both server methods trigger nothing, so every join and every departure a mod sees is one it detects itself [#2386/C/C-only] [#2403/C/C-only].
`OnPlayerDeath` is unreachable on a dedicated server, whatever a mod registers on it [#2388/C/C-only].
`getPlayerFromUsername` has no server branch, so there is no server-side Lua lookup of a player by name [#2390/C/C-only].
A server-side global modData transmit cannot be aimed at one player [#2398/C/C-only].
The wiki mirror marks `OnNewGame` client-only, in its load-order line and in its event list, while the jar fires it on a dedicated server from `CreatePlayerPacket.processServer` with the new `IsoPlayer` [#2421/C/C-only].
Every row this page owns is a static read of the bytecode: none was exercised on a live server, and the join, respawn and reconnect ordering in particular has no session behind it.
Not covered: the SQL write of a connected player's row and how often it runs (`ServerPlayerDB.process`, its save thread and the `charactersToSave` drain), the client-driven character upload and whether it can overwrite a server-side edit to the same blob, the delayed disconnect and its username-keyed map, where the server calls `GlobalModData.save()` and the save-cycle events around it, the body of `NetworkPlayerManager.update`, the side of `OnCreateLivingCharacter` and `OnCharacterCreateStats`, the player-data, player-stats, player-fields, extra-info and load-profile packets, the shipped server Lua beyond its per-player sweep, every cause of death's entry into the death chain, and single player — none of them was read.

## Open
<a id="open"></a>

- How often the server writes `global_mod_data.bin` — settled by the file's modification times and the save log line with and without a write, beside a console save; -> [X49a](../areas/open-questions.md#x49a) [#2097/C/open].
- Whether a global modData value written a minute before a hard server stop survives a restart — settled by a write, a hard stop and a boot on the same run directory, beside a boot on the restored fixture that must miss it; -> [X49b](../areas/open-questions.md#x49b) [#2098/C/open].
- Whether a player's and the world's modData survive a save and reload — settled by a write, a teardown and a second boot on the same run directory, beside a control boot that must miss the key, in the player and the global scope; -> [X28](../areas/open-questions.md#x28) [#1294/C/open].
- The design must choose where a player's durable values live, because character modData rides in the blob the server stores [#2394/C/C-only] while one client transmit replaces the server's copy of that table [#1042/M/n=2], and global modData is a per-world file whose tables the mod keys itself [#2397/C/C-only].
- The design must choose whether a death is read from the event, from a sweep of `isDead()`, or from both, because the server fires `OnCharacterDeath` from the death chain [#2408/C/C-only] while whether every cause of death enters that chain on the server is not read.
- The design must choose whether a player's row is seeded on `OnNewGame` or on the first sweep that sees the username, because `OnNewGame` fires only for a new character [#2387/C/C-only] and a returning character arrives with no event [#2386/C/C-only].

## Worked examples

| shape | file:lines | what it shows |
|---|---|---|
| the server-side lookup by username | `testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Test.lua:52-62` | a scan of the online list with `size()` and `get(i)`, comparing `getUsername()`, in place of the client-only lookup by name |

## See also

- [mp-model.md](mp-model.md) — who owns each value, the command bus, the player-modData wipe, and the packets and their cadence.
- [lua-platform.md](lua-platform.md#events) — the event roster and which boot events a dedicated server fires.
- [wire-packets.md](../facts/wire-packets.md) — the fields each packet carries.
- [character-stats.md](../facts/character-stats.md#tick-order) — the stat updaters' place inside the player update.
- [lessons.md](lessons.md) — the standing rules on modData and cadence.
- [open-questions.md](../areas/open-questions.md) — the experiments this page's open rows wait on.
