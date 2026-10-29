# Plan 24 jar reads: the hoppable edge, the one-step death and the swing that never starts

Read on build 42.21 (buildid 25485521, jar `4a0e9546ec`) · 2026-10-29 · Plan 24 Task 6 · scope: three questions the live sessions raised that only the jar answers: how the pathfinder and the path follower treat a hoppable fence that `isBlockedTo` reads blocked (§ 1), what takes a character's health from 73 to 0 in one frame step under a group (§ 2), and what stops a `DoAttack` from starting a swing (§ 3).
Every cite is `Class.method @off L<n>` off a `pz.sh dump` of this jar; nothing here was run live.
Three readings needed a scratch parser rebuilt from the toolchain's own `cp.py` and `dis.py`, as [jar research](../../platform/jar-research.md#method) prescribes for what the shipped subcommands do not print: the target of each `invokedynamic` (the `BootstrapMethods` attribute), a per-class caller scan narrowing each jar-wide grep, and a string-literal scan of a class's methods.
The scratch scripts were session-scoped and are not kept; each reading they made is quoted below with the bytecode it resolved.
The vanilla data and Lua are cited as `lua:<path under media>:<line>` off the read-only install.

## 1. The hoppable edge

**A hoppable sprite carries the collide flag.** The tile loader turns a sprite's `HoppableN` property into three flags at once (`IsoWorld.LoadTileDefinitions @1939–@1980 L860–L863`), and `HoppableW` into the west three (`@1983–@2024 L865–L868`):

```
   1939   L860  aload            42
   1941         ldc_w            'HoppableN'
   1944         invokevirtual    java/lang/String.equals
   1947         ifeq             1983
   1950   L861  aload            39
   1955         getstatic        zombie/iso/SpriteDetails/IsoFlagType.collideN
   1958         invokevirtual    zombie/core/properties/PropertyContainer.set
   1961   L862  aload            39
   1966         getstatic        zombie/iso/SpriteDetails/IsoFlagType.canPathN
   1969         invokevirtual    zombie/core/properties/PropertyContainer.set
   1972   L863  aload            39
   1977         getstatic        zombie/iso/SpriteDetails/IsoFlagType.transparentN
   1980         invokevirtual    zombie/core/properties/PropertyContainer.set
```

So a picket fence such as `fencing_01_5`, whose definition lists `HoppableN` and no `collideN` (`lua:newtiledefinitions.tiles.txt:35148 "HoppableN = "`), loads with `collideN`, `canPathN` and `transparentN` set.

**The square merges it.** `IsoGridSquare.RecalcProperties` clears the square's `properties` (`@63–@67 L7361`) and adds every object's properties to them (`@226–@232 L7397`, `PropertyContainer.AddProperties`), so `IsoGridSquare.hasProperty(IsoFlagType) @0–@8 L990` and `has(IsoFlagType) @0–@8 L2482` read the fence's `collideN`, `canPathN` and `HoppableN` on the square.
One exception: an object on the square carrying `collideN` without `HoppableN` (a solid wall on the same edge) sets a local (`@315–@343 L7413–L7414`), and the square then has `canPathN` and `HoppableN` unset (`@705–@740 L7476–L7478`; the west pair at `@345–@373 L7416–L7417` and `@743–@778 L7480–L7482`):

```
   7413  315    iload            5   / ifne 345
          320    aload 14 / getstatic IsoFlagType.collideN / PropertyContainer.has / ifeq 345
          331    aload 14 / getstatic IsoFlagType.HoppableN / PropertyContainer.has / ifne 345
   7414  342    iconst_1 / istore 5
   ...
   7476  705    iload 5 / ifeq 743
          710    properties.has(HoppableN) / ifeq 743
   7477  723    properties.unset(canPathN)
   7478  733    properties.unset(HoppableN)
```

