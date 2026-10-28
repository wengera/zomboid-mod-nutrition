# Plan 23 jar reads: the square's edges, the hour and the dedicated server's sleep path

Read on build 42.21 (buildid 25485521, jar `4a0e9546ec`) · 2026-10-28 · Plan 23 Task 3 · scope: what the engine does behind the four calls the survivor's Lua builds on: the square-edge predicates (§ 1), the clock hour (§ 2), the dedicated server's sleep path (§ 3), and the vanilla bed-quality and zombie-count reads the client's sleep handler makes (§ 4).
Every cite is `Class.method @off L<n>` off a `pz.sh dump` of this jar; nothing here was run live.
Three readings needed a scratch parser rebuilt from the toolchain's own `cp.py` and `dis.py` modules, as [jar research](../../platform/jar-research.md#method) prescribes for what the shipped subcommands do not print: the target of each `invokedynamic` (the `BootstrapMethods` attribute, which `dump` prints as a bare `invokedynamic`), the case table of each `tableswitch` and `lookupswitch` (which `dump` prints without its keys), and a per-class caller scan narrowing each jar-wide grep.
The scratch scripts were session-scoped and are not kept; each reading they made is quoted below with the bytecode it resolved.

## 1. The square's edges

`IsoGridSquare.isBlockedTo(IsoGridSquare)` is the four-way or of a wall, a blocked window, a blocked door and a stair edge (`isBlockedTo(IsoGridSquare,GetSquare) @0–@40 L1120`):

```
      3         invokevirtual    zombie/iso/IsoGridSquare.isWallTo
      6         ifne             35
     12         invokevirtual    zombie/iso/IsoGridSquare.isWindowBlockedTo
     15         ifne             35
     21         invokevirtual    zombie/iso/IsoGridSquare.isDoorBlockedTo
     24         ifne             35
     29         invokevirtual    zombie/iso/IsoGridSquare.isStairBlockedTo
     32         ifeq             39
     35         iconst_1
```

`isWallTo`, `isWindowBlockedTo` and `isDoorBlockedTo` are each one call, `isEdgeElementTo(other, <predicate>, getSquare)` (`isWallTo @0–@11 L918`, `isWindowBlockedTo @0–@11 L1155`, `isDoorBlockedTo @0–@11 L1167`), and the predicate is a method reference the bootstrap table names: `IsoGridSquare.isWall(GridSquareEdge,GetSquare)` for the wall, `isBlockedWindow(GridSquareEdge,GetSquare)` for the window, `isBlockedDoor(GridSquareEdge,GetSquare)` for the door (`isWindowTo` and `isDoorTo` take `isWindow` and `isDoor`).

**Which edge of which square.** `isEdgeElementTo @0–@158 L3606–L3610` returns false when the argument is null or the square itself, then tests by coordinate alone, with no adjacency or level check:

```
      9         aload_0 / aload_1
     11  L3607  invokevirtual    zombie/iso/IsoGridSquare.isEastOf          (this.x > other.x, isEastOf @0–@16 L974)
     19         getstatic        GridSquareEdge.WEST     -> test(this,  WEST)
     33         getstatic        GridSquareEdge.EAST     -> test(other, EAST)
     47  L3608  invokevirtual    zombie/iso/IsoGridSquare.isWestOf          -> test(other, WEST), test(this, EAST)
     83  L3609  invokevirtual    zombie/iso/IsoGridSquare.isSouthOf         (this.y > other.y, isSouthOf @0–@16 L982)
     91         getstatic        GridSquareEdge.NORTH    -> test(this,  NORTH)
    105         getstatic        GridSquareEdge.SOUTH    -> test(other, SOUTH)
    119  L3610  invokevirtual    zombie/iso/IsoGridSquare.isNorthOf         -> test(other, NORTH), test(this, SOUTH)
```

`isEdgeElement(GridSquareEdge,BiPredicate,GetSquare) @0–@144 L3578–L3587` maps an edge to a square and a facing through `IsoGridSquare$1`'s switch map (`<clinit> @232–@296 L3563`: NORTH 1, WEST 2, SOUTH 3, EAST 4), whose case table reads key 1 → @50, 2 → @63, 3 → @76, 4 → @110:

```
     50  L3579  aload_2; aload_0; GridSquareEdgeFacingDirection.NORTH_SOUTH   (NORTH: this square, its N facing)
     63  L3580  aload_2; aload_0; GridSquareEdgeFacingDirection.EAST_WEST     (WEST: this square, its W facing)
     78  L3582  invokevirtual    zombie/iso/IsoGridSquare.getSouth            (SOUTH: the square at y+1, its N facing)
    112  L3586  invokevirtual    zombie/iso/IsoGridSquare.getEast             (EAST: the square at x+1, its W facing)
```

