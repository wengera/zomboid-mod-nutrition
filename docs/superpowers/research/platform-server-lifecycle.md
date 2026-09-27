# Server-side player lifecycle — jar and Lua read

Build `42.20.4` · jar `b0bbce05d5` · read 2026-09-27 · C-grade throughout (static read of bytecode plus the shipped Lua; nothing here was run on a live server).

## Summary for the design

The dedicated server has no player-lifecycle events at all, and that is the single fact the design has to absorb. `GameServer.receivePlayerConnect` — the method that loads the character from the server's database, inserts it into `GameServer.Players`, `IDToPlayerMap` and `UserNameToPlayerMap`, assigns its online id and marks the connection fully connected — contains no `LuaEventManager.triggerEvent` call anywhere in its 928 bytes, and `GameServer.disconnectPlayer` contains none either. The only server-side hook that carries an `IsoPlayer` at an arbitrary moment is `OnClientCommand`, so a join handshake has to be initiated by the client and answered on the server; the only structural alternative is polling `getOnlinePlayers()` and diffing usernames, which is what the mod should do anyway as a safety net, because a client that never sends the handshake would otherwise never be ticked. The one genuine server-side character event is `OnNewGame`, fired from `CreatePlayerPacket.processServer` with `(IsoPlayer, nil)` just after the traits are applied and just before the character is written to the database — and since a respawn after death goes through the same packet, `OnNewGame` is both the character-creation hook and the respawn hook, which is exactly how vanilla uses it in `server/XpSystem/XpUpdate.lua`.

Death is worse than join: `IsoPlayer.OnDeath` returns at its fourth instruction when `GameServer.server` is set, so `OnPlayerDeath` cannot fire on a dedicated server, and `IsoPlayer.updateWhileDead` likewise returns false immediately. `OnCharacterDeath` is triggered ungated as the first instruction of `IsoGameCharacter.OnDeath`, which `IsoPlayer.OnDeath` reaches through `super` before its own gate — but I could not find what calls `OnDeath` in the first place, so whether it fires server-side for a player is unsettled and the mod should poll `isDead()` rather than trust it. The server's notion of a player's health is in any case client-reported: `PlayerHealthPacket.parse` writes each body part's health from the wire and then recomputes the overall value.

Addressing is the second trap. `getOnlineID()` is `slot * 4 + playerIndex`, where `slot` is the first `null` entry of `SlotToConnection` — a recycled number, so it is neither stable across a reconnect nor unique over time; `disconnectPlayer` sets it back to `-1` and frees the slot for whoever connects next. `getSteamID()` is set only under Steam mode. `getPlayerFromUsername` is a three-instruction delegate to `GameClient.instance` with no server branch at all, so calling it on a dedicated server is a null dereference — the server-side equivalent is the Java `GameServer.getPlayerByUserName`, or a scan of `getOnlinePlayers()`. `getNumActivePlayers()` returns the local split-screen count and is useless online. That leaves `getUsername()` as the only stable key, which is also the key the engine's own `networkPlayers` table uses.

The third and most consequential finding is that character modData is not persisted. `getModData()` is declared on `IsoObject`, but the character save chain — `IsoPlayer.save(ByteBuffer, boolean)` → `IsoGameCharacter.save` → `IsoMovingObject.save` — never reaches `IsoObject.save` and never references `getModData`; it ends at `PlayerCraftHistory.save`. So the blob in `networkPlayers.data` carries `Nutrition`, `Fitness`, traits and read books, but nothing a mod put in `player:getModData()`. Vanilla's own use of character modData (`xpUpdate.getModData`, which lazily writes the four fitness keys on the server's first `EveryTenMinutes` sweep — the 22-33 s appearance the library already records) is a live cache, not a store. A server-authoritative nutrition store therefore has to be the mod's own table in global modData, keyed on username, saved into `global_mod_data.bin`; character modData remains useful only as the per-session mirror.

Mirroring to one client must not go through `ModData.transmit`, whose server branch loops every entry of `udpEngine.connections` and sends the whole named table to all of them, with no `isFullyConnected` filter — a per-player nutrition table broadcast to the whole server. `sendServerCommand(playerObj, ...)` is the right instrument. On the receiving side `OnReceiveGlobalModData` hands Lua a freshly allocated table, or `(name, false)` when the packet carries none, and installs nothing itself.

Cadence is the one comfortable part. `EveryTenMinutes` and `EveryOneMinute` are both triggered inside `GameTime.update`, ungated by side and argument-free, with the ten-minute event first; `OnTick` is triggered from `IngameState.onTick` with the tick count as a double, outside any server gate, and the dedicated server does construct and drive an `IngameState`. Within one server frame the order is world and player updates, then `GameTime.update` and its time events, then `OnTick`, then `NetworkPlayerManager.update` — so a value written on `EveryOneMinute` or `OnTick` is carried by the same frame's 1 Hz stats push. The recommended shape is therefore: open the store on `OnInitGlobalModData` and `OnServerStarted`; seed a row on `OnNewGame`; confirm and mirror on a client-initiated `OnClientCommand`; sweep `getOnlinePlayers()` with `size()`/`get(i)` on `EveryOneMinute` to tick, to detect deaths by `isDead()`, and to detect departures by absence; and key everything on `getUsername()`. All of that is a static reading — grade C, bound C-only — and the join, respawn and reconnect ordering in particular wants a live run before anything is built on it.

