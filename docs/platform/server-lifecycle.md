# Server lifecycle
Verified against 42.20.4 (b0bbce05d5) · 2026-10-01 · scope: what a dedicated server does and fires when a player joins, is created, dies and leaves, how a player is addressed on the server, where per-player and world state is stored, and the order of the server's time events in a frame; the packets that carry state are `platform/mp-model.md`'s, their fields `facts/wire-packets.md`'s, and the stat updaters' place in the frame `facts/character-stats.md`'s.

## Rules

- Key a per-player store on `getUsername()`, never on `getOnlineID()`: the online id is a recycled slot number, while the server's own player store is keyed on the username, with world and player index [T11.25] [T11.7] [T11.8].
- Treat `OnNewGame` on the server as the hook for every new character, including the one a client creates when its stored character is dead, and seed a player's row there: it fires from the character-creation packet with the new `IsoPlayer`, before the character is handed to the store, and a client whose stored character is dead or absent sends that packet when its world loads [T11.26] [T11.2] [T11.19] [T11.35].
- Detect a join and a departure with a client-sent command or by diffing the usernames of `getOnlinePlayers()` on a sweep: the server fires no Lua event when a character joins or disconnects [T11.27] [T11.1] [T11.18] [T11.6].
- Never read a player's death on the server from `OnPlayerDeath`, and treat `OnCharacterDeath`, checked for an `IsoPlayer`, as the only death event the server can fire: `OnPlayerDeath` sits behind a server return and a local-player gate, while `OnCharacterDeath` fires from a death chain the server has entries into, though which causes of death reach that chain on the server is unread [T11.28] [T11.3] [T11.4] [T11.23] [T11.24].
- Never carry an online id across a reconnect: a disconnect sets the slot's id to `-1`, and the next connection takes the first free slot [T11.29] [T11.18] [T11.7].
- Look a player up on the server by scanning `getOnlinePlayers()`, never with `getPlayerFromUsername`: the latter delegates to the client instance with no server branch [T11.30] [T11.5] [T11.6].
- Keep one player's values out of any global modData table the server transmits: a server-side transmit sends the whole named table to every connection, with no per-player target [T11.31] [T11.13].
- Create a mod's world-scoped table whenever it is missing, with `ModData.getOrCreate`, rather than only when `OnInitGlobalModData`'s Boolean says the world is new: that argument says the world is new and not the table, and the event fires after the load of `global_mod_data.bin`, which restores only the tables the file holds [T11.32] [T11.11] [T11.12].
- Install the table `OnReceiveGlobalModData` hands over yourself, and treat a `false` second argument as no table: the event passes a freshly loaded table, or `false` when the packet carries none, and merges nothing into the receiver's copy [T11.33] [T11.14].
- Count connected players with `getOnlinePlayers():size()`, never `getNumActivePlayers()`: the latter returns the local split-screen count [T11.34] [T11.22] [T11.6].

## How it works