`getSouth @0–@20 L954` is the square at `(x, y+1, z)` and `getEast @0–@20 L946` the one at `(x+1, y, z)`, so a square stores only its own north and west edges and an east or south edge is the neighbour's west or north.
For the north neighbour, `isSouthOf` holds, and both tests land on this square's north edge (`this` NORTH, and `other.getSouth()`, which is this square, at its N facing); for the west neighbour, `isEastOf` holds, and both tests land on this square's west edge.
For the south or east neighbour the read is that neighbour's north or west edge.
A neighbour the `GetSquare` returns as null (an unloaded square) reads that edge as unblocked: the SOUTH and EAST branches return false on a null square (`isEdgeElement @83–@106 L3583`, `@117–@140 L3587`):

```
     78         invokevirtual    zombie/iso/IsoGridSquare.getSouth
     81         astore           4
     83  L3583  aload            4
     85         ifnull           106
    106         iconst_0
```

**The wall predicate.** `isWall(GridSquareEdgeFacingDirection) @0–@82 L1002–L1005` (switch map NORTH_SOUTH 1 → @46, EAST_WEST 2 → @59, `IsoGridSquare$1.<clinit> @301–@336 L962`):

```
     46  L1003  getstatic        zombie/iso/SpriteDetails/IsoFlagType.collideN
     50         invokevirtual    zombie/iso/IsoGridSquare.hasProperty
     53         ifeq             81
     59  L1004  getstatic        zombie/iso/SpriteDetails/IsoFlagType.collideW
     66         ifeq             81
     71  L1005  invokevirtual    zombie/iso/IsoGridSquare.isWindow
     74         ifne             81
     77         iconst_1
```

A wall edge is the square's `collideN` or `collideW` flag on an edge that does not also carry `windowN` or `windowW` (`isWindow(GridSquareEdgeFacingDirection) @46–@63 L1017–L1019`): it is a collision flag, so `isWallTo` is a movement wall and not a sight read.

**Doors.** `hasBlockedDoor(GridSquareEdgeFacingDirection) @0–@20 L1176` finds, among the square's `objects` list (`findObject(Class,BiPredicate,Object) @0–@63 L426–L433`), an object passing `isBlockedDoor(IsoObject,GridSquareEdgeFacingDirection) @0–@45 L1171–L1172`: an `IsoDoor` whose `isBlocked(GridSquareEdgeFacingDirection)` holds, or an `IsoThumpable` whose `isBlockedDoor(GridSquareEdgeFacingDirection)` holds; each first requires the object's own facing to match (`IsoDoor.isBlocked(GridSquareEdgeFacingDirection) @0–@20 L148`, `IsoThumpable.isBlockedDoor(GridSquareEdgeFacingDirection) @0–@20 L342`).

```
IsoDoor.isBlocked() @0–@19 L144
      1         invokevirtual    zombie/iso/objects/IsoDoor.isOpen
      4         ifeq             14          (closed -> true)
      8         invokevirtual    zombie/iso/objects/IsoDoor.isBarricaded
     11         ifeq             18          (open and not barricaded -> false)
```

`IsoThumpable.isBlockedDoor() @0–@26 L338` is the same rule behind `isDoor()`: a built door reads blocked when closed or barricaded.

**Windows.** `hasBlockedWindow(GridSquareEdgeFacingDirection) @0–@21 L1159` finds an `IsoWindow` passing `IsoWindow.isBlocked(GridSquareEdgeFacingDirection) @0–@20 L1277` (its facing matches and `isBlocked()`):

```
IsoWindow.isBlocked() @0–@26 L1273
      1         invokevirtual    zombie/iso/objects/IsoWindow.isDestroyed
      4         ifne             14
      8         invokevirtual    zombie/iso/objects/IsoWindow.IsOpen
     11         ifeq             21          (intact and closed -> true)
     15         invokevirtual    zombie/iso/objects/IsoWindow.isBarricaded
     18         ifeq             25          (open or smashed, not barricaded -> false)
```

The search is for `IsoWindow` objects only: the class literal `hasBlockedWindow @1 ldc_w zombie/iso/objects/IsoWindow` and its predicate's bootstrap target `IsoWindow.isBlocked(GridSquareEdgeFacingDirection)`. A player-built window, an `IsoThumpable`, is not read by `isWindowBlockedTo`, and blocks through `isBlockedTo` only if its sprite carries a collide flag, which is not read.

**Stairs.** `isStairBlockedTo @0–@47 L2570–L2580` reads true when this square is east of the other and `HasStairTopWest`, or south of it and `HasStairTopNorth`.

**`isSomethingTo`.** `isSomethingTo(IsoGridSquare,GetSquare) @0–@32 L874` is `isWallTo` or `isWindowTo` or `isDoorTo`, the last two presence tests whatever the state (`isDoor(GridSquareEdgeFacingDirection) @46–@63 L1040–L1042` reads the `doorN`/`doorW` flag), so it reads true across an open door or an open window, where `isBlockedTo` reads false.