## A. Every Lua event the server fires that carries a player or a connection

"Side" is where the `triggerEvent` call site can run: **both** = the class runs on client and dedicated server, **server** = the call site is inside a server-gated method or a server-only class, **client** = client-only class.

| event | args | side | when | cite |
|---|---|---|---|---|
| `OnClientCommand` | `module, command, IsoPlayer, table` | server | on every `sendClientCommand` arriving at the server; the bus the mod already uses | literal in `zombie/network/GameServer`, `zombie/Lua/LuaManager$GlobalObject`, `zombie/globalObjects/SGlobalObjectSystem`, `zombie/spnetwork/SinglePlayerServer` |
| `OnServerStarted` | none | server | once, after the world is loaded and before any client can join | literal in `zombie/network/GameServer` |
| `OnPlayerUpdate` | `IsoPlayer` | both | per player per frame from the player's own update | literal in `zombie/characters/IsoPlayer` |
| `OnPlayerMove` | `IsoPlayer` | both | per player per frame while moving | literal in `zombie/characters/IsoPlayer` |
| `OnPlayerDeath` | `IsoPlayer` | both | in the player's death path | literal in `zombie/characters/IsoPlayer` |
| `OnCharacterDeath` | `IsoGameCharacter` | both | generic character death; also fired for animals | literal in `zombie/characters/IsoGameCharacter`, `zombie/characters/animals/IsoAnimal` |
| `OnCreateLivingCharacter` | `IsoPlayer, SurvivorDesc` | both? | character construction | literal in `zombie/characters/IsoPlayer`, `zombie/characters/IsoSurvivor` |
| `OnNewGame` | `IsoPlayer, square` | both? | literal lives in the join packet as well as `IsoWorld` | literal in `zombie/network/packets/character/CreatePlayerPacket`, `zombie/iso/IsoWorld` |
| `OnConnected` | none | client | client's own connect state machine | literal in `zombie/gameStates/ConnectToServerState` only |
| `OnDisconnect` | none | client | client losing the server | literal in `zombie/network/GameClient` only |
| `OnServerPlayerLogin` / `OnPlayerConnect` | — | — | **absent from the jar** (§ E) | jar-wide grep |

Resolved gating, from the call sites:

| site | reading |
|---|---|
| `IsoPlayer.OnDeath @1 L7087` | calls `super.OnDeath()` **first** — `invokespecial zombie/characters/IsoLivingCharacter.OnDeath`, which `IsoLivingCharacter` does not define, so it resolves to `IsoGameCharacter.OnDeath` |
| `IsoGameCharacter.OnDeath @0 L4905` | `ldc_w 'OnCharacterDeath'` → `triggerEvent(name, this)`, the very first instruction, **ungated**: this is the death event the dedicated server sees |
| `IsoPlayer.OnDeath @4 L7088` | `getstatic zombie/network/GameServer.server; ifeq 11; return` — on a dedicated server the method **returns at L7089**, before anything else |
| `IsoPlayer.OnDeath @57 L7105` | `isLocalPlayer()` gate around `ldc_w 'OnPlayerDeath'` @64 L7106 — so `OnPlayerDeath` is client-only **and** local-player-only |
| `IsoPlayer.updateInternal2 @1141 L2438` | `ldc_w 'OnPlayerUpdate'` → `triggerEvent(name, this)`; `@852 L2385` is `OnPlayerMove` in the same method |
| `GameServer.receivePlayerConnect` | **no `LuaEventManager.triggerEvent` anywhere in the method** (offsets 0-928, L2762-L2870) — the server fires no Lua event when a player joins |
| `IsoPlayer.updateWhileDead @0 L7610` | opens `getstatic zombie/network/GameServer.server` — the dead-player update path is side-split |

## B. The player registry on the server

| accessor | server behaviour | cite |
|---|---|---|
| `getOnlinePlayers()` | server branch returns `GameServer.getPlayers()`; client branch `GameClient.instance.getPlayers()`; neither → a fresh empty `ArrayList` | `LuaManager$GlobalObject.getOnlinePlayers @0 L4034` (server), `@10 L4037`, `@23 L4040` |
| `GameServer.getPlayers()` | allocates a **new** `ArrayList` per call and delegates to `getPlayers(list)` — so every Lua call is a fresh snapshot and a fresh allocation | `GameServer.getPlayers @0 L3573` |
| `GameServer.getPlayers(list)` | `list.clear()`, then walks `udpEngine.connections`, and for each connection slots `0..3` of `UdpConnection.players`, adding any non-null player whose `onlineId != -1` | `GameServer.getPlayers @0 L3559`, the `iconst_4` slot bound `@40 L3562`, the null and `-1` filters `@52-63 L3564` |
| `getPlayerByOnlineID(int)` | server branch reads `GameServer.IDToPlayerMap` (a `HashMap<Short, IsoPlayer>`), client branch `GameClient.IDToPlayerMap`, else `null` | `LuaManager$GlobalObject.getPlayerByOnlineID @0 L3659`, `@21 L3662`, `@42 L3665` |
| `getPlayerFromUsername(String)` | **client-only, unguarded**: the whole body is `GameClient.instance.getPlayerFromUsername(name); areturn` — no `GameServer.server` branch, so on a dedicated server it dereferences a null `GameClient.instance` | `LuaManager$GlobalObject.getPlayerFromUsername @0 L7709` (3 instructions) |
| `getNumActivePlayers()` | returns `IsoPlayer.numPlayers`, the *local* split-screen count — not the online count | `LuaManager$GlobalObject.getNumActivePlayers @0 L3624` |
| `GameServer.getPlayerByUserName(String)` | the server-side name lookup: walks connections × 4 slots and matches `getDisplayName()` **or** `getUsername()` | `GameServer.getPlayerByUserName @48-79 L2357-L2358` |
| `getPlayerInfo(IsoPlayer)` | builds a Kahlua table with `OnlineID`, `RealX`, `RealY`, `X`, `Y`, then reads `getNetworkCharacterAI()` — a debug/diagnostic shape, not an identity source | `LuaManager$GlobalObject.getPlayerInfo @21-101 L7060-L7065` |