**`isBlockedTo` reads it blocked.** `isBlockedTo` is the or of `isWallTo`, `isWindowBlockedTo`, `isDoorBlockedTo` and `isStairBlockedTo` (`isBlockedTo(IsoGridSquare,GetSquare) @0–@40 L1120`, #4222), and the wall predicate is the square's `collideN` (`collideW`) flag on an edge with no window (`isWall(GridSquareEdgeFacingDirection) @0–@82 L1002–L1005`). No test in that chain names `HoppableN`, so a hoppable fence's edge reads blocked to `isBlockedTo` and present to `isSomethingTo`; vanilla's own Lua reads it the same way, testing `square:isWallTo(gs) and not square:isHoppableTo(gs)` to tell a wall from a fence (`lua:lua/client/ISUI/ISButtonPrompt.lua:1080 "if gs ~= square and square:isWallTo(gs) and not square:isHoppableTo(gs) then"`).

**The pathfinder crosses it.** The pathfinder is fed the square's flags as bits (`pathfind/nativeCode/SquareUpdateTask.getBits(IsoGridSquare) @0–@970 L86–L257`): `collideN` is bit 4 (`@58–@73 L99–L100`), `HoppableN` bit 16777216 (`@170–@186 L120–L121`), `canPathN` bit 16384 (`@416–@431 L146–L147`), and the west three 2, 33554432 and 8192 (`@42–@57 L96–L97`, `@245–@261 L125–L126`, `@400–@415 L143–L144`).
The Java graph links the two squares across a can-path edge: `PolygonalMap2.addCanPathNodes @220–@342 L423–L434` takes each square whose `Square.isCanPathN()` holds (bit 16384, `Square.isCanPathN @0–@11 L71–L72`), creates a node on it and on its north neighbour and calls `connectTwoNodes` (the west edge the same way at `@94–@216 L409–L420`).
The mover's fence switch is an animal's alone: `PMMover.set(PathFindRequest) @0–@75 L25–L33` zeroes `canClimbFences`, copies it from `IsoAnimal.canClimbFences()` for an animal (`@42–@47 L30`) and sets `canClimbTallFences` true for a player (`@70–@72 L33`), and the cost function reads `canClimbFences` only behind `isAnimal()` (`SearchNode.c @86–@117 L85`).

**The path follower climbs it at any pace.** A walk is the vanilla timed action, which drives `PathFindBehavior2` (`lua:lua/client/TimedActions/WalkToTimedAction.lua:42 "self.character:getPathFindBehavior2():pathToLocation(self.location:getX(), self.location:getY(), self.location:getZ());"`, and `:18` its `update()`).
`PathFindBehavior2.update(F) @1604–@1666 L984–L985` calls `checkDoorHoppableWindow` on the point half a step ahead, and that method (`@553–@698 L1211–L1230`) picks a climb direction off the square flags: moving east, the square ahead's `HoppableW`; moving west, the current square's `HoppableW`; moving north, the current square's `HoppableN`; moving south, the square ahead's `HoppableN`; then, unless the character is aiming (`@654–@665 L1222–L1223`), it faces that way and calls `IsoGameCharacter.climbOverFence(dir)`:

```
    604  L1216  iload 7 / ifge 628
    609         aload 4 / getstatic IsoFlagType.HoppableN / IsoGridSquare.has / ifeq 628
    620  L1217  getstatic IsoDirections.N / astore 12
    ...
    692  L1230  aload_0 / getfield chr / aload 12 / invokevirtual IsoGameCharacter.climbOverFence
```

`climbOverFence @0–@92 L8565–L8581` checks only a current square, `IsoWindow.canClimbThroughHelper` and `IsoGridSquare.isPlayerAbleToHopWallTo`, then sets `ClimbOverFenceState`'s parameters and reports `EventClimbFence`; nothing on the path reads running.
The pace gate is on the free-movement vault alone: `IsoMovingObject.checkVaultOver @24–@46 L1985–L1986` returns false unless the player `IsRunning`, `isSprinting` or is remote with an obstacle on its path, and it is called from the wall-collision check (`checkHitWall @252 L1970`).
A tall fence is a different edge: `TallHoppableN`/`WallN` with `SquareUpdateTask.canClimbOverWall` both ways sets bit 1073741824 (`getBits @189–@244 L122–L123`), and the follower calls `IsoPlayer.climbOverWall` for it (`checkDoorHoppableWindow @701–@915 L1233–L1244`).

**What the Lua can read.** `IsoGridSquare.has(IsoFlagType)` is public and reads the merged flag (`@0–@8 L2482`), and vanilla calls it from Lua (`lua:lua/client/TimedActions/ISClimbOverFence.lua:48 "local north = square:has(IsoFlagType.HoppableN)"`). `isHoppableTo(IsoGridSquare) @0–@8 L1223` is the neighbour form: not diagonal, and an edge element passing `isHoppable(GridSquareEdge,GetSquare)` (the bootstrap target at `isHoppableTo(IsoGridSquare,GetSquare) @14 L1228`), which is `getHoppableOrWindowFrame(GridSquareEdge,GetSquare)` non-null (`isHoppable @0–@14 L1211`); that resolves the edge to a square and a facing (`@2 L1203`, bootstrap target `getHoppableOrWindowFrame(GridSquareEdgeFacingDirection)`) and searches its objects with the predicate `IsoObject.isHoppableOrWindowFrame` (the bootstrap target at `@3 L1195`), so it tests each object's `IsoObject.isHoppableOrWindowFrame @0–@21 L6998` (an object `HoppableN`/`HoppableW` facing the edge, `getHoppableDirection @0–@29 L3552–L3558`, or a window frame) rather than the square's merged flag.

Not read: the native pathfinder's own edge rules, which run behind `PathfindNative` in native code (only the bits it is fed are in the jar), and which of the native and the Java `PolygonalMap2` graphs a 42.21 dedicated server and client run; whether a player-built `IsoThumpable` fence reaches the square's flags (`IsoThumpable.isHoppable @30 L1697` overrides the object test); the climb's own duration and its failure (`ClimbOverFenceState`, the trip roll).

**Finding:** a hoppable fence's sprite loads with `collideN` (`collideW`), `canPathN` (`canPathW`) and `HoppableN` (`HoppableW`) set, so `isBlockedTo` reads its edge blocked, while the pathfinder links the squares across the can-path edge and the path follower climbs any edge whose square carries `HoppableN`/`HoppableW` through `climbOverFence` at a walk; only a free-movement collision needs a run or a sprint to vault [#4288/C/n=1] [#4289/C/n=1].

**Proposed change (PZA/1.4, controller's and Task 2's to rule):** add `hopN` and `hopW` to the square record as `sq:has(IsoFlagType.HoppableN)` and `sq:has(IsoFlagType.HoppableW)` (the square's own north and west edges, the same edges `blockN`/`blockW` read, and the flags the follower climbs on; an edge beside a solid wall reads false, as the follower sees it); then `World.blocked` reads an edge with `block` and `hop` both true as crossable by a climb (the flood and the planner's routes may cross it at a climb's cost), and `line_clear` and the steer probe keep it blocked, since a steered walk is free movement and vaults only at a run.

## 2. The one-step death

**The drag-down.** Every zombie attack that reaches the player runs `BodyDamage.AddRandomDamageFromZombie(IsoZombie,String,int)`, which counts the group first (`@236–@255 L1360`) and, at or above a strength-set threshold, takes the defence away and marks the death (`@257–@342 L1362–L1368`) [#4290/C/n=1]:

```
    148  L1342  iconst_3 / istore 12                         (threshold 3)
    151  L1344  lore.strength == 1 -> L1345 iconst_2 / istore 12
    170  L1348  lore.strength == 3 -> L1349 bipush 6 / istore 12
    236  L1360  parentChar.getSurroundingAttackingZombies(lore.zombiesCrawlersDragDown) / istore 13
    257  L1362  'EndDeath'.equals(getHitReaction()) -> skip
    273  L1363  !isGodMod && istore13 >= istore12 && lore.zombiesDragDown && !isSitOnGround
    315  L1364  iconst_0 / istore 6      (the three defence chances to 0, L1364-L1366)
    324  L1367  setHitReaction('EndDeath')
    334  L1368  setDeathDragDown(true)
    345  L1370  else setHitReaction(<the attack's reaction>)
```

The sandbox defaults are `ZombiesDragDown` true and `ZombiesCrawlersDragDown` false (`SandboxOptions$ZombieLore.<init> @365–@371 L320`, `@379–@385 L321`); `Strength` 1 lowers the threshold to 2 and 3 raises it to 6, every other value keeping 3.
**The count.** `IsoGameCharacter.getSurroundingAttackingZombies(Z) @0–@336 L14578–L14629` reads the moving objects on the character's square and its eight neighbours and counts each `IsoZombie` whose `target` is the character (`@239–@248 L14613`), at a squared distance under 0.81 (`@251–@264 L14617–L14618`, `ldc_w 0.809999942779541`), not crawling unless the argument says so (`@267–@279 L14621–L14622`), and in `AttackState`, `AttackNetworkState`, `LungeState` or `LungeNetworkState` (`@282–@326 L14625–L14626`): three standing zombies attacking from within 0.9 tiles.

**The kill.** `IsoGameCharacter.Kill(IsoGameCharacter,HandWeapon,boolean,CharacterDiedListener) @0–@31 L15847–L15852` sets the health and the body's overall health to 0 in one call, with no wound in between [#4291/C/n=1]:

```
     12 L15849  aload_0 / fconst_0 / invokevirtual IsoGameCharacter.setHealth
     17 L15850  getBodyDamage / astore 5
     28 L15852  aload 5 / fconst_0 / invokevirtual BodyDamage.setOverallBodyHealth
```

and `BodyDamage.getHealth() @0–@4 L1726` is `getOverallBodyHealth()`, the frames' `body.health`. Three paths reach `Kill` from the drag-down:
- **The server's hit.** On a client, `AddRandomDamageFromZombie` decides the hit and returns at `GameClient.sendZombieHit` without applying the wound (`@1276–@1292 L1556–L1558` for a scratch, `@1807–@1823 L1631–L1633` for a bite), after the drag-down branch has run. The server's `ZombieHitPlayerPacket.preProcess @0–@11 L67–L68` copies the client's drag-down flag onto its player (`fields/hit/Player.process @188–@207 L138`, the flag written at `Player.set @124–@130 L65`), and `process @0–@21 L73` runs `fields/hit/Bite.process`, which on the server re-runs `AddRandomDamageFromZombie` and then kills (`@137–@176 L84–L88`):
```
    137    L84  getstatic GameServer.server / ifeq 179
    163    L85  BodyDamage.AddRandomDamageFromZombie
    167    L87  aload_2 / invokevirtual IsoGameCharacter.isDeathDragDown / ifeq 179
    174    L88  aload_2 / aload_1 / invokevirtual IsoGameCharacter.Kill
```
- **The client's animation.** The `EndDeath` hit reaction plays `Bob_EndDeath`, whose `Death` event fires at the clip's end (`lua:AnimSets/player/hitreaction-endDeath/EndDeath.xml:9 "<m_EventName>Death</m_EventName>"`), and `PlayerHitReactionState.animEvent @202–@231 L78–L81` puts the character on the floor and, off the server, calls `Kill(getAttackedBy())`.
- **The fallback.** `IsoPlayer.updateDeathDragDown @0–@238 L3617–L3657`, called every update (`updateInternal2 @216 L2279`), re-sets `EndDeath` while a live standing zombie stands on the 3 × 3 squares around a drag-down flagged player, and otherwise clears the flag and calls `Kill(null)` on a client (`@197–@235 L3650–L3655`).

`OnPlayerGetDamage` fires from `BodyDamage.Update`, `IsoGameCharacter.Hit`, `FireCheck`, `ReduceHealthWhenBurning`, the landing impact and the vehicle hit (a string-literal scan of `BodyDamage`, `IsoGameCharacter` and `IsoPlayer`), and `Kill` calls none of them, so the death writes no `damage.watch` record.

**Finding:** a group of at least three standing zombies (the default `Strength`) targeting the character and attacking from within 0.9 tiles turns the next zombie hit into the drag-down, which zeroes its defence, sets the `EndDeath` reaction and the drag-down flag, and ends in `Kill`, which sets health and overall body health to 0 in one call: on the server when the hit packet is processed, and on the client at the end of the `EndDeath` clip. This explains a 73 → 0 fall in one frame step with a bleeding sum under 1 [#4290/C/n=1] [#4291/C/n=1]; E3's five zombies within 0.36 to 0.77 tiles would meet its count if they were targeting and attacking, which the frames do not read.

**What could show it.** A server read: no PZTestKit command reads `isDeathDragDown()`, `getHitReaction()` or `getSurroundingAttackingZombies()` (`damage.watch` hooks `OnPlayerGetDamage`, which the kill bypasses; `lua.read` and `lua.call` reach plain Lua only), so the read needs a new `TK.register` command (a `player.combat <user>` reply `{hitReaction, dragDown, attackers, dead, health}`) landed before its run under § 5. A client read, before the pull-down: `getSurroundingAttackingZombies()` is public on `IsoGameCharacter` (access 0x0001), as are `getHitReaction()`, `hasHitReaction()` and `isDeathDragDown()`; the frames can carry `attackers` (the count at the drag-down's own rule) and `hitReaction`, and the planner's group rule can flee at two attackers, one under the threshold, rather than on health.

Not read: a bite's or a scratch's own damage (`AddRandomDamageFromZombie`'s `AddDamage` amounts past `@1293 L1562`); which of the server's kill and the client's clip lands first, and what the client's frames read between (the client's `Kill` is local, and how the server's death reaches the client is not read); whether the zombie's attack runs on the server or the zombie's owning client in 42.21 (`ZombieHitPlayerPacket.isConsistent @0–@68 L59–L62` reads the zombie's owner); E5's death, which no reading here places inside a group.

## 3. The swing that never starts

**The guard.** `IsoPlayer.DoAttack(F,String) @0–@19 L6187–L6193` returns false unless `isAuthorizedHandToHandAction` (true from construction, `IsoPlayer.<init> @267–@269 L418`), then calls `pressedAttack()`, which is `CombatManager.pressedAttack(IsoPlayer)` (`IsoPlayer.pressedAttack @0–@7 L4085`); that method returns before starting anything while an attack is already started or the player is in the hit-reaction state (`CombatManager.pressedAttack @34–@51 L3178–L3179`):

```
     34  L3178  aload_1 / invokevirtual IsoPlayer.isAttackStarted / ifne 51
     41         aload_1 / invokestatic PlayerHitReactionState.instance / invokevirtual IsoPlayer.isCurrentState / ifeq 52
     51  L3179  return
```

The later returns: `FishingState` (`@52–@62 L3182–L3183`), on a client the PvP hit reaction unless the server option behind `ServerOptions.pvpMeleeWhileHitReaction` (`@63–@91 L3186–L3187`), `canPerformHandToHandCombat()` false (`@92–@103 L3190–L3192`), and a weapon not ready for a non-shove (`@104–@118 L3195–L3196`, `IsoGameCharacter.isWeaponReady @0–@26 L17729`); past them it sets `setInitiateAttack(true)` and `setAttackStarted(true)` (`@135–@142 L3203–L3204`).
`getMeleeDelay` is not on this path: it gates the keyboard and mouse attack in `IsoPlayer.updateInternal2` (`@2334–@2339 L2706`, `@2439–@2444 L2721`), which `DoAttack` does not pass through.

**How a hit puts the player there.** Every zombie attack that reaches `AddRandomDamageFromZombie` sets the player's hit reaction before the defence roll is made (`@345–@350 L1370`, the zombie's `PlayerHitReaction` string, `Bite` when empty, `@0–@10 L1320–L1321`), and nothing later in the method clears it (its only `setHitReaction` calls are at L1367 and L1370), so a defended attack sets it too.
The animation variable `hashitreaction` is bound to `IsoGameCharacter.hasHitReaction()` (the bootstrap target at `registerVariableCallbacks @48 L815`), which is `getHitReaction()` non-empty (`hasHitReaction @0–@15 L13191`), and the melee and idle action states transition to `hitreaction` on it (`lua:actiongroups/player/melee/to_hitreaction.xml:5 "<isTrue>hashitreaction</isTrue>"`). `PlayerHitReactionState.enter @0–@34 L30–L34` force-stops the current timed action and clears aiming, and `exit @0–@11 L39–L40` clears the hit reaction to `''`.

**Finding:** a `DoAttack` starts no swing while `isAttackStarted()` already reads true or the player is in `PlayerHitReactionState` [#4292/C/n=1], which any zombie attack reaching the player's damage roll sets up, a defended one included, until the reaction's state exits [#4293/C/n=1]; a swing already running is left when the melee state transitions to `hitreaction` (the transition file's reading, not a jar line).

**What the Lua could read.** `getHitReaction()` and `hasHitReaction()` are public on `IsoGameCharacter`, and `PlayerHitReactionState` is exposed (`LuaManager$Exposer.exposeAll @415`), so `p:isCurrentState(PlayerHitReactionState.instance())` is the guard's own test. Proposed: the frames carry `hitReaction` (the string, `''` when none); the `attack` skill refuses with a `busy` reason while `hasHitReaction()` or `isAttackStarted()` reads true, and the planner re-sends the attack on the first frame after the reaction clears rather than counting the refused one as a swing.

Not read: the hit-reaction clip lengths (how long a bite or a defended attack holds the state); whether a started swing's `attackStarted` is cleared when the melee state is left for `hitreaction`; the unit of `getMeleeDelay`.

Read with:

```
cd /c/Users/Angus/pz-b42
./pz.sh methods zombie/iso/IsoGridSquare
./pz.sh dump zombie/iso/IsoWorld LoadTileDefinitions --from 1930 --to 2030
./pz.sh dump zombie/iso/IsoGridSquare RecalcProperties
./pz.sh dump zombie/iso/IsoGridSquare isHoppableTo      # and isHoppable, getHoppableOrWindowFrame, has, hasProperty
./pz.sh dump zombie/iso/IsoObject isHoppableOrWindowFrame   # and getHoppableDirection
./pz.sh dump zombie/pathfind/nativeCode/SquareUpdateTask getBits
./pz.sh dump zombie/pathfind/PolygonalMap2 addCanPathNodes
./pz.sh dump zombie/pathfind/Square isCanPathN
./pz.sh dump zombie/pathfind/PMMover set
./pz.sh dump zombie/pathfind/SearchNode c
./pz.sh dump zombie/pathfind/PathFindBehavior2 checkDoorHoppableWindow   # and update --from 1580 --to 1700
./pz.sh dump zombie/characters/IsoGameCharacter climbOverFence
./pz.sh dump zombie/iso/IsoMovingObject checkVaultOver
./pz.sh dump zombie/characters/BodyDamage/BodyDamage AddRandomDamageFromZombie
./pz.sh dump zombie/characters/IsoGameCharacter getSurroundingAttackingZombies
./pz.sh dump zombie/characters/IsoGameCharacter Kill
./pz.sh dump zombie/characters/BodyDamage/BodyDamage getHealth
./pz.sh dump zombie/characters/IsoPlayer updateDeathDragDown
./pz.sh dump zombie/network/fields/hit/Bite process
./pz.sh dump zombie/network/packets/hit/ZombieHitPlayerPacket preProcess   # and process, parse
./pz.sh dump zombie/network/fields/hit/Player process
./pz.sh dump zombie/ai/states/PlayerHitReactionState animEvent   # and enter, exit
./pz.sh dump 'zombie/SandboxOptions$ZombieLore' '<init>'
./pz.sh dump zombie/characters/IsoPlayer DoAttack
./pz.sh dump zombie/CombatManager pressedAttack
./pz.sh dump zombie/characters/IsoGameCharacter hasHitReaction   # and getHitReaction, isWeaponReady, registerVariableCallbacks
./pz.sh refs 'zombie/Lua/LuaManager$Exposer' exposeAll
# plus the scratch invokedynamic, caller and string-literal scans named above
```