**The diagonal rule.** The four coordinate branches are tested in turn, each falling through when false, so for a diagonal argument one x branch and one y branch both run, and the call reads true if either does. For the north-west diagonal `(x-1, y-1)` that is four edges: this square's west and north, the west edge of `(x, y-1)` (the other's `getEast`) and the north edge of `(x-1, y)` (the other's `getSouth`) — the four edges meeting at the shared corner, any one of which blocks.
`isEdgeElementTo` has no adjacency check, so for a square two or more away the tests read this square's edge and the edge of the square beside the other one, not the edges between.

Not read: which tile sprites carry `collideN`/`collideW` beside a door (`isWall` excludes only window edges, so a door frame that also carries the collide flag would read a wall when open); whether a low fence or a hoppable carries the collide flag; the window-frame-without-window case.

**Finding:** `isBlockedTo(n)` reads this square's own north edge for the north neighbour and its own west edge for the west neighbour (the south and east neighbours' north and west edges otherwise), as a `collideN`/`collideW` flag not on a window edge, a closed or barricaded door (an open one not), an intact closed or barricaded `IsoWindow` (an open or smashed one not; a player-built `IsoThumpable` window is not read), or a stair top, and a null (unloaded) south or east neighbour reads its edge unblocked; a diagonal reads blocked when any of the four edges meeting at the shared corner does; `isSomethingTo` reads any wall, window or door edge whatever its state.

Read with:

```
cd /c/Users/Angus/pz-b42
./pz.sh methods zombie.iso.IsoGridSquare
./pz.sh dump zombie.iso.IsoGridSquare isBlockedTo
./pz.sh dump zombie.iso.IsoGridSquare isWallTo
./pz.sh dump zombie.iso.IsoGridSquare isDoorBlockedTo
./pz.sh dump zombie.iso.IsoGridSquare isWindowBlockedTo
./pz.sh dump zombie.iso.IsoGridSquare isSomethingTo
./pz.sh dump zombie.iso.IsoGridSquare isEdgeElementTo
./pz.sh dump zombie.iso.IsoGridSquare isEdgeElement
./pz.sh dump zombie.iso.IsoGridSquare isWall
./pz.sh dump zombie.iso.IsoGridSquare isWindow
./pz.sh dump zombie.iso.IsoGridSquare isDoor
./pz.sh dump zombie.iso.IsoGridSquare hasBlockedDoor
./pz.sh dump zombie.iso.IsoGridSquare hasBlockedWindow
./pz.sh dump zombie.iso.IsoGridSquare isBlockedDoor
./pz.sh dump zombie.iso.IsoGridSquare findObject
./pz.sh dump zombie.iso.IsoGridSquare isStairBlockedTo
./pz.sh dump zombie.iso.IsoGridSquare isEastOf      # and isWestOf, isNorthOf, isSouthOf, getSouth, getEast
./pz.sh dump 'zombie.iso.IsoGridSquare$1' '<clinit>'
./pz.sh dump zombie.iso.objects.IsoDoor isBlocked
./pz.sh dump zombie.iso.objects.IsoWindow isBlocked
./pz.sh dump zombie.iso.objects.IsoThumpable isBlockedDoor
# plus the scratch invokedynamic and switch-table reads named above
```

## 2. The hour

`GameTime.getTimeOfDay() @0–@4 L851` returns the float field `timeOfDay`, and `setTimeOfDay(F) @0–@5 L855–L856` writes it.
`GameTime.update(Z)` advances it each update by `1 / getMinutesPerDay() / 60 × getMultiplier() / 2` (`@469–@536 L525–L534`) and wraps it, on the server and on a client alike (`@885–@911 L586–L587` for a client, `@938–@962 L598–L600` otherwise, the latter followed by `advanceOneDay`):

```
    942         ldc_w            24.0
    945         fcmpl
    946         iflt             974
    954         ldc_w            24.0
    957         fsub
    958         invokevirtual    zombie/GameTime.setTimeOfDay
    962         invokevirtual    zombie/GameTime.advanceOneDay
```

The step is skipped while the game is paused (`update @463–@466 L524`: `isGamePaused` then `ifne 804`, past the advance) and zeroed under the debug option `freezeTimeOfDay` (`@513–@526 L530–L531`).
A client's clock is also set from the server's: `SyncClockPacket.processClient @21–@26 L56` writes the packet's `timeOfDay` with `setTimeOfDay` (and `@4–@8 L54` sets `GameClient.fastForward` from it); the server sends it from `GameTime.update @804–@834 L575` every 10 s of wall time or on every update while fast-forwarding, when the clock crosses 7.0 and at the day rollover (`@836–@872 L576–L579`, `@965–@971 L601–L602`), the send itself at `@1261–@1266 L655–L656` (`syncClock`), and on each `setFastForward` change. So "on a client alike" covers the advance and the wrap; between syncs the client's clock runs on its own multiplier.