### How the online id is allocated — it is a recycled slot number

`GameServer.receiveClientConnect` opens with `getFreeSlot()`; `-1` means full and the connection is denied `ServerFull` and force-disconnected (`@10-43 L2648-L2652`). The slot is then turned into the base id by `iload_2; iconst_4; imul; i2s` — **`baseId = slot * 4`** (`@44-48 L2654`) — stored into `SlotToConnection[slot]` (`@117 L2666`) and into `UdpConnection.playerIds[0]` (`@123-129 L2667`). `getFreeSlot` is a linear scan of `SlotToConnection` for the first `null` (`GameServer.getFreeSlot @12-21 L2637-L2638`), so a freed slot is handed straight to the next connection.

Consequences for addressing a player:

| identifier | stability | cite |
|---|---|---|
| `getOnlineID()` (`short onlineId`) | **not stable**: `slot * 4 + playerIndex`, and the slot is the first free index in `SlotToConnection`; a reconnect after someone else has taken the slot gets a different id, and a reconnect into the same free slot gets the *same* id as the departed player did. Never a store key. | `receiveClientConnect @44 L2654`; `receivePlayerConnect @328-390 L2804-L2808` sets it from `connection.getPlayerId(playerIndex)` |
| `getUsername()` | set on the server from the login name argument: `player.username = arg2` at `receivePlayerConnect @450-453 L2818`, and it is what `ServerPlayerDB.serverLoadNetworkCharacter` was keyed on a moment earlier | `receivePlayerConnect @128-141 L2779`, `@450 L2818` |
| `getSteamID()` (`long`) | set only under `SteamUtils.isSteamModeEnabled()`: `player.setSteamID(connection.getSteamId())`; zero/absent on a non-Steam (hosted, local, or `-nosteam`) server | `receivePlayerConnect @416-433 L2813-L2815` |
| the `IsoPlayer` object | valid only between `receivePlayerConnect` and the disconnect; a reference held across a reconnect is a stale object | § A, § B |

Up to **four** players share one connection (`UdpConnection.players[4]`, slots `0..3`, and `receivePlayerConnect` rejects `playerIndex >= 4` at `@48-67 L2768-L2769`), so a username is not one-per-connection on a split-screen client.

## C. Durable per-player storage the server controls

The dedicated server's player store is a SQLite table `networkPlayers`, reached only through `zombie/savefile/ServerPlayerDB`.

| fact | reading | cite |
|---|---|---|
| the table and its key | `SELECT id, x, y, z, data, worldversion, isDead FROM networkPlayers WHERE username=? AND world=? AND playerIndex=?` — and, only when `GameServer.coop && SteamUtils.isSteamModeEnabled()`, the same query keyed on `steamid=?` | `ServerPlayerDB.serverLoadNetworkCharacter @32 L289` (steam), `@39 L291` (username) |
| the key is **(username or steamid, world, playerIndex)** | `setString(1, name)`, `setString(2, Core.gameSaveWorld)`, `setInt(3, playerIndex)` | `ServerPlayerDB.serverLoadNetworkCharacter @55-84 L295-L298` |
| `playerIndex` is bounded to `0..3` | the method returns `null` immediately for `< 0` or `>= 4` | `ServerPlayerDB.serverLoadNetworkCharacter @0-10 L281-L282` |
| the character is rebuilt from the blob | `new IsoPlayer(IsoWorld.instance.currentCell)`, `serverPlayerIndex = playerIndex`, then `player.load(buffer, worldversion)` | `ServerPlayerDB.serverLoadNetworkCharacter @203-232 L312-L315` |
| a corrupt blob deletes the row | the `load` catch logs `The server cannot load player data.` then runs `DELETE FROM networkPlayers WHERE username=?/steamid=? AND world=? AND playerIndex=?` and returns `null` | `@238-249 L317-L318`, `@278 L321`, `@285 L323`, `@389-406 L332` |
| a dead row loads as a corpse | if the `isDead` column is true: `getBodyDamage().setOverallBodyHealth(0)` and `setHealth(0)` | `@407-427 L334-L336` |
| **no row → `null`** | the "no `ResultSet.next()`" branch returns `null` | `@93-100 L299`, `@462-479 L344` |
| `null` kicks the client | `receivePlayerConnect` kicks with `UI_LoadPlayerProfileError` and force-disconnects | `GameServer.receivePlayerConnect @143-165 L2782-L2785` |
| the loaded player is `remote = 1` | set on the server's copy before it is returned | `@427-433 L338-L339`; also `receivePlayerConnect @313-318 L2800` |