This page follows one player through a dedicated server: the join, the creation of a new character, death, addressing, the two stores a mod can use, the order of the server's time events, and the disconnect.
The Lua events a dedicated server fires at boot, and the client-only events it never fires, are [lua-platform.md](lua-platform.md#events)'s.
Which side owns each value, and the routes a value can take between the sides, are [mp-model.md](mp-model.md#ownership)'s.
Every row this page owns is read from the bytecode; none of them was exercised on a live server.

<a id="join"></a>
### Join: a returning character arrives with no event

A dedicated server fires no Lua event when an existing character joins: `GameServer.receivePlayerConnect`, which loads the character from the server's store and registers it, contains no `LuaEventManager.triggerEvent` call from its first instruction to its last [T11.1].
A `serverLoadNetworkCharacter` that finds no row returns `null`, and `receivePlayerConnect` then kicks the client with `UI_LoadPlayerProfileError` and force-disconnects it [T11.10].
So a character passes through `receivePlayerConnect` only once it has a row, and a brand-new character gets its row through [the creation path](#creation), not here [T11.10] [T11.19].
A client can announce itself over the command bus, whose server-side handler receives the sending player [#0932]; the bus is [mp-model.md](mp-model.md#command-bus)'s.
The server's own sweep of the online list, which [the addressing section](#ids) describes, finds a player whether or not its client ever sends that command.

<a id="creation"></a>
### Creation: `OnNewGame` on the server

`OnNewGame` fires on a dedicated server with the arguments `(IsoPlayer, nil)` when a client creates a character, from `CreatePlayerPacket.processServer` after it has built the `IsoPlayer`, applied its traits and set its username, the square argument being a hard null on this path [T11.2].
A new character is handed to the server's store at creation: `CreatePlayerPacket.processServer` calls `serverUpdateNetworkCharacter` and then `ServerPlayerDB.process()` after the `OnNewGame` trigger and before it writes its reply [T11.19].
A handler on `OnNewGame` therefore runs on a character that already has its username and traits and has not yet been queued for the store, so whatever the handler writes onto the character is in the first copy the store receives [T11.2] [T11.19].
On a client, `IsoWorld.init` takes the load path only when `ClientPlayerDB.clientLoadNetworkPlayer()` finds a network player and `isAliveMainNetworkPlayer()` says it is alive, and otherwise calls `GameClient.sendCreatePlayer`, which sends the `CreatePlayer` packet, so a client whose stored character is dead or absent creates a new one through `CreatePlayerPacket` when its world loads [T11.35].
The same event is therefore the hook for the character a client creates after a death, while a returning character with a living stored character never passes this way [T11.26].

<a id="death"></a>
### Death: the event the server sees

`OnPlayerDeath` never fires on a dedicated server: `IsoPlayer.OnDeath` returns at its `GameServer.server` gate before the trigger, and the trigger is further gated on `isLocalPlayer()` [T11.3].
`OnCharacterDeath` is triggered with the dying character as its one argument by the first instruction of `IsoGameCharacter.OnDeath`, with no side gate, and `IsoPlayer.OnDeath` calls that body through `super` before its own server return [T11.4].
So on the server a player's death fires `OnCharacterDeath` and nothing after it in `IsoPlayer.OnDeath`, provided the server reaches `OnDeath` at all [T11.3] [T11.4].
`IsoGameCharacter.DoDeath` is the only caller of `OnDeath` in the jar, and a player's `die()` reaches it through `Kill` and `IsoPlayer.onKilled`: `die()` calls `Kill(getAttackedBy())` while the kill is not yet done, `Kill` calls `onKilled`, `IsoPlayer.onKilled` calls `DoDeath` with or without an attacker, and `DoDeath`'s first instruction is the `OnDeath` call that fires `OnCharacterDeath` [T11.23].
The dedicated server has entries into that death chain for a player: `IsoGameCharacter.updateInternal` calls `die()` under `GameServer.server` for a dead character no longer on its square's moving-object list, `PlayerOnGroundState.execute` calls `die()` for any dead character with no side gate, `IsoPlayer.onKilled` counts the death in the server's statistics under `GameServer.server` before it calls `DoDeath`, and `DoDeath` writes the user-log death line and the `announceDeath` chat line only under `GameServer.server` [T11.24].
The chain, as the bytecode lays it out [T11.23]:

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

The event's argument is whatever character died, not only a player, so a handler that wants players tests the argument [T11.4].
`PlayerHealthPacket` runs from server to client: its one sender, `NetworkPlayerAI.syncHealth`, is gated on `GameServer.server` and sends to the player's own fully connected connection, its `@PacketSetting` annotation carries `handlingType 2`, the bit `PacketSetting$HandlingType.getType` sets for a packet type that has a client-side process and no server-side one, and its `parse` writes each body part's health and then recomputes the overall value on the receiving client [T11.20].
`PlayerHealthPacket` therefore does not write the server's body health; the client's copy is the one it writes [T11.20].
The code establishes server-side entries into the chain, not that every cause of death, starvation included, reaches one of them on the server; [the open section](#open) carries the decision that forces [T11.24].

<a id="ids"></a>
### Addressing a player on the server

`getOnlinePlayers()` on a dedicated server returns a freshly allocated `ArrayList` on every call, filled from each connection's four player slots, skipping an empty slot and a player whose online id is `-1` [T11.6].
The list is a snapshot: a player who connects or leaves after the call is not in it, so a handler that keeps the list across ticks keeps a stale one [T11.6].
Up to four players can share one connection on a split-screen client, so a connection is not a player [T11.6].
A Java list is walked from Lua with `size()` and `get(i)`; the Kahlua limits behind that are [lua-platform.md](lua-platform.md#kahlua-limits)'s.
A player's online id on a dedicated server is `slot * 4 + playerIndex`, where the slot is the first free index of `SlotToConnection`, so the id is recycled and is not stable across a reconnect [T11.7].
A reconnect after someone else has taken the slot gets a different id, and a reconnect into the same free slot gets the id the departed player had [T11.7].
The username is the identifier the server itself keys its store on, as [the player store](#player-store) shows.
`getPlayerFromUsername` is client-only and unguarded: its whole body delegates to `GameClient.instance`, with no `GameServer.server` branch [T11.5].
The server-side lookup by name is therefore a scan of `getOnlinePlayers()` comparing `getUsername()` [T11.5] [T11.6].
`getNumActivePlayers()` returns `IsoPlayer.numPlayers`, the local split-screen count, not the number of connected players [T11.22].

<a id="player-store"></a>
### The server's player store

The dedicated server's own player store is the SQLite table `networkPlayers`, read by username, world and player index, or by Steam id in the username's place when the server is a co-op host in Steam mode [T11.8].
The query reads back the character's position, its death flag and one serialised blob of the character [T11.8].
Character modData is saved in the blob the server stores in `networkPlayers`: `NetworkCharacterData` fills that blob through `IsoObject.save(ByteBuffer)`, which dispatches to `IsoPlayer.save`, whose chain through `IsoGameCharacter.save` reaches `IsoMovingObject.save`, which writes a presence byte and then the object's modData table, the field `getModData` returns, whenever that table is non-empty, and `IsoMovingObject.load` reads it back [T11.9].
The blob is filled when the row is queued, so it holds whatever the server's `IsoPlayer`, modData table included, holds at that moment [T11.9].
That table is also a channel the client writes: one client transmit makes the server's copy exactly the client's [#1042/M/n=2], and the rule that follows is [mp-model.md](mp-model.md#player-moddata)'s.
When the server rewrites a connected player's row after creation, and whether a client's own upload can overwrite it, lie outside the rows here; [the walls](#walls) name them.
A mod's own table in global modData, keyed on the username, sits outside this blob altogether; the next section reads that store.

<a id="global-moddata"></a>
### Global modData: the world's own store

`OnInitGlobalModData` fires with one argument, the Boolean `WorldDictionary.isIsNewGame()`, after `GlobalModData.init` has run `reset()` and `load()` [T11.11].
A handler that reads `false` finds only the tables the file held when the load ran, so a mod added to an existing world finds its own table absent [T11.11] [T11.12].
Where a mod initialises its world-scoped tables is [lessons.md](lessons.md#rules)'s standing rule.
Global modData lives in one file per save, `global_mod_data.bin` in the current save's folder, and `GlobalModData.save()` returns without writing under `Core.isNoSave()` [T11.12].
On a dedicated server one save is one world, so the file is per world and outlives every connection [T11.12].
When the server calls `save()`, and so when a write reaches the disk, is open; [the open section](#open) carries it.
`ModData.transmit(name)` on a dedicated server sends the whole named table to every entry of `GameServer.udpEngine.connections`, with no per-player target and no `isFullyConnected` filter [T11.13].
A table keyed by username and transmitted from the server is therefore every player's values on every client [T11.13].
The per-player push a mod controls is the command bus's server send, which [mp-model.md](mp-model.md#command-bus) owns.
`OnReceiveGlobalModData` fires on the receiving side with `(name, table)`, the table freshly allocated and loaded from the packet, or with `(name, false)` when the packet carries no table, and the parse installs nothing itself [T11.14].
A handler that does nothing with the table leaves the receiver's copy exactly as it was [T11.14].
`GetModDataPacket.processServer` is exactly `triggerEvent("SendCustomModData")`, a server-side Lua event with no arguments [T11.21].
That event names no player, so a handler cannot tell which client's request fired it [T11.21].

<a id="tick-order"></a>
### The order of the server's time events

`EveryTenMinutes` fires before `EveryOneMinute` within one `GameTime.update` call, both argument-free and neither gated by side, the one-minute event guarded only by the minute stamp having changed [T11.15].
On the minute that closes a ten-minute block, the ten-minute handlers therefore run first [T11.15].
`OnTick` is triggered with `IngameState.numberTicks` as a double from `IngameState.onTick`, which `IngameState.updateInternal` calls outside any `GameServer.server` gate and after `UpdateStuff`, whose `GameTime.update` call is itself ungated, and the dedicated server constructs and drives an `IngameState` [T11.16].
On a dedicated server `IngameState.update()`, and with it `GameTime.update` and `OnTick`, runs before `NetworkPlayerManager.update()` in the same pass of the server loop [T11.17].
One pass of the server loop, in order [T11.17] [T11.16] [T11.15]:

```
GameServer.main loop
  IngameState.update()
    updateInternal
      UpdateStuff -> GameTime.update     EveryTenMinutes, then EveryOneMinute
      onTick()                           OnTick(numberTicks)
  ...
  NetworkPlayerManager.update()          the player-stats push
```

A value a handler writes on `EveryOneMinute` or `OnTick` is therefore in place before the same pass's stats push runs [T11.17]; the push and its cadence are [mp-model.md](mp-model.md#packets)'s.
Where the stat updaters and the `CalculateStats` hook sit inside the player update is [character-stats.md](../facts/character-stats.md#tick-order)'s.

<a id="disconnect"></a>
### Disconnect: the player leaves with no event

`GameServer.disconnectPlayer` triggers no Lua event and writes nothing to `ServerPlayerDB`; it removes the player from `IDToPlayerMap`, `UserNameToPlayerMap` and `GameServer.Players` and sets the connection's player id for that slot to `-1` [T11.18].
From that point the player is absent from `getOnlinePlayers()`, which skips that id [T11.18] [T11.6].
A mod learns of the departure only by the player's absence from its next sweep of the online list [T11.18].
A per-player table keyed on the username keeps its row across the gap, and the returning character is found again by the same key under whatever online id its new slot gives it [T11.7].

## Walls and bounds
<a id="walls"></a>

The engine has no Lua event for a returning character's join and none for a disconnect: both server methods trigger nothing, so every join and every departure a mod sees is one it detects itself [T11.1] [T11.18].
`OnPlayerDeath` is unreachable on a dedicated server, whatever a mod registers on it [T11.3].
`getPlayerFromUsername` has no server branch, so there is no server-side Lua lookup of a player by name [T11.5].
A server-side global modData transmit cannot be aimed at one player [T11.13].
The wiki mirror marks `OnNewGame` client-only, in its load-order line and in its event list, while the jar fires it on a dedicated server from `CreatePlayerPacket.processServer` with the new `IsoPlayer` [T11.36].
Every row this page owns is a static read of the bytecode: none was exercised on a live server, and the join, respawn and reconnect ordering in particular has no session behind it.
Not covered: the SQL write of a connected player's row and how often it runs (`ServerPlayerDB.process`, its save thread and the `charactersToSave` drain), the client-driven character upload and whether it can overwrite a server-side edit to the same blob, the delayed disconnect and its username-keyed map, where the server calls `GlobalModData.save()` and the save-cycle events around it, the body of `NetworkPlayerManager.update`, the side of `OnCreateLivingCharacter` and `OnCharacterCreateStats`, the player-data, player-stats, player-fields, extra-info and load-profile packets, the shipped server Lua beyond its per-player sweep, every cause of death's entry into the death chain, and single player — none of them was read.

## Open
<a id="open"></a>

- How often the server writes `global_mod_data.bin` — settled by the file's modification times and the save log line with and without a write, beside a console save; -> [X49a](../areas/open-questions.md#x49a) [#2097/C/open].
- Whether a global modData value written a minute before a hard server stop survives a restart — settled by a write, a hard stop and a boot on the same run directory, beside a boot on the restored fixture that must miss it; -> [X49b](../areas/open-questions.md#x49b) [#2098/C/open].
- Whether a player's and the world's modData survive a save and reload — settled by a write, a teardown and a second boot on the same run directory, beside a control boot that must miss the key, in the player and the global scope; -> [X28](../areas/open-questions.md#x28) [#1294/C/open].
- The design must choose where a player's durable values live, because character modData rides in the blob the server stores [T11.9] while one client transmit replaces the server's copy of that table [#1042/M/n=2], and global modData is a per-world file whose tables the mod keys itself [T11.12].
- The design must choose whether a death is read from the event, from a sweep of `isDead()`, or from both, because the server fires `OnCharacterDeath` from the death chain [T11.23] while whether every cause of death enters that chain on the server is not read.
- The design must choose whether a player's row is seeded on `OnNewGame` or on the first sweep that sees the username, because `OnNewGame` fires only for a new character [T11.2] and a returning character arrives with no event [T11.1].

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