```
SyncClockPacket.processClient
     21    L56  aload_2
     23         getfield         zombie/network/packets/service/SyncClockPacket.timeOfDay
     26         invokevirtual    zombie/GameTime.setTimeOfDay
```

`getHour() @0–@22 L936–L937` is `floor(floor(timeOfDay × 3600) / 3600)`, the whole hour; `getMinutes() @0–@16 L466` is `(int)((timeOfDay − (int)timeOfDay) × 60)`, the minute within the hour.

**Finding:** `getTimeOfDay()` is the clock as a float hour in [0, 24), its whole part `getHour()` and its fraction times 60 truncated `getMinutes()`, wrapped by subtracting 24 at the update that reaches 24; it does not advance while the game is paused, and a client's clock is also reset to the server's at each clock sync.

Read with:

```
./pz.sh methods zombie.GameTime
./pz.sh dump zombie.GameTime getTimeOfDay
./pz.sh dump zombie.GameTime setTimeOfDay
./pz.sh dump zombie.GameTime getHour
./pz.sh dump zombie.GameTime getMinutes
./pz.sh dump zombie.GameTime update
./pz.sh dump zombie.network.packets.service.SyncClockPacket processClient
```

## 3. Sleep on a dedicated server

**What the client starts.** The vanilla handler `ISWorldObjectContextMenu.onSleepWalkToComplete` (`media/lua/client/ISUI/ISWorldObjectContextMenu.lua` L1034–L1110) refuses when any of the three zombie counts of § 4 is above 0 (L1036), sets the bed, the bed type, a force-wake-up clock hour of `sleepFor + getTimeOfDay()` wrapped at 24 (`sleepFor` from FATIGUE, the bed type and traits, clamped to 3–16 hours, L1057–L1082), `setAsleepTime(0.0)` and `setAsleep(true)` (L1084–L1088), and then on a client with `SleepAllowed` fades the screen and returns (L1094–L1100), before `getSleepingEvent():setPlayerFallAsleep` (L1103), which runs only in single player.
So in multiplayer the sleep is the client's own `asleep` flag and force-wake-up hour on its local player, and no sleeping-event data is set up.

**The writers of `asleep`.** Within the eleven classes a jar-wide grep for `setAsleep` names (the interface `ILuaGameCharacter` holds no code), the field `asleep` is written only by `IsoGameCharacter.setAsleep(Z) @0–@2 L2991`, `load @86` and `loadChange @321` (a per-class scan for a `putfield` of that name; a jar-wide grep for the bare field name, which would hit every `isAsleep`, was not narrowed, so a direct field write elsewhere is not excluded).
`setAsleep` is called from ten sites in eight of those classes: `SleepingEvent.wakeUp(IsoGameCharacter,boolean) @131`, `IsoPlayer.OnDeath @35`, `NetworkPlayerVariables.setBooleanVariables(IsoPlayer,ShortFlags) @40`, `SafeHouse.checkTrespass @56`, `SafeHouse.kickUserFromSafehouse @94`, `TeleportPacket.processServer @50`, `WakeUpPlayerPacket.processServer @5`, `ModalDialog.Clicked @95` and `AttackVehicleState.animEvent @197, @609`.
The two that carry a connected player's sleep to the server are the player packet and the wake packet.
The client's `asleep` reaches the server's copy through the player packet's flag word. On the sending side `NetworkPlayerVariables.getBooleanVariables(IsoPlayer) @26–@34 L46` sets the `isAsleep` flag from `isAsleep()` (`NetworkPlayerAI.set(PlayerPacket) @256` calls it):

```
     26    L46  aload_1
     27         getstatic        zombie/characters/NetworkPlayerVariables$Flags.isAsleep
     31         invokevirtual    zombie/characters/IsoPlayer.isAsleep
     34         invokevirtual    zombie/util/flags/ShortFlags.set
```

On the receiving side `PlayerPacket.processServer @47–@50 L170` calls `NetworkPlayerAI.parse(PlayerPacket)`, which at `@216–@224 L574` calls `NetworkPlayerVariables.setBooleanVariables`, which sets it from the `isAsleep` flag (`@32–@40 L74`):

```
     34         getstatic        zombie/characters/NetworkPlayerVariables$Flags.isAsleep
     37         invokevirtual    zombie/util/flags/ShortFlags.has
     40         invokevirtual    zombie/characters/IsoPlayer.setAsleep
```

The wake is the other writer: `WakeUpPlayerPacket.processServer @0–@21 L26–L28` sets `setAsleep(false)` and `setAsleepTime(0)` on the server's copy and relays the packet to the clients.