### Where the row comes from, and when it is written

| fact | reading | cite |
|---|---|---|
| a brand-new character is created **on the server** | `CreatePlayerPacket.processServer` does `new IsoPlayer(IsoWorld.instance.currentCell, survivorDescriptor, 0,0,0)`, then `setX/setY/setZ/setDir`, `applyTraits(characterTraits)`, `applyProfessionRecipes()`, `applyCharacterTraitsRecipes()`, `setUsername(connection.getUserName())` and, under Steam, `setSteamID(connection.getSteamId())` | `CreatePlayerPacket.processServer @941-1064 L272-L284` |
| **`OnNewGame` fires on the dedicated server** | `ldc_w 'OnNewGame'; aload player; aconst_null; invokestatic LuaEventManager.triggerEvent` — args `(IsoPlayer, nil)`; the second argument (the square) is a hard `null` on this path | `CreatePlayerPacket.processServer @1067-1075 L287` |
| the new character is persisted immediately and synchronously | `ServerPlayerDB.getInstance().serverUpdateNetworkCharacter(player, playerIndex, connection)` then `ServerPlayerDB.getInstance().process()` on the same line pair, before the `CreatePlayer` reply is written back | `@1078-1096 L289-L290`, reply `@1099-1126 L292-L296` |
| `serverUpdateNetworkCharacter` is a queue push, not a write | the whole body is `charactersToSave.add(new NetworkCharacterData(player, playerIndex, connection))`; `process()` is what drains it | `ServerPlayerDB.serverUpdateNetworkCharacter @0-18 L192-L193` |
| what the queued row captures | `playerIndex`, `playerName` from `getDescriptor().getForename()/getSurname()`, `x`, `y`, `z`, `isDead()`, `IsoWorld.getWorldVersion()`, and a blob from `player.save(buffer)` into a `ByteBuffer.allocate(32768)` that retries at +32768 up to 1048576 on overflow | `NetworkCharacterData.<init> @9-114 L42-L57`, the growth loop `@118-148 L58-L67` |
| the snapshot is taken **at queue time**, on the server's own `IsoPlayer` | the buffer is filled inside the constructor, so whatever the server holds then is what persists | same |

### `getModData()` is not in the character blob

`getModData()` / `setModData` / `hasModData` / `transmitModData` are declared on **`zombie/iso/IsoObject`**, not on `IsoGameCharacter` or `IsoPlayer` (`methods zombie/iso/IsoObject` lists all four; `methods zombie/characters/IsoGameCharacter` lists only `getMusicIntensityEventModData` / `setMusicIntensityEventModData`, and `methods zombie/characters/IsoPlayer` only `getUnwantedModDataString`).

The character save chain never reaches `IsoObject.save`, and no link in it references `getModData`:

| link | reading | cite |
|---|---|---|
| `IsoPlayer.save(ByteBuffer, boolean)` | opens `invokespecial zombie/characters/IsoLivingCharacter.save`, runs through `Nutrition.save`, `Fitness.save`, `alreadyReadBook`, `saveKnownMediaLines`, `getVoiceType`, and **ends** at `PlayerCraftHistory.save` — the only string writes are `GameWindow.WriteString` at `@171` and `@215` | `IsoPlayer.save @11`, `@146` (Nutrition), `@444 L1518` (Fitness), `@521-524 L1529-L1530` |
| `IsoGameCharacter.save(ByteBuffer, boolean)` | `invokespecial zombie/iso/IsoMovingObject.save`, then descriptor/traits/…, ending at `PlayerCheats.save`; no `getModData` in its constant-pool use in this method | `IsoGameCharacter.save @17-22 L5334`, `@872-881 L5423-L5424` |
| `IsoMovingObject.save(ByteBuffer, boolean)` | writes its own fields (`Serialize`, `factoryGetClassID`, `offsetX`, `offsetY`, `getX`, …) and **does not call `IsoObject.save`** | `IsoMovingObject.save @17-72 L699-L705` |
| the single-player path is the same blob | `IsoPlayer.save()` builds a buffer, calls `player.save(buffer)` and writes `map_p.bin` via `ZomboidFileSystem.getFileNameInCurrentSave` | `IsoPlayer.save @144-159 L1553-L1555` |

So a nutrition store kept in `player:getModData()` on the server is **not** carried by `networkPlayers.data`. The mod's durable store must be something the mod writes itself (global modData, or its own table), keyed on username.

### Global modData — the store that does persist server-side

`ModData` (Lua) is a static facade: `ModData.transmit(n)` is `GlobalModData.instance.transmit(n); return` (`ModData.transmit @0-7 L46-L47`) and `ModData.getOrCreate(n)` is `GlobalModData.instance.getOrCreate(n); areturn` (`ModData.getOrCreate @0-7 L22`). Everything below is `zombie/world/moddata/GlobalModData`.

