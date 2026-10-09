# Server lifecycle
Verified against 42.20.4 (b0bbce05d5) · 2026-10-01 · scope: what a dedicated server does and fires when a player joins, is created, dies and leaves, how a player is addressed on the server, where per-player and world state is stored, and the order of the server's time events in a frame; the packets that carry state are `platform/mp-model.md`'s, their fields `facts/wire-packets.md`'s, and the stat updaters' place in the frame `facts/character-stats.md`'s.

## Rules
<a id="rules"></a>

- Key a per-player store on `getUsername()`, never on `getOnlineID()`: the online id is a recycled slot number, while the server's own player store is keyed on the username, with world and player index [#2410/C/inference] [#2392/C/C-only] [#2393/C/C-only].
- Treat `OnNewGame` on the server as the hook for every new character, including the one a client creates when its stored character is dead, and seed a player's row there: it fires from the character-creation packet with the new `IsoPlayer`, before the character is handed to the store, and a client whose stored character is dead or absent sends that packet when its world loads [#2411/C/inference] [#2387/C/C-only] [#2404/C/C-only] [#2420/C/C-only].
- Detect a join and a departure with a client-sent command or by diffing the usernames of `getOnlinePlayers()` on a sweep: the server fires no Lua event when a character joins or disconnects [#2412/C/inference] [#2386/C/C-only] [#2403/C/C-only] [#2391/C/C-only] [#3273/M/n=1].
- Never read a player's death on the server from `OnPlayerDeath`, and treat `OnCharacterDeath`, checked for an `IsoPlayer`, as the only death event the server can fire: `OnPlayerDeath` sits behind a server return and a local-player gate, while `OnCharacterDeath` fires from a death chain the server has entries into, though which causes of death reach that chain on the server is unread [#2413/C/inference] [#2388/C/C-only] [#2389/C/C-only] [#2408/C/C-only] [#2409/C/C-only].
- Never carry an online id across a reconnect: a disconnect sets the slot's id to `-1`, and the next connection takes the first free slot [#2414/C/inference] [#2403/C/C-only] [#2392/C/C-only].
- Look a player up on the server by scanning `getOnlinePlayers()`, never with `getPlayerFromUsername`: the latter delegates to the client instance with no server branch [#2415/C/inference] [#2390/C/C-only] [#2391/C/C-only].
- Keep one player's values out of any global modData table the server transmits: a server-side transmit sends the whole named table to every connection, with no per-player target [#2416/C/inference] [#2398/C/C-only] [#3290/M/n=1].
- Create a mod's world-scoped table whenever it is missing, with `ModData.getOrCreate`, rather than only when `OnInitGlobalModData`'s Boolean says so: that argument is the world dictionary's new-game flag, which read true on reload boots of one fixture world, so it says neither that the table is new nor that the world is, and the event fires after the load of `global_mod_data.bin`, which restores only the tables the file holds [#3287/C/inference] [#2396/C/C-only] [#2397/C/C-only] [#3284/M/n=1].
- Install the table `OnReceiveGlobalModData` hands over yourself, and treat a `false` second argument as no table: the event passes a freshly loaded table, or `false` when the packet carries none, and merges nothing into the receiver's copy [#2418/C/inference] [#2399/C/C-only].
- Count connected players with `getOnlinePlayers():size()`, never `getNumActivePlayers()`: the latter returns the local split-screen count [#2419/C/inference] [#2407/C/C-only] [#2391/C/C-only].

## How it works

This page follows one player through a dedicated server: the join, the creation of a new character, death, addressing, the two stores a mod can use, the world save and the stop, the order of the server's time events, and the disconnect.
The Lua events a dedicated server fires at boot, and the client-only events it never fires, are [lua-platform.md](lua-platform.md#events)'s.
Which side owns each value, and the routes a value can take between the sides, are [mp-model.md](mp-model.md#ownership)'s.
Every row tagged C is read from the bytecode; the readings tagged M were taken on a live dedicated server through the mod's own sweep and table: the departure and first sight on a reconnect [#3273/M/n=1], the mod's reset line on a driven respawn, whose only caller is its `OnNewGame` handler (inference) [#3279/M/n=1], one `ReduceGeneralHealth` death [#3278/M/n=1], the quit's save, the kill's loss and the restored fixture's empty table [#3275/M/n=1, #3280/M/n=1, #3282/M/n=1], and the new-game flag on reload boots [#3284/M/n=1].

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
On a live server a respawn driven through the post-death UI and the coop creation's accept ended in the mod's record reset: its log line, seen 0.007 s after the accept's reply returned, came with a fresh record whose reset count read 1, and the reset's only caller in the mod is its `OnNewGame` handler, so the run read the line and not the event [#3279/M/n=1].
After a hard kill the returning client's join logged the first sight as its only player line and no reset line, and the record read living with its resets 0, so the handler did not reset it, which character the store held not being read [#3281/M/n=1].

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
A server `ReduceGeneralHealth(110)` killed the character on a live server: the server read it dead at the first poll after the call, no departure was logged before the respawn, and the mod's sweep marked its record dead and kept it [#3278/M/n=1].
On a driven respawn the dead character stayed in `getOnlinePlayers` marked dead from its death until two ticks after `OnNewGame` fired, and the new character entered the list one tick later: death at tick 4296, `OnNewGame` at 4344 with the list still holding only the dead object, the dead object gone at 4346, the new one present at 4347; the mod's own online table kept the dead object until the next game-minute event, at tick 4351. [#3358/M/n=1]
The mod's own record of the respawned character was left marked dead: the server logged `store: reset record for admin (reset 1)` at frame 4344 and `players: admin is dead; record kept until respawn` at frame 4345, and the record read `dead` true with `resets` 1 at three reads spanning 8.6 s of wall after the respawn. [#3359/M/n=1]

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
After a reload the server hands the saved table to the client at join, a server-written key the client never held included [#2757/M/n=1].
When the server rewrites a connected player's row after creation, and whether a client's own upload can overwrite it, lie outside the rows here; [the walls](#walls) name them.
A mod's own table in global modData, keyed on the username, sits outside this blob altogether; the next section reads that store.

<a id="global-moddata"></a>
### Global modData: the world's own store

`OnInitGlobalModData` fires with one argument, the Boolean `WorldDictionary.isIsNewGame()`, after `GlobalModData.init` has run `reset()` and `load()` [#2396/C/C-only].
A handler that reads `false` finds only the tables the file held when the load ran, so a mod added to an existing world finds its own table absent [#2396/C/C-only] [#2397/C/C-only].
Where a mod initialises its world-scoped tables is [lessons.md](lessons.md#rules)'s standing rule.
Global modData lives in one file per save, `global_mod_data.bin` in the current save's folder, and `GlobalModData.save()` returns without writing under `Core.isNoSave()` [#2397/C/C-only].
On a dedicated server one save is one world, so the file is per world and outlives every connection [#2397/C/C-only].
With `SaveWorldEveryMinutes` at 0, the fixture's value, the server wrote the file only on a console `save` and on a clean `quit`, each logging one `Saving GlobalModData` line and moving the file's modification time once, while about 100 game-minutes with no write, about 100 game-minutes after a write and transmit, and every boot left it untouched [#2097/M/n=1].
A clean `quit` with no console save before it carried a key in the player scope and one in a global table to the next boot [#2756/M/n=1].
A key the server wrote into a player's modData, a key the client wrote and transmitted, and a key in a global table all survived a clean save and reload on the same world, while a boot on the restored fixture missed all three [#1294/M/n=1].
A global value written about one game-minute before the server process was hard-killed did not survive the restart, because no save ran in between [#2098/M/n=1].
The kill lost the world's progress since the last save along with it, so the restart resumed from the previous clean quit's save [#2758/M/n=1].
On a server whose autosave is off, a global table is therefore as durable as the last console save or clean quit [#2097/M/n=1] [#2098/M/n=1].
The console `save` and the autosave run `GlobalModData.save()` inside the world save on the server's main loop, and the quit save runs it on the JVM's shutdown-hook thread [#3420/C/C-only].
The save serialises every table into one heap buffer that starts at 1 MiB and grows by 512 KiB, re-serialising the overflowing table on each overflow, and the world save's pause for clients after 600 ms is checked only between its steps, never inside this one [#3421/C/C-only].
In the worked example this mod keeps no record in global modData: each player's inputs-only record is one JSON line in two alternating slot files, and its six golden-trace records at minute 240, with the trailing-24 h rings, the monotony table where laid and, for the smoker, the nicotine anchor among their inputs, encode at 5,973 to 7,765 bytes a line (mean 7,251.7); in the save's own global-modData format the same records are 13,253 to 13,537 bytes (mean 13,448.8) and 11,391.2 inputs-only on average, so a store of 500 would be 6,731,587 bytes of the file, where Plan 10c's records read 10,807.8 bytes on average, 8,774.2 inputs-only, and 500 of them 5,411,040. [#3651/C/inference]
A mod's own per-player table measured the same way: a clean quit and a reload carried its record equal in every leaf [#3275/M/n=1], a hard kill took it back to the last clean quit's record, a respawn and a version migration since then included, on a build whose record version has since been removed [#3280/M/n=1], and a boot on the restored fixture held no record until its first sight [#3282/M/n=1].
`OnInitGlobalModData` passed `true` on the three boots of one world and on a fresh-restore control, the two reuse boots, whose files held the records boot 1's clean quit had saved, included, so the flag did not separate a reload from a new world [#3284/M/n=1].
`ModData.transmit(name)` on a dedicated server sends the whole named table to every entry of `GameServer.udpEngine.connections`, with no per-player target and no `isFullyConnected` filter [#2398/C/C-only].
A table keyed by username and transmitted from the server is therefore every player's values on every client [#2398/C/C-only].
The per-player push a mod controls is the command bus's server send, which [mp-model.md](mp-model.md#command-bus) owns.
`OnReceiveGlobalModData` fires on the receiving side with `(name, table)`, the table freshly allocated and loaded from the packet, or with `(name, false)` when the packet carries no table, and the parse installs nothing itself [#2399/C/C-only].
A handler that does nothing with the table leaves the receiver's copy exactly as it was [#2399/C/C-only].
`GetModDataPacket.processServer` is exactly `triggerEvent("SendCustomModData")`, a server-side Lua event with no arguments [#2406/C/C-only].
That event names no player, so a handler cannot tell which client's request fired it [#2406/C/C-only].

<a id="save-and-stop"></a>
### Save and stop: no Lua event on the server

A dedicated server's world save, `ServerMap.QueuedSaveAll`, runs its steps in a fixed order with a client-pause check between them: the loaded cells, the player store, the visited world map, the chunk loader's queued saves, the reanimated players, the animal population, the collision data, the global object systems, the world-generation parameters, the instance and meta trackers, the radio, global modData, the entity manager and the world map's save file; its body references no `LuaEventManager` member [#3588/C/C-only].
The console `save` and the autosave queue it onto the main loop, and the quit runs it on the JVM's shutdown-hook thread [#3420/C/C-only].
The shutdown hook and the quit routine it calls fire no Lua event in their own bodies: the hook marks the server done and calls `QueuedQuit`, which waits for a zip backup, runs the quit save, broadcasts `ServerQuit`, sleeps 5 s and then stops or closes the server's subsystems one by one [#3589/C/C-only].
An ordinary save sends `StartPause` to the clients at its first check after 600 ms, and a quit save sends none [#3421/C/C-only].
`OnSave` is triggered only inside `GameWindow.save`, the client's and single player's save, which neither the world save nor the quit calls [#3590/C/C-only].
`OnPostSave` fires only where a client or single-player session ends [#2476/C/C-only].
`OnServerStartSaving` and `OnServerFinishSaving` fire on the client, from the pause packets the server's save sends, and `OnDisconnect` fires on the client alone [#3591/C/C-only] [#3592/C/C-only].
A stop therefore gives a mod no per-player Lua event, as a disconnect gives none [#3593/C/inference] [#2403/C/C-only].
A mod's `OnSave` and `OnPostSave` handlers never run on a dedicated server, so a mod that keeps files of its own has no flush hook and writes them on its own cadence [#3590/C/C-only] [#2476/C/C-only]; the standing rule is [lessons.md](lessons.md#rules)'s.
A hard kill saves nothing: a global value written about one game-minute before one did not survive the restart [#2098/M/n=1].

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
What this order costs a frame, with the packet pass and the day, hour and ten-minute arms around it, is [performance.md](performance.md#frame-order)'s.
`GameTime.update` fires `EveryOneMinute` at most once per update: when the stored previous minute stamp differs from the current one it triggers the event once and copies the current stamp over, however many game minutes the update advanced. [#3348/C/C-only]
A dedicated server fast-forwards while every live player in its player list is asleep: `GameServer.main` counts the live and the sleeping players each frame and calls `setFastForward` true only when `SleepAllowed` is on, at least one is live and the two counts are equal. [#3351/C/C-only]
At `DayLength` 1 (a fifteen-minute day) a dedicated server running at its ten-tick lock delivered 63 consecutive game minutes at a mean 6.270 `OnTick` calls each — 46 minutes of 6 ticks, 17 of 7, none of 0 — at 10.115 ticks and 1.600 world minutes per wall second. [#3346/M/n=1]
At the fixture's `DayLength` 4 (ninety minutes, the value every vanilla preset but SixMonthsLater ships) the same host delivered 50 consecutive game minutes at a mean 37.46 `OnTick` calls each — 28 of 38, 20 of 37, one of 29 and one of 40, none of 0 — at 10.011 ticks and 0.2665 world minutes per wall second. [#3347/M/n=1]
Under `settimespeed 30` at `DayLength` 1 the server delivered 213 `EveryOneMinute` calls in 214 ticks and never more than one between two ticks, while the world advanced 47.66 minutes per wall second at 10.05 ticks per second — about 4.7 game minutes per tick, each tick's 4.7 game minutes reaching Lua as one call. [#3349/M/n=1]
With both players held asleep on a server that allows sleep, the server fast-forwarded to 31.89 world minutes per wall second against 1.600 at speed 1, and delivered 213 `EveryOneMinute` calls in 213 ticks, never more than one between two ticks. [#3350/M/n=1]

<a id="disconnect"></a>
### Disconnect: the player leaves with no event

`GameServer.disconnectPlayer` triggers no Lua event and writes nothing to `ServerPlayerDB`; it removes the player from `IDToPlayerMap`, `UserNameToPlayerMap` and `GameServer.Players` and sets the connection's player id for that slot to `-1` [#2403/C/C-only].
From that point the player is absent from `getOnlinePlayers()`, which skips that id [#2403/C/C-only] [#2391/C/C-only].
A mod learns of the departure only by the player's absence from its next sweep of the online list [#2403/C/C-only].
A per-player table keyed on the username keeps its row across the gap, and the returning character is found again by the same key under whatever online id its new slot gives it [#2392/C/C-only].
On a live server a mod's sweep logged the departure, seen within 1.744 s of the start of the client's clean quit, and the same account's return brought a new first sight with its stored state, its first-seen age kept [#3273/M/n=1].
A client's quit and rejoin under the same username brought a new `IsoPlayer`: `bob` left the list at tick 2867 and a different object entered at tick 3516, and the mod logged the departure (frame 3289) and a new first sight (frame 3914) because one game-minute event fell between them; a log frame is read as the bench tick of the same number (inference). [#3360/M/n=1]

## Walls and bounds
<a id="walls"></a>

The engine has no Lua event for a returning character's join and none for a disconnect: both server methods trigger nothing, so every join and every departure a mod sees is one it detects itself [#2386/C/C-only] [#2403/C/C-only].
`OnPlayerDeath` is unreachable on a dedicated server, whatever a mod registers on it [#2388/C/C-only].
`getPlayerFromUsername` has no server branch, so there is no server-side Lua lookup of a player by name [#2390/C/C-only].
A server-side global modData transmit cannot be aimed at one player [#2398/C/C-only].
The engine fires no Lua event a mod can hook at a world save or a stop on a dedicated server: the save and the quit routines fire none in their own bodies, and `OnSave`, `OnPostSave`, `OnServerStartSaving`, `OnServerFinishSaving` and `OnDisconnect` fire only on a client or in single player [#3588/C/C-only] [#3589/C/C-only] [#3590/C/C-only] [#3591/C/C-only] [#3592/C/C-only] [#2476/C/C-only].
The wiki mirror marks `OnNewGame` client-only, in its load-order line and in its event list, while the jar fires it on a dedicated server from `CreatePlayerPacket.processServer` with the new `IsoPlayer` [#2421/C/C-only].
Every row tagged C is a static read of the bytecode; the live readings are two fixtures' with the world autosave off, the persistence readings under [the player store](#player-store) and [Global modData](#global-moddata) and the lifecycle readings of two reconnects, two driven respawns, one hard kill and one `ReduceGeneralHealth` death [#3273/M/n=1, #3279/M/n=1, #3280/M/n=1, #3278/M/n=1, #3358/M/n=1, #3360/M/n=1]; the join of a returning character beside the engine's own steps, the order of the engine's steps inside each of those events, apart from the list order of one driven respawn [#3358/M/n=1] and the new object of a rejoin [#3360/M/n=1], and every cause of death but one have no session behind them.
Not covered: the SQL write of a connected player's row and how often it runs (`ServerPlayerDB.process`, its save thread and the `charactersToSave` drain), the client-driven character upload and whether it can overwrite a server-side edit to the same blob, the delayed disconnect and its username-keyed map, the Lua calls inside the world save's and the quit's callees, the save cadence under a non-zero `SaveWorldEveryMinutes`, the body of `NetworkPlayerManager.update`, the side of `OnCreateLivingCharacter` and `OnCharacterCreateStats`, the player-data, player-stats, player-fields, extra-info and load-profile packets, the shipped server Lua beyond its per-player sweep, every cause of death's entry into the death chain, and single player — none of them was read.

## Open
<a id="open"></a>

- The design must choose where a player's durable values live, because character modData rides in the blob the server stores [#2394/C/C-only] while one client transmit replaces the server's copy of that table [#1042/M/n=2], and global modData is a per-world file whose tables the mod keys itself [#2397/C/C-only].
- The design must choose whether a death is read from the event, from a sweep of `isDead()`, or from both, because the server fires `OnCharacterDeath` from the death chain [#2408/C/C-only] while whether every cause of death enters that chain on the server is not read; the mod's sweep of the online list read one death, a server `ReduceGeneralHealth(110)`, as dead, and the event's own firing on the server was not read [#3278/M/n=1].
- The design must choose whether a player's row is seeded on `OnNewGame` or on the first sweep that sees the username, because `OnNewGame` fires only for a new character [#2387/C/C-only] and a returning character arrives with no event [#2386/C/C-only]; both seeds ran on a live server, the mod's reset line, whose only caller is its `OnNewGame` handler (inference), after a driven respawn [#3279/M/n=1] and a first sight from the sweep on a reconnect [#3273/M/n=1].

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
- [performance.md](performance.md#frame-order) — what the time events and the global modData save cost the server's frame.
- [open-questions.md](../areas/open-questions.md) — the experiments this page's open rows wait on.