**`allPlayersAsleep` and `isOnlyPlayerAsleep`.** `IsoPlayer.allPlayersAsleep() @0–@77 L1056–L1065` counts the living entries of the process's local `IsoPlayer.players` array (`numPlayers`) and the asleep ones among them and returns true when there is at least one and all are asleep — the split-screen array, not the server's connected players (as #2788 read on 42.20.4).
Its jar callers are of two kinds: six are behind a side guard, two are not.
The guarded ones are the single-player branches of `GameTime.getMultiplier @18`, `getServerMultiplier @46` and `getUnmoddedMultiplier @18`, each guarded by `!GameServer.server && !GameClient.client` (`getMultiplier @0–@35 L982–L983`, the ×`200 × 30 / lockFPS` sleep speed), `IngameState.UpdateStuff @65–@80 L601–L602` (guarded by `!GameServer.server`), `SleepingEvent.wakeUp(IsoGameCharacter,boolean) @90–@99 L502` (guarded by `!GameClient.client`), and `ThumpState.getFastForwardDamageMultiplier @70 L398`, which reaches it only after its server and client branches return (`@4–@69 L392–L396`).
The two with no server or client guard are `IsoPlayer.updateStats_Sleeping @2–@16 L3299–L3300`, which multiplies the sleeping recovery factor (2, applied to ENDURANCE and then FATIGUE) by `getDeltaMinutesPerDay()` when it is true, and `ThumpState.execute @225–@236 L123`, which skips its thump branch when it is true:

```
IsoPlayer.updateStats_Sleeping
      0  L3298  fconst_2
      2  L3299  invokestatic     zombie/characters/IsoPlayer.allPlayersAsleep
      5         ifeq             17
      8  L3300  fload_1
     12         invokevirtual    zombie/GameTime.getDeltaMinutesPerDay
     15         fmul
ThumpState.execute
    225   L123  iload            7
    227         ifeq             791
    230         invokestatic     zombie/characters/IsoPlayer.allPlayersAsleep
    233         ifeq             239
    236         goto             791
```

On a multiplayer client whose one local player is asleep `allPlayersAsleep()` reads true, so both run there; on the dedicated server what they read depends on the unread content of the server's own `IsoPlayer.players`.
`isOnlyPlayerAsleep() @0–@66 L7064–L7072` returns false unless this player is asleep and false if any other living local player is asleep; a jar-wide grep finds the name only in `IsoPlayer` itself, with no caller there, and the vanilla Lua has none, so nothing gates on it.

**The server's fast-forward.** The server's main loop counts, over `GameServer.Players`, the living players and the asleep ones among them, and sets fast-forward when sleep is allowed and every living player is asleep (`GameServer.main @3910–@4055 L1052–L1069`):

```
   3945         invokevirtual    zombie/characters/IsoPlayer.isAlive
   3987  L1061  iinc             18 1
   3992         invokevirtual    zombie/characters/IsoPlayer.isAsleep
   3998  L1063  iinc             17 1
   4029         getfield         zombie/network/ServerOptions.sleepAllowed
   4035         ifeq             4054
   4040         ifle             4054        (no living player -> false)
   4047         if_icmpne        4054        (asleep != living -> false)
   4055         invokestatic     zombie/network/GameServer.setFastForward
```

`setFastForward(Z) @0–@15 L3903–L3908` writes the static and calls `syncClock` on a change, and it is the only writer of `GameServer.fastForward` (`main @4055` its only caller).
While it is set, `GameTime.getMultiplier() @38–@65 L988–L989` replaces its base 1 by `FastForwardMultiplier / getDeltaMinutesPerDay()`, before the shared factors and the `× 0.8` (`@103–@143 L994–L1001`):

```
     44         getstatic        zombie/network/GameServer.fastForward
     53         getfield         zombie/network/ServerOptions.fastForwardMultiplier
     61         invokevirtual    zombie/GameTime.getDeltaMinutesPerDay
     64         fdiv
```

`getDeltaMinutesPerDay() @0–@7 L446` is `30 / minutesPerDay`, `minutesPerDay` is set to `SandboxOptions.getDayLengthMinutes()` by `SandboxOptions.applySettings @50–@58 L594` through `GameTime.setMinutesPerDay` (`ConnectedPacket` also references `setMinutesPerDay`, unread), and `getDayLengthMinutes` (`@8–@66 L556–L561`) maps DayLength 1, 2, 3, 4 to 15, 30, 60, 90 minutes, and the ini's `FastForwardMultiplier` is a double option of minimum 1, maximum 100 and default 40 (`ServerOptions.<init> @1524–@1542`).
So the clock's rate is multiplied by `FastForwardMultiplier × minutesPerDay / 30`: 120 at the default 40 and the 90-minute day, 20 at DayLength 1 — the factor run x151s-20261005-165844 measured as "about 20 times" at DayLength 1 on 42.20.4 (#2956), whose bound left the mechanism an inference; that the factor matches the jar here is a reading, not a re-measurement. Since the time-of-day step divides by `minutesPerDay` (§ 2), the fast-forwarded game day takes about `30 / FastForwardMultiplier` real minutes whatever the day length (inference from the two formulas, the shared factors taken as unchanged).
`GameServer.fastForward` also suspends `AntiCheat.update` (#2861) and scales thump damage (`ThumpState.getFastForwardDamageMultiplier @10–@31 L393`); `SyncClockPacket` carries it to the clients, which set `GameClient.fastForward` from it.

**What `SleepNeeded` adds.** On the server, `IsoGameCharacter.calculateStats @8–@48 L10228–L10229` resets FATIGUE every update unless `SleepAllowed` and `SleepNeeded` are both true (as #3009 rests on).
`updateBeardAndHair @85–@137 L9583–L9587` runs its growth step for an asleep character always and for an awake one only when that flag is false, the flag being set in single player and, in multiplayer, when `SleepAllowed` and `SleepNeeded` are both true: so where sleep is not both allowed and needed, beard and hair grow awake too.
On a client, `ISWorldObjectContextMenuLogic.doSleepOption @208–@231 L3300` turns on the menu's gates only when `SleepNeeded` is true (or in single player): the sleep option is marked `notAvailable` at FATIGUE 0.3 or under (`@233–@258 L3301–L3302`, `IGUI_Sleep_NotTiredEnough`), with any zombie counted (`@282–@353 L3306–L3309`, `IGUI_Sleep_NotSafe`), or within one hour of the last sleep (`@358–@377 L3312–L3314`, `ContextMenu_NoSleepTooEarly`).
`doBedMenu @280–@311 L1467–L1471` offers the option on a client only when `SleepAllowed` is true.

**What wakes the player.** `IsoGameCharacter.updateInternal @1555–@1580 L9263–L9264` calls `IsoPlayer.processWakingUp` for an asleep player after `calculateStats`. `processWakingUp @0–@204 L3374–L3408` maps a force-wake-up hour of exactly 0 to 9.0 (`@0–@13 L3374–L3375`), wakes when the clock passes that hour between the last update and this one (the 24-hour wrap handled), when `getAsleepTime()` is above 16, on a local player in multiplayer at any aim or movement input, or on the `forceWakeUp` flag; it then calls `SleepingEvent.wakeUp`, sets the hour to -1 and, on a client, `GameClient.sendPlayer` (as #3029 read on 42.20.4).
The hour is left at -1 by every wake (`processWakingUp @184–@188 L3406`, `SleepingEvent.wakeUp @122–@126 L509`), and at -1 the clock test never holds: it wakes when `now >= hour` and `last < hour` (`@60–@83 L3388`), and `last` is at least 0, or at the day wrap the previous hour less 24, which is above -1 unless one update steps the clock by more than an hour:

```
      0  L3374  getfield         zombie/characters/IsoPlayer.forceWakeUpTime
      4         fconst_0
      5         fcmpl
      6         ifne             16
     10  L3375  ldc_w            9.0
     13         putfield         zombie/characters/IsoPlayer.forceWakeUpTime
     60  L3388  fload_1          (now)
     62         getfield         zombie/characters/IsoPlayer.forceWakeUpTime
     65         fcmpl
     66         iflt             82
     69         fload_2          (last)
     71         getfield         zombie/characters/IsoPlayer.forceWakeUpTime
     74         fcmpg
     75         ifge             82
     78         iconst_1
    185  L3406  ldc_w            -1.0
    188         putfield         zombie/characters/IsoPlayer.forceWakeUpTime
```

So a sleep started after an earlier wake without its own `setForceWakeUpTime` has no clock wake; only the 16-hour, input, force-flag and very-close-zombie wakes remain.
`SleepingEvent.wakeUp(IsoGameCharacter,boolean) @5–@26 L492–L493` sends `WakeUpPlayer` from a client for a non-remote character, which the server answers by `setAsleep(false)` as above; it then sets the force-wake-up hour to -1 and `setAsleep(false)` (`@122–@131 L509–L511`), and adjusts FATIGUE and the neck by bed type (#2278).
`getAsleepTime` advances in `GameTime.update @736–@795 L563–L570`, which also runs `SleepingEvent.update` for each asleep entry of the local `IsoPlayer.players` array; `SleepingEvent.update @10–@97 L300–L306` wakes the player at any very close zombie (with PANIC +70 and STRESS +0.5).

Not read: whether the dedicated server's own `IsoPlayer.players` array holds connected players (which decides whether the server runs `SleepingEvent.update` and advances `asleepTime` for them), whether the server's copy of a connected player runs `processWakingUp`, and whether the client's force-wake-up hour reaches the server's copy; the clients' clock under `GameClient.fastForward` was not traced past `getMultiplier @69–@102 L990–L991`.

**Finding:** on a dedicated server with `SleepAllowed`, a client's `setAsleep(true)` reaches the server's copy through the player packet's `isAsleep` flag, and when every living connected player reads asleep the server sets `fastForward`, which multiplies the clock's rate by `FastForwardMultiplier × minutesPerDay / 30` (120 at the default 40 and the 90-minute day); `allPlayersAsleep` reads the process's local players array and gates the single-player speed-up and, unguarded, `updateStats_Sleeping`'s recovery scale and `ThumpState.execute`, and `isOnlyPlayerAsleep` gates nothing; `SleepNeeded` adds the server's fatigue (no reset) and, on the client's menu, the tired, safe and too-early gates; the client wakes itself when the clock passes its force-wake-up hour (9.0 when it is 0; at -1, the value every wake leaves, never by the clock), after 16 hours asleep or at input, and tells the server by `WakeUpPlayer`.

Read with:

```
./pz.sh refs zombie.characters.IsoGameCharacter setAsleep
./pz.sh dump zombie.characters.IsoGameCharacter setAsleep
./pz.sh grep setAsleep
./pz.sh grep setForceWakeUpTime
./pz.sh dump zombie.characters.IsoPlayer allPlayersAsleep
./pz.sh dump zombie.characters.IsoPlayer isOnlyPlayerAsleep
./pz.sh grep allPlayersAsleep
./pz.sh grep isOnlyPlayerAsleep
./pz.sh grep fastForward
./pz.sh grep setFastForward
./pz.sh grep SleepAllowed
./pz.sh grep SleepNeeded
./pz.sh grep sleepAllowed
./pz.sh grep sleepNeeded
./pz.sh dump zombie.network.GameServer main --from 3880 --to 4080
./pz.sh dump zombie.network.GameServer setFastForward
./pz.sh dump zombie.GameTime getMultiplier
./pz.sh dump zombie.GameTime getServerMultiplier
./pz.sh dump zombie.GameTime getUnmoddedMultiplier
./pz.sh dump zombie.GameTime getDeltaMinutesPerDay
./pz.sh dump zombie.SandboxOptions getDayLengthMinutes
./pz.sh dump zombie.SandboxOptions applySettings --from 40 --to 62
./pz.sh dump zombie.characters.NetworkPlayerVariables getBooleanVariables --from 0 --to 40
./pz.sh dump zombie.ai.states.ThumpState execute --from 220 --to 240
./pz.sh dump zombie.network.ServerOptions '<init>'
./pz.sh dump zombie.gameStates.IngameState UpdateStuff --from 40 --to 130
./pz.sh dump zombie.ai.states.ThumpState getFastForwardDamageMultiplier
./pz.sh dump zombie.characters.IsoPlayer updateStats_Sleeping --from 0 --to 60
./pz.sh dump zombie.characters.IsoGameCharacter calculateStats --from 0 --to 60
./pz.sh dump zombie.characters.IsoGameCharacter updateBeardAndHair --from 80 --to 140
./pz.sh dump zombie.characters.IsoGameCharacter updateInternal --from 1530 --to 1600
./pz.sh dump zombie.iso.ISWorldObjectContextMenuLogic doBedMenu --from 250 --to 330
./pz.sh dump zombie.iso.ISWorldObjectContextMenuLogic doSleepOption
./pz.sh dump zombie.characters.IsoPlayer processWakingUp
./pz.sh dump zombie.ai.sadisticAIDirector.SleepingEvent wakeUp
./pz.sh dump zombie.ai.sadisticAIDirector.SleepingEvent update
./pz.sh dump zombie.network.packets.actions.WakeUpPlayerPacket processServer
./pz.sh refs zombie.network.packets.character.PlayerPacket processServer
./pz.sh dump zombie.network.packets.character.PlayerPacket processServer --from 30 --to 56
./pz.sh dump zombie.characters.NetworkPlayerAI parse --from 210 --to 228
./pz.sh dump zombie.characters.NetworkPlayerVariables setBooleanVariables --from 0 --to 60
# plus the per-class caller scans for setAsleep, asleep, setForceWakeUpTime, forceWakeUpTime, fastForward,
# setFastForward, sleepAllowed, sleepNeeded, allPlayersAsleep, isOnlyPlayerAsleep, processWakingUp, minutesPerDay
```

## 4. The bed quality and the zombie counts

**`getBedQuality(playerObj, bed)` with `bed` nil** (`ISWorldObjectContextMenu.lua` L2915–L2950): in a vehicle it returns `badBed`, or `badBedPillow` with a pillow in either hand or in the seat's container (L2923–L2935), whatever `bed` is; otherwise with `bed` nil it returns `floorPillow` when either hand item or any world item on the player's own square has the `PILLOW` tag, and `floor` otherwise (L2936–L2950).
The handler then multiplies the hours by 0.7 for `floor` or a `floorPillow` type (L1065–L1067), and `SleepingEvent.wakeUp(IsoGameCharacter,boolean) @388–@465 L542–L547` adds FATIGUE 0.15 to 0.25 times the event's sleeping time over 8 on `floor`, with a one-in-five neck injury of 10 to 20 damage and 30 to 50 pain (`floorPillow` @468–@546 L549–L554: the same FATIGUE, one in ten, 5 to 10 and 15 to 25).
In multiplayer the sleeping-event data is never set up by the vanilla handler (§ 3), so what that sleeping time reads there is not read.

**The counts.** `Stats.getNumVisibleZombies() @0–@4 L137` returns `numVisibleZombies`, `getNumChasingZombies() @0–@4 L141` returns `lastNumChasingZombies` and `getNumVeryCloseZombies() @0–@4 L149` returns `lastVeryCloseZombies`.
`IsoPlayer.updateLOS` writes all three, and `IsoPlayer.updateInternal1 @50–@67 L2208–L2212` calls it only when `updateInternal2()` returned true and the player's `remote` is false:

```
     51         invokevirtual    zombie/characters/IsoPlayer.updateInternal2
     54         istore_1
     55  L2210  iload_1
     56         ifeq             74
     60  L2211  getfield         zombie/characters/IsoPlayer.remote
     63         ifne             70
     67  L2212  invokevirtual    zombie/characters/IsoPlayer.updateLOS
```

`updateLOS` itself returns, after zeroing the counts, when the player's current square is null (`@82–@89 L6210–L6211`). It zeroes `numVisibleZombies`, copies `numChasingZombies` into `lastNumChasingZombies` through `setLastNumberChasingZombies` and zeroes `numChasingZombies` (`@7–@34 L6200–L6202`), then for each moving object of the cell seen by this player (`TestIfSeen` on the server, the client's `isVisibleToPlayer[playerIndex]` otherwise, `@600–@627 L6302–L6303`) that is a zombie:

```
    658  L6312  fload 13 (zombie z) >= fload 6 (player z) - 1
    668         fload 14 (distance) < 7.0
    679         IsoZombie.ghost == false;  687 isFakeDead == false
    693         the zombie's square's room == the player's square's room
    713  L6314  numVisibleZombies += 1
    726  L6316  fload 14 < 3.0
    735  L6317  iinc 8 1                   (the very-close local)
```

A seen zombie on the player's own floor and not in `lastSpotted` adds 2 more within 4 tiles (7 when more than four are already counted) (`@935–@1065 L6351–L6366`), and the very-close local is stored to `lastVeryCloseZombies` at the end (`@1428–@1434 L6415`).
`numChasingZombies` is incremented by each zombie whose `target` is that player, in `IsoZombie.postUpdateInternal @0–@27 L3012–L3013`, so `getNumChasingZombies` is the previous pass's count of zombies targeting the player.
So the visible count is seen zombies within 7 tiles in the player's room (or both outside, rooms null) no lower than one floor below the player's (with no upper floor bound), excluding ghost and fake-dead zombies, plus the newly-spotted bonus, the very-close count seen zombies within 3 tiles at any floor and room, and the chasing count zombies targeting the player whether seen or not.
Not read: whether the server's copy of a connected player has `remote` false (which decides whether the server's counts are live), and whether a client runs `postUpdateInternal` for the zombies it does not own.

**Finding:** with `bed` nil and no vehicle `getBedQuality` returns `floor`, or `floorPillow` with a pillow in hand or on the player's square, which shortens the sleep to 0.7 and costs fatigue and a chance of a neck injury at the wake; `getNumVisibleZombies` counts seen zombies within 7 tiles in the player's room and floor band, ghost and fake-dead ones excluded, `getNumVeryCloseZombies` seen zombies within 3 tiles, and `getNumChasingZombies` the zombies targeting the player on the last pass, all written in `IsoPlayer.updateLOS`, which runs only for a non-remote player whose `updateInternal2` returned true and whose current square is not null.

Read with:

```
./pz.sh methods zombie.characters.Stats
./pz.sh dump zombie.characters.Stats getNumVisibleZombies
./pz.sh dump zombie.characters.Stats getNumChasingZombies
./pz.sh dump zombie.characters.Stats getNumVeryCloseZombies
./pz.sh dump zombie.characters.Stats setNumVisibleZombies
./pz.sh grep numVisibleZombies
./pz.sh grep lastNumChasingZombies
./pz.sh grep lastVeryCloseZombies
./pz.sh grep numChasingZombies
./pz.sh grep setLastNumberChasingZombies
./pz.sh dump zombie.characters.IsoPlayer updateLOS
./pz.sh dump zombie.characters.IsoPlayer updateInternal1 --from 0 --to 75
./pz.sh dump zombie.characters.IsoZombie postUpdateInternal --from 0 --to 40
./pz.sh dump zombie.ai.sadisticAIDirector.SleepingEvent wakeUp
# the vanilla Lua, read-only: D:\SteamLibrary\steamapps\common\ProjectZomboid\media\lua\client\ISUI\ISWorldObjectContextMenu.lua L1034–L1110, L2915–L2950
```