| fact | reading | cite |
|---|---|---|
| the init hook | `init()` is exactly `reset(); load(); triggerEvent("OnInitGlobalModData", WorldDictionary.isIsNewGame())` — **one argument, a Boolean `isNewGame`** | `GlobalModData.init @0-19 L56-L59` |
| where it is stored | `load()` reads `global_mod_data.bin` through `ZomboidFileSystem.getFileNameInCurrentSave` — one file per save, so per world on the server | `GlobalModData.load @10-19 L287` |
| load is skipped when the file is missing | if the file does not exist and `WorldDictionary.isIsNewGame()` is false, `load()` returns without clearing | `GlobalModData.load @29-42 L289-L294` |
| load wipes the in-memory map first | `modData.clear()` before reading, then an int version and an int count | `GlobalModData.load @64-73 L299`, `@108-120 L305-L306` |
| `save()` is a no-op under `-nosave` | `Core.getInstance().isNoSave()` → return; otherwise logs `Saving GlobalModData` | `GlobalModData.save @0-13 L224-L228` |
| the save format | a buffer sized `lastBlockSize` (or `1048576` the first time), then `putInt(249)` as the version and `putInt(modData.size())`, growing through `ensureCapacity` | `GlobalModData.save @16-57 L229-L232`, `@95-120 L236-L239` |
| `transmit(name)` on the **server** broadcasts | server branch builds one `GlobalModDataPacket`, then loops **every** entry of `GameServer.udpEngine.connections` and sends it — no `isFullyConnected` filter, no per-player targeting | `GlobalModData.transmit @75-81 L130`, the loop `@95-174 L132-L145` |
| `transmit(name)` on the **client** sends up | client branch sends one packet on `GameClient.connection` | `GlobalModData.transmit @10-58 L117-L124` |
| a null table only logs | `get(name) == null` falls to a `DebugLog.log` and returns | `GlobalModData.transmit @6-7 L116`, `@191-200 L148-L150` |
| the receive hook | `GlobalModDataPacket.parse` fires `triggerEvent("OnReceiveGlobalModData", name, table)`; when the packet's boolean is false it fires `(name, Boolean.FALSE)` instead — no table | `GlobalModDataPacket.parse @12-19 L49`, `@45-50 L55` |
| the received table is a **fresh** table | `LuaManager.platform.newTable()` then `KahluaTable.load(reader.bb, 249)` — nothing is merged into the existing one; Lua must install it | `GlobalModDataPacket.parse @23-40 L52-L53` |
| `request(name)` is client-side | the method opens on `GameClient.client` and sends a `GlobalModDataRequestPacket`; the server answers through `receiveRequest` | `GlobalModData.request @0-29 L154-L158` |

## D. Server-side per-minute and per-tick hooks that see every player

The dedicated server constructs and drives an `IngameState`: `GameServer.main` does `new IngameState()` at `@2582 L857` and calls `IngameState.update()` at `@3742` inside its loop, then `NetworkPlayerManager.getInstance().update()` at `@4687 L1171`.

| hook | args | trigger site | order within a server frame |
|---|---|---|---|
| `EveryTenMinutes` | none | `GameTime.update @1368-1371 L658`, ungated by side | 1st of the time events |
| `EveryOneMinute` | none | `GameTime.update @1407-1410 L665`, ungated, guarded only by `previousMinuteStamp != minutesStamp` (`@1395-1404 L664`) | fires **after** `EveryTenMinutes` in the same `GameTime.update` call |
| `EveryHours` | none | `GameTime.update @1199-1202 L628` | earlier in the same method than the two above |
| `EveryDays` | none | `GameTime.update @983-986 L596` and `@1108-1111 L611` (two sites) | earliest |
| `OnTick` | one number, `(double) IngameState.numberTicks` | `IngameState.onTick @0-11 L1615`, called from `IngameState.updateInternal @1331 L1531`, inside a `GameProfiler.profile("On Tick")` block and **not** inside a `GameServer.server` gate | after `UpdateStuff` |
| `OnTickEvenPaused` | `0.0` | `GameWindow.logic @506-513 L394`, behind `GameWindow.isIngameState()` in the **window** loop the dedicated server does not run | n/a server-side |
| `OnPlayerUpdate` | `IsoPlayer` | `IsoPlayer.updateInternal2 @1141 L2438` — per player, per update of that player | inside the world update, before `NetworkPlayerManager` |
| `OnServerStarted` | none | `GameServer.startServer @231-234 L1557` | once, at boot |
| `OnGameTimeLoaded` | none | `GameServer.main @2442-2445 L822` | once, at boot, before `IngameState` is constructed at `@2582` |

`GameTime.update` is reached from `IngameState.UpdateStuff` (`@104`, in the `L599` region, after the `GameServer.server` branch at `@65 L596`), and `UpdateStuff` is called at `updateInternal @1283 L1528` — i.e. **immediately before** `onTick()` at `@1331`. So the order in one server frame is: world and player updates (`OnPlayerUpdate`) → `GameTime.update` (`EveryDays`/`EveryHours`/`EveryTenMinutes`/`EveryOneMinute`) → `OnTick` → `NetworkPlayerManager.update` (the 1 Hz `syncStats` push). A write made on `EveryOneMinute` or `OnTick` is therefore picked up by the same frame's stats push.

## E. Absences

Each row is a jar-wide constant-pool grep, `./pz.sh grep "<literal>"`, on jar `b0bbce05d5`; "absent" means the tool answered `no class contains that literal`.

| literal grepped | result |
|---|---|
| `"OnServerPlayerLogin"` | absent |
| `"OnPlayerConnect"` | absent |
| `"OnPlayerJoin"` | absent |
| `"OnPlayerJoined"` | absent |
| `"OnPlayerLogin"` | absent |
| `"OnPlayerLoaded"` | absent |
| `"OnPlayerReady"` | absent |
| `"OnPlayerDisconnect"` | absent |
| `"OnPlayerLeave"` | absent |
| `"OnClientDisconnect"` | absent |
| `"OnServerPlayerDisconnect"` | absent |
| `"OnPlayerRespawn"` | absent |
| `"OnRespawn"` | absent |
| `"OnPlayerSpawn"` | absent |
| `"OnCreateCharacter"` | absent |
| `"OnPlayerDeathServer"` / `"OnCharacterDeathServer"` | absent |
| `"getPlayerByUsername"` | absent (the Lua global is `getPlayerFromUsername`, client-only; the Java server-side one is `GameServer.getPlayerByUserName`) |
| `"getPlayerBySteamID"` / `"getPlayerFromSteamID"` | absent |
| `"savePlayerModData"` / `"transmitPlayerModData"` | absent |

Two structural absences, from reading the methods rather than a grep:

- **`GameServer.receivePlayerConnect` triggers no Lua event at all.** The method runs from offset 0 to 928 (`L2762`-`L2870`) and contains no `zombie/Lua/LuaEventManager.triggerEvent` call. So a dedicated server gets no notification when an existing character joins — only when a *new* one is created (`OnNewGame`, § A/§ C).
- **`GameServer.disconnectPlayer` triggers no Lua event and writes nothing to `ServerPlayerDB`.** Offsets 0-399 (`L2576`-`L2633`): it stores safehouse safety, drops the player from the vehicle, `removeFromWorld()`, `removeFromSquare()`, removes the player from `PlayerToAddressMap`, `IDToAddressMap`, `IDToPlayerMap`, `UserNameToPlayerMap` and `GameServer.Players`, sets `connection.setUserName(idx, null)`, `setPlayerAt(idx, null)`, **`setPlayerId(idx, -1)`**, `setRelevantPos(idx, null)`, `setConnectArea(idx, null)`, sends `PlayerTimeout` to all, removes the player from `ServerLOS`, and logs. No `triggerEvent`, no `serverUpdateNetworkCharacter` (`@138-202 L2601-L2608`, `@264-296 L2618-L2620`, `@319-330 L2624`).
- `DeadCharacterPacket` (the parent of `DeadPlayerPacket`) has **no `processServer`** — only `processClient` — so the corpse packet is not where the server learns a player died (`methods zombie/network/packets/character/DeadCharacterPacket`).

## Recommended lifecycle

Derived from § A-§ E. **Untested** — nothing in this section was run on a live server; each step names the reading it rests on.

| phase | what the mod does | why |
|---|---|---|
| boot | `OnServerStarted` → open the durable store: `ModData.getOrCreate("Nutrition_Players")`, a table keyed by **username** | `OnServerStarted` is server-only and fires once (`GameServer.startServer @231 L1557`); global modData is already loaded by then if `OnInitGlobalModData` has run |
| boot, earlier | `OnInitGlobalModData(isNewGame)` → create the table if `isNewGame`, otherwise trust what `GlobalModData.load()` read from `global_mod_data.bin` | `GlobalModData.init @0-19 L56-L59` |
| **join** | there is **no join event**. Have the client send a `sendClientCommand` "hello" on its own `OnCreatePlayer`, and treat the matching `OnClientCommand(module, "hello", playerObj, args)` as the join hook | `receivePlayerConnect` triggers nothing (§ E); `OnClientCommand` is the only server hook that carries an `IsoPlayer` at an arbitrary moment (§ A) |
| join, fallback | poll `getOnlinePlayers()` on `EveryOneMinute` and diff against the mod's own set of usernames | `getOnlinePlayers()` is server-safe and returns only players with `onlineId != -1` (§ B) |
| new character | `OnNewGame(playerObj, nil)` → seed the store row for `playerObj:getUsername()`; this is also the respawn hook | `CreatePlayerPacket.processServer @1067 L287`; vanilla uses exactly this in a `server/` file (`XpUpdate.lua:397` → `xpUpdate.onNewGame` calls `getFitness():init()`) |
| key | key the store on `playerObj:getUsername()`, never on `getOnlineID()` | the online id is `slot * 4 + playerIndex` off a recycled free slot (§ B) |
| tick | `EveryOneMinute` → `local players = getOnlinePlayers(); for i=0,players:size()-1 do local p = players:get(i) ... end`, skipping `p:isDead()` | the vanilla server pattern, `XpUpdate.lua:299-304`; `size()`/`get(i)` because `#` on a Java list is forbidden (§ 5 of CLAUDE.md) |
| mirror | after writing, push to that client with `sendServerCommand(playerObj, module, cmd, t)`; do **not** use `ModData.transmit`, which broadcasts the whole named table to every connection | `GlobalModData.transmit @95-174 L132-L145` loops all `udpEngine.connections` |
| persist | write the store row on every change and let `GlobalModData.save()` carry it; do not rely on `player:getModData()` surviving | the character blob contains no modData (§ C) |
| leave | no leave event. On `EveryOneMinute`, any username in the mod's set that is no longer in `getOnlinePlayers()` has gone: flush its row and stop ticking it | `disconnectPlayer` triggers nothing and saves nothing (§ E) |
| death | no server-side player death event is established. Poll `p:isDead()` in the same `EveryOneMinute` sweep | the server's health comes from `PlayerHealthPacket.parse` writing each `BodyPart.SetHealth` then `calculateOverallHealth()` (`@46-78 L41-L44`); `IsoPlayer.OnDeath` returns at `@4 L7088` on the server and `updateWhileDead` returns `false` at `@0 L7610` |
| reconnect | the same username reappears in `getOnlinePlayers()` with a **new** `IsoPlayer` and possibly a different `getOnlineID()`; re-mirror from the store rather than from the object | § B |

## Claims candidates

Every row: grade **C**, bound **"C-only"** (static read of jar `b0bbce05d5`, build `42.20.4`, 2026-09-27; no live run).

| # | claim wording | pointer |
|---|---|---|
| 1 | A dedicated server fires no Lua event when an existing character joins: `GameServer.receivePlayerConnect` contains no `LuaEventManager.triggerEvent` call. | `C: GameServer.receivePlayerConnect`, offsets 0-928, `L2762`-`L2870` |
| 2 | `OnNewGame` fires on a dedicated server with arguments `(IsoPlayer, nil)` when a client creates a character. | `C: CreatePlayerPacket.processServer @1067-1075 L287` |
| 3 | `OnPlayerDeath` never fires on a dedicated server: `IsoPlayer.OnDeath` returns immediately when `GameServer.server` is set, and the event is additionally gated on `isLocalPlayer()`. | `C: IsoPlayer.OnDeath @4 L7088`, `@57-67 L7105`-`L7106` |
| 4 | `OnCharacterDeath` is triggered ungated as the first instruction of `IsoGameCharacter.OnDeath`, before `IsoPlayer.OnDeath`'s server gate. | `C: IsoGameCharacter.OnDeath @0-4 L4905`; `IsoPlayer.OnDeath @1 L7087` |
| 5 | `getPlayerFromUsername` is client-only and unguarded: its whole body delegates to `GameClient.instance`. | `C: LuaManager$GlobalObject.getPlayerFromUsername @0-7 L7709` |
| 6 | `getOnlinePlayers()` on a dedicated server allocates a fresh `ArrayList` per call and fills it from `udpEngine.connections` × 4 player slots, skipping nulls and `onlineId == -1`. | `C: GameServer.getPlayers @0 L3573`; `GameServer.getPlayers(list) @0-86 L3559`-`L3569` |
| 7 | A player's `getOnlineID()` on a dedicated server is `slot * 4 + playerIndex` where `slot` is the first free index of `SlotToConnection`, so it is recycled and is not stable across a reconnect. | `C: GameServer.receiveClientConnect @44-48 L2654`; `GameServer.getFreeSlot @12-21 L2637`-`L2638` |
| 8 | The dedicated server's durable player store is the SQLite table `networkPlayers`, keyed on `(username, world, playerIndex)` — or `(steamid, world, playerIndex)` under `coop && steam`. | `C: ServerPlayerDB.serverLoadNetworkCharacter @32 L289`, `@39 L291`, `@55-84 L295`-`L298` |
| 9 | Character modData is not in that store: `getModData` is declared on `IsoObject`, and the save chain `IsoPlayer.save` → `IsoGameCharacter.save` → `IsoMovingObject.save` never reaches `IsoObject.save` nor references `getModData`. | `C: IsoPlayer.save(ByteBuffer,Z) @521-524 L1529`-`L1530`; `IsoGameCharacter.save @17-22 L5334`; `IsoMovingObject.save @17-72 L699`-`L705` |
| 10 | A `serverLoadNetworkCharacter` that finds no row returns `null`, and `receivePlayerConnect` then kicks the client with `UI_LoadPlayerProfileError`. | `C: ServerPlayerDB.serverLoadNetworkCharacter @462-479 L344`; `GameServer.receivePlayerConnect @143-165 L2782`-`L2785` |
| 11 | `OnInitGlobalModData` fires with one argument, the Boolean `WorldDictionary.isIsNewGame()`, after `GlobalModData.reset()` and `load()`. | `C: GlobalModData.init @0-19 L56-L59` |
| 12 | Global modData lives in `global_mod_data.bin` in the current save, and `GlobalModData.save()` is a no-op under `Core.isNoSave()`. | `C: GlobalModData.load @10-19 L287`; `GlobalModData.save @0-13 L224`-`L228` |
| 13 | `ModData.transmit(name)` on a dedicated server sends the whole named table to every entry of `GameServer.udpEngine.connections`, with no per-player targeting and no `isFullyConnected` filter. | `C: GlobalModData.transmit @75-81 L130`, loop `@95-174 L132`-`L145` |
| 14 | `OnReceiveGlobalModData` fires on the receiving side with `(name, table)` where the table is a freshly allocated Kahlua table, or with `(name, false)` when the packet carries no table. | `C: GlobalModDataPacket.parse @12-19 L49`, `@23-50 L52`-`L55` |
| 15 | `EveryTenMinutes` fires before `EveryOneMinute` within one `GameTime.update` call, both ungated by side and both argument-free. | `C: GameTime.update @1368-1371 L658`, `@1407-1410 L665` |
| 16 | `OnTick` is triggered with `(double) IngameState.numberTicks` from `IngameState.onTick`, called from `updateInternal` outside any `GameServer.server` gate, and the dedicated server does run an `IngameState`. | `C: IngameState.onTick @0-11 L1615`; `IngameState.updateInternal @1331 L1531`; `GameServer.main @2582 L857`, `@3742` |
| 17 | On a dedicated server, `IngameState.update()` (hence `GameTime.update` and `OnTick`) runs before `NetworkPlayerManager.update()` in the same frame. | `C: GameServer.main @3742`; `@4687-4690 L1171` |
| 18 | `GameServer.disconnectPlayer` triggers no Lua event and writes nothing to `ServerPlayerDB`; it sets the connection's `playerId` for that slot to `-1` and removes the player from `IDToPlayerMap`, `UserNameToPlayerMap` and `GameServer.Players`. | `C: GameServer.disconnectPlayer @138-202 L2601`-`L2608`, `@286-296 L2619`-`L2620` |
| 19 | A new character is persisted synchronously at creation: `CreatePlayerPacket.processServer` calls `serverUpdateNetworkCharacter` then `ServerPlayerDB.process()` before replying. | `C: CreatePlayerPacket.processServer @1078-1096 L289`-`L290` |
| 20 | The server's copy of a player's body health is written by `PlayerHealthPacket.parse` from the client — per `BodyPartType`, then `calculateOverallHealth()` — so `isDead()` on the server is a client-reported state. | `C: PlayerHealthPacket.parse @46-78 L41`-`L44` |
| 21 | `GetModDataPacket.processServer` is exactly `triggerEvent("SendCustomModData")` — a server-side Lua event with no arguments. | `C: GetModDataPacket.processServer @0-5 L29`-`L30` |
| 22 | `getNumActivePlayers()` returns `IsoPlayer.numPlayers`, the local split-screen count, not the number of connected players. | `C: LuaManager$GlobalObject.getNumActivePlayers @0-3 L3624` |

## Not read

- **Who calls `IsoPlayer.OnDeath` / `IsoGameCharacter.OnDeath`.** `IsoGameCharacter.die()` calls `Kill(getAttackedBy())` then either `getNetworkCharacterAI().onDied()` (client) or `becomeCorpse()` (server) — `@30-50 L15819`-`L15822` — and neither `die()` nor the four-argument `Kill` references `OnDeath`. So whether `OnCharacterDeath` actually fires on a dedicated server for a *player* is unsettled: the trigger is ungated, but the path into it was not found. `pz.sh refs` lists outgoing references only, so callers cannot be found without a whole-jar method-body scan.
- **Which `IsoPlayer.save` overload `NetworkCharacterData.<init>` and `IsoPlayer.save()` invoke.** Both call sites push receiver + one `ByteBuffer` (`NetworkCharacterData.<init> @82-85 L53`; `IsoPlayer.save() @144-146 L1553`), yet `methods zombie/characters/IsoPlayer` lists only `save(Ljava/nio/ByteBuffer;Z)V`. Either pzdis drops an instruction or the listing is incomplete. It does not change claim 9 — no overload in the chain touches `getModData`.
- **`ServerPlayerDB.serverUpdateNetworkCharacterInt`** — the actual SQL write (INSERT vs INSERT-OR-REPLACE, and whether it is `process()` on the main thread or a save thread) was not dumped, so "how often a connected player's row is rewritten" is still open. `ServerPlayerDB.process`, `save`, `saveFinishWait` and the `charactersToSave` drain were not read.
- **`ServerPlayerDB.serverUpdateNetworkCharacter(ByteBuffer, UdpConnection)`** and `NetworkCharacterData.<init>(ByteBuffer, UdpConnection)` — the client-driven save path. Not read, so it is not established whether a client's periodic character upload can overwrite server-side edits to the same blob.
- **`GameServer$DelayedConnection.disconnect`** and where `addDelayedDisconnect` / `doDelayedDisconnect` are driven from; the delayed-disconnect map is keyed on `username` (`doDelayedDisconnect @6-16 L2554`), which suggests a save-then-drop, but that was not confirmed.
- **Where `GlobalModData.save()` is called from on a dedicated server** — the save cycle, `OnSave` / `OnPostSave` / `OnServerStartSaving` / `OnServerFinishSaving` (`StartPausePacket` holds the last two literals) were not read, so "when a global-modData write actually reaches disk" is open.
- **`NetworkPlayerManager.update`** was not dumped here (the brief supplied its behaviour); only its position in `GameServer.main` at `@4687 L1171` was read.
- **`OnCreateLivingCharacter` and `OnCharacterCreateStats` gating.** The literals are in `IsoPlayer` / `IsoSurvivor` and `LuaEventManager`, but their call sites were not dumped, so their side is marked "both?" in § A.
- **`PlayerDataRequestPacket.processServer`**, `PlayerStatsPacket`, `SyncPlayerFieldsPacket`, `ExtraInfoPacket` and `LoadPlayerProfilePacket` — not read.
- **The shipped Lua** was sampled, not swept: `XpUpdate.lua` (the vanilla server-side per-player pattern and the lazy fitness modData keys at lines 299-304 and 337-346) and `SpawnItems.lua`'s `OnNewGame` handler. `ClientCommands.lua`, `LuaNet.lua` and the `server/` tree at large were not read.
- **Single player** is out of scope throughout, per the library's rule.
