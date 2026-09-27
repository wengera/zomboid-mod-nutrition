# Jar reading — the perk API, Strength and Fitness

Build `42.20.4` · jar `b0bbce05d5` · read 2026-09-27 · scope: what a Lua mod can and cannot do to a
character's Strength and Fitness perk on this build. Every fact below is a static bytecode read of
`projectzomboid.jar` through `pz.sh grep|methods|refs|dump` plus a session-scoped constant-pool
access-flag parser and a session-scoped jar-wide reverse-reference scanner, both rebuilt over
`pz-b42/tools/{cp,dis}.py` as [jar-research.md](../../platform/jar-research.md) requires. Nothing here was
measured on a live session; every row is a C-grade code reading.

Two files of the read-only install's shipped Lua were read as files (not disassembled) because the
mechanism turned out to live there: `media/lua/server/XpSystem/XpUpdate.lua` and
`media/lua/shared/TimedActions/ISFitnessAction.lua`.

## Summary for the design

Perk level and perk XP are two separate stores on the character and both are reachable from Lua: the
level lives in `IsoGameCharacter.perkList` as `PerkInfo.level` and is read with `getPerkLevel(perk)`, the
XP lives in `IsoGameCharacter$XP.xpMap` and is read with `getXp():getXP(perk)`.

There is no writable "effective strength": every one of the twenty-odd Java consumers calls
`getPerkLevel(Perks.Strength)` live inside its own body, so the only way to move melee damage, shove
power, climb odds, defence score, stomp damage, door damage, window-opening odds, recoil or muscle
strain is to move the perk level itself — there is no damage, knockback or combat-speed setter on
`IsoGameCharacter` for a mod to write instead.

Carry capacity is the one exception and it is a clean one: `BodyDamage.UpdateStrength` computes
`maxWeight = (int)(getMaxWeightBase() × getWeightMod()) − moodlePenalty`, clamps it at zero, and then
multiplies by `IsoPlayer.getMaxWeightDelta()`, and both `setMaxWeightBase(int)` and
`setMaxWeightDelta(float)` are public, have **no Java caller anywhere in the jar**, and are re-applied
on every recompute — so a mod can own carry capacity outright without touching the perk.

Fitness's whole effect surface is likewise `getPerkLevel(Perks.Fitness)` read live, in three
multiplier ladders (`getFatigueMod` for endurance cost, `getPacingMod` for endurance drain,
`getRecoveryMod` for endurance and muscle recovery) plus combat speed, the animation speed variable,
climb, vault, window and fall terms — and `getRecoveryMod` already reads lipids and proteins, so the
nutrition hook into Fitness's most valuable consumer exists in vanilla.

In multiplayer the **server owns both level and XP**: `NetworkPlayerManager.update` runs server-only and
every 1000 ms calls `NetworkPlayerAI.syncXp`, which sends a `PlayerXp` packet carrying the whole XP
object — character traits, total XP, the per-perk XP map **and the per-perk level list** — to that
player's own connection, where `PlayerXpPacket.parse` loads it straight over the client's copy.

A client-side XP or level write therefore survives less than a second unless the mod also calls the
Lua global `SyncXp(player)`, which is client-gated, ships the client's whole XP object to the server,
and is relayed onward to the other clients — that is the only client→server perk write path, and it
is exactly what the vanilla debug stats UI uses.

The other perk packet, `SyncPerks`, is a red herring for a mod: `GameClient.sendPerks` carries only the
Sneak, Strength and Fitness **levels** and both receivers write them into the cosmetic
`remoteSneakLvl`/`remoteStrLvl`/`remoteFitLvl` fields rather than into the perk list — `remoteFitLvl` has
no reader in the jar at all, and `remoteStrLvl`'s only reader is `IsoPlayer.calculateCritChance`.

The XP write itself has a side trap: `XP.AddXP(perk, float)` and its three- and four-argument siblings
all return immediately unless the character `isLocalPlayer()`, and `IsoPlayer.isLocalPlayer()` returns
false unconditionally when `GameServer.server` is set — so those three overloads are silent no-ops for
every player on a dedicated server, and only the five- and six-argument overloads reach the body.

The safe route from Lua is the exposed global `addXp(player, perk, amount)`, which branches to
`GameServer.addXp` on a server (capability-checked, then the six-argument `AddXP`, then
`updateXpChecker`) and does nothing at all on a multiplayer client.

Both Strength and Fitness XP are already nutrition-gated inside `XP.AddXP`: Fitness XP is dropped
entirely when `Nutrition.canAddFitnessXp()` is false, and Strength XP is multiplied by 1.5 while
proteins sit strictly between 50 and 300 and by 0.7 while proteins are below −300.

XP is hard-capped: any non-negative gain is discarded once the perk's XP has reached
`Perk.getTotalXpForLevel(10)`, and the level itself is clamped to 10 inside `LevelPerk`; for Strength and
Fitness the per-level thresholds declared in `PerkFactory.init` are 1000/2000/4000/6000/12000/20000/
40000/60000/80000/100000, each multiplied by 1.5 inside `AddPerk`, so level 10 costs 487,500 XP.

Levels move only through `LevelPerk`, `LoseLevel`, `setPerkLevelDebug` and `level0`; the first two are
driven by `XP.AddXP` crossing a threshold in either direction, and the last two have **no Java caller at
all** — they exist for Lua and the debug UI, which is what makes `setPerkLevelDebug(perk, n)` the direct
level setter a mod wants.

Two Lua events carry the change: `AddXP(chr, perk, amount)` fires from `XP.AddXP` but only when
`GameClient.client` is null, so never on a multiplayer client; `LevelPerk(chr, perk, level, gained)`
fires from both `LevelPerk` (gained = true) and `LoseLevel` (gained = false) with no side gate.

Everything a designer would call "skill rust" is in shipped **Lua**, not Java: `XpUpdate.lua`'s
`everyTenMinutes` walks the online players, advances `strengthUpTimer`/`fitnessUpTimer` in player modData
by `getLoosingXpTick()` (10 per tick normally), and once a timer passes 20000 calls `addXp(player, perk,
getLoosingXpValue())` — that is −1 XP per 1200 timer units — then `LoseLevel` through
`xpUpdate.checkForLosingLevel`; a jar-wide grep finds no `SkillRust`, `XPDecay` or `LoseXP` identifier
anywhere.

The same Lua file is where Strength level is turned into the WEAK/FEEBLE/STOUT/STRONG traits and
Fitness level into UNFIT/OUT_OF_SHAPE/FIT/ATHLETIC, on the `LevelPerk` event — which means a mod can
replace that mapping without touching Java, and also means the trait→`maxWeightDelta` mapping in
`IsoPlayer.<init>` is a character-creation snapshot that levelling never refreshes.

Exercise XP is real and server-side: `ISFitnessAction:exeLooped` calls `Fitness.exerciseRepeat`, which
refreshes its cached Strength and Fitness levels, bumps regularity, drains endurance, queues future
stiffness, then `incStats` awards `arms 4 + chest 2` scaled XP to Strength and `legs 4 + abs 2` scaled
XP to Fitness through `GameServer.addXp` on a server and through `XP.AddXP` in single-player, and
awards nothing at all on a multiplayer client.

"Muscle strain" is `BodyPart.stiffness`, a float per body part with public `getStiffness`,
`setStiffness` and `addStiffness`, fed by `IsoGameCharacter.addCombatMuscleStrain` and the six
`addXxxMuscleStrain(float)` helpers, all public, and Strength reduces it by the factor
`(15 − StrengthLevel) / 10`.

One hazard worth designing around: `AntiCheatXPUpdate` runs on the server and flags a player whose
per-perk XP grew by more than `1000 × maxMultiplier × maxBoostMultiplier` between checks, and a flagged
anticheat calls `AntiCheat.act(connection, "update failed")` — so a mod that grants a large Strength or
Fitness lump server-side can trip it.

## A — the perk API reachable from Lua

Exposure: every class below is in the `LuaManager$Exposer.exposeAll()` constant-pool class set, read end
to end (`zombie/characters/IsoGameCharacter` at `@716 L…`, `IsoGameCharacter$XP` at `@800`,
`IsoGameCharacter$PerkInfo` at `@793`, `IsoPlayer` at `@814`, `PerkFactory` at `@637`, `PerkFactory$Perk`
at `@643`, `PerkFactory$Perks` at `@649`, `BodyDamage/Fitness` at `@601`, `BodyDamage/Nutrition` at
`@5413`, `BodyDamage/BodyPart` at `@571`). Kahlua publishes methods and never fields, so every public
**field** in the tables below is unreachable regardless.

`zombie/characters/ILuaGameCharacter` is an interface `IsoGameCharacter` implements and is **not** in the
exposer set; it looks like a curated Lua-API list and is quoted below only as a secondary signal. A
public method of the exposed class that is absent from that interface (`setMaxWeight`,
`setMaxWeightBase`, `level0`, `getWeightMod`, `getHittingMod`, `applyTraits`) is still reachable under
the library's exposure rule, but is a live-probe item rather than a settled one.

### Reading a perk

| Member | Signature | Flags | Exposed? | Side | Cite |
|---|---|---|---|---|---|
| `IsoGameCharacter.getPerkLevel` | `(Perk)I` | public | yes; in `ILuaGameCharacter` | either | `IsoGameCharacter.getPerkLevel @11 L4788` — returns `getPerkInfo(perk).level`, 0 when the info is absent |
| `IsoGameCharacter.getPerkInfo` | `(Perk)PerkInfo` | public; in `ILuaGameCharacter` | yes | either | `IsoGameCharacter.getPerkInfo @21 L10513` — linear scan of `perkList` |
| `IsoGameCharacter$PerkInfo.getLevel` | `()I` | public | yes | either | `IsoGameCharacter$PerkInfo.getLevel @1 L14072`; `level` is a public **field** with no setter, so Lua can read the level here and not write it |
| `IsoGameCharacter.getXp` | `()XP` | public; in `ILuaGameCharacter` | yes | either | `IsoGameCharacter.getPerkToUnit @23 L16106` (a call site; the getter is a one-line field read) |
| `IsoGameCharacter$XP.getXP` | `(Perk)F` | public | yes | either | `IsoGameCharacter$XP.getXP @5 L14359` — `xpMap.get(perk)`, 0 when absent. Two calls, never one, as [lua-platform](../../platform/lua-platform.md#java-members) already records |
| `IsoGameCharacter.getPerkList` | `()ArrayList` | public | yes | either | `IsoGameCharacter$XP.save @121 L14444` (the field it returns); walk it by size and index per the Kahlua rule |
| `IsoGameCharacter.getPerkToUnit` | `(Perk)F` | public; in `ILuaGameCharacter` | yes | either | `IsoGameCharacter.getPerkToUnit @53 L16112` — `0.1 × level + 0.1 × (xp − totalXpForLevel(level)) / xpForLevel(level+1)`, clamped `[0,1]`; returns 1.0 at level 10 (`@12 L16102`) |
| `IsoGameCharacter$XP.getTotalXp` | `()F` | public | yes | either | `IsoGameCharacter$XP.getTotalXp @1 L14140` — a global XP counter, not per perk |
| `IsoGameCharacter$XP.getLevel` | `()I` | public | yes | either | `IsoGameCharacter$XP.getLevel @1 L14132` — the *global* level against the 32-entry `LevelUpLevels` table (`IsoGameCharacter.<clinit> @30 L381`, first entries 25, 75, 150, 225, 300, 400), unrelated to perk levels |
| `PerkFactory$Perk.getXpForLevel` | `(I)F` | public | yes | either | `PerkFactory$Perk.getXpForLevel @6 L184` — a `xp1..xp10` ladder |
| `PerkFactory$Perk.getTotalXpForLevel` | `(I)F` | public | yes | either | `PerkFactory$Perk.getTotalXpForLevel @10 L219` — sums `getXpForLevel(1..n)`, skipping `-1` entries |
| `PerkFactory.getPerk` / `getPerkFromName` / `getPerkName` | statics | public static | yes | either | `PerkFactory.init @1282 L321` (the Strength registration these look up) |

### Writing XP

| Member | Signature | Flags | Exposed? | Side | Cite |
|---|---|---|---|---|---|
| `XP.AddXP` | `(Perk;F)V` | public | yes | **local player only** | `IsoGameCharacter$XP.AddXP @6–@24 L14144` — `instanceof IsoPlayer && isLocalPlayer()` or return; forwards as `AddXP(p, f, true, true, false, false)` |
| `XP.AddXP` | `(Perk;FZ)V` | public | yes | local player only | `IsoGameCharacter$XP.AddXP @19–@26 L14156` — same gate |
| `XP.AddXP` | `(Perk;FZZ)V` | public | yes | local player only | `IsoGameCharacter$XP.AddXP @19–@26 L14162` — same gate |
| `XP.AddXP` | `(Perk;FZZZ)V` | public | yes | **no gate** | `IsoGameCharacter$XP.AddXP @0–@9 L14179` — straight to the six-arg with a trailing `false` |
| `XP.AddXP` | `(Perk;FZZZZ)V` | public | yes | **no gate**; the real body | `IsoGameCharacter$XP.AddXP @0 L14183` through `@1367 L14339` |
| `XP.AddXPHaloText` | `(Perk;F)V` | public | yes | — | declared; body not dumped (see `## Not read`) |
| `XP.AddXPNoMultiplier` | `(Perk;F)V` | public | yes | local player only (it routes through the two-arg) | `IsoGameCharacter$XP.AddXPNoMultiplier @1–@15 L14168` — removes the perk's `XPMultiplier`, calls the **two-arg** `AddXP`, restores it in a finally |
| `XP.AddXP` | `(HandWeapon;I)V` | public | yes | — | `IsoGameCharacter$XP.AddXP @0 L14367` — **empty body, `return` only**; a dead overload |
| `XP.setTotalXP` | `(F)V` | public | yes | either | `IsoGameCharacter$XP.setTotalXP @2 L14370` — writes the global counter, no perk effect |
| `XP.setXPToLevel` | `(Perk;I)V` | public | yes | either | `IsoGameCharacter$XP.setXPToLevel @54–@70 L14472` — writes `xpMap[perk] = perk.getTotalXpForLevel(level)`; **does not change the perk level** and fires no event; its Fitness→`CharacterStat.FITNESS` sync at `@71–@105 L14473` is gated on `Core.debug` |
| `XP.addXpMultiplier` | `(Perk;FII)V` | public | yes | either | `IsoGameCharacter$XP.addXpMultiplier @27–@56 L14094` — stores `multiplier/minLevel/maxLevel` in `xpMapMultiplier` |
| `XP.getMultiplier` | `(Perk)F` | public | yes | either | `IsoGameCharacter$XP.getMultiplier @16 L14107` — **0.0 when no entry exists**, not 1.0 |
| `XP.getMultiplierMap` | `()HashMap` | public | yes | either | `IsoGameCharacter$XP.AddXP @877 L14284` (a call site) |
| `XP.getPerkBoost` / `setPerkBoost` | `(Perk)I` / `(Perk;I)V` | public | yes | either | `IsoGameCharacter$XP.getPerkBoost @10 L14113` reads `getDescriptor().getXPBoostMap()`; `setPerkBoost @19–@65 L14123` clamps `[0,10]` via `PZMath.clamp` and removes the entry at 0 |
| `XP.isSkillExcludedFromSpeedReduction` / `...Increase` | `(Perk)Z` | **private** | no | — | `IsoGameCharacter$XP.isSkillExcludedFromSpeedReduction @19 L14348`, `...Increase @10 L14355`; both name Fitness and Strength |
| `XP.save` / `XP.load` | `(ByteBuffer[,I])V` | public | yes | either | `IsoGameCharacter$XP.save @0 L14433`, `load @0 L14384` |
| global `addXp` | `(IsoPlayer;Perk;F)V` | public | Lua global | server: `GameServer.addXp`; **MP client: no-op** | `LuaManager$GlobalObject.addXp @8–@38 L9780` — `isExistInTheWorld()` first, then `GameServer.server` → `GameServer.addXp`, else `GameClient.client != null` → return |
| global `addXpNoMultiplier` | `(IsoPlayer;Perk;F)V` | public | Lua global | same shape | `LuaManager$GlobalObject.addXpNoMultiplier @14–@39 L9768` — server arm passes `true` for the no-multiplier flag |
| global `addXpMultiplier` | `(IsoPlayer;Perk;FII)V` | public | Lua global | same shape | `LuaManager$GlobalObject.addXpMultiplier @8–@43 L9793` |
| global `SyncXp` | `(IsoPlayer)V` | public | Lua global | **client only** | `LuaManager$GlobalObject.SyncXp @0–@17 L9830` — `GameClient.client` or nothing; sends `PacketType.PlayerXp` |
| global `getLoosingXpValue` | `()I` | public | Lua global | either | `LuaManager$GlobalObject.getLoosingXpValue @27 L9747` — returns **−1**, or −100 under `Core.debug` with the `fastLooseXp` cheat |
| global `getLoosingXpTick` | `(Object)I` | public | Lua global | either | `LuaManager$GlobalObject.getLoosingXpTick @48 L9758` — returns **10**, or 30000 under the same cheat |
| `GameServer.addXp` | `(IsoPlayer;Perk;F[Z[Z]])V` | public static | class not in the exposer set; reached from Lua through the `addXp` global | server | `GameServer.addXp @12–@52 L1893` — `canModifyPlayerStats` or return, then `XP.AddXP(perk, amount, false, !noMult, true, halo)`, then `updateXpChecker` |
| `GameServer.canModifyPlayerStats` | `(UdpConnection;IsoPlayer)Z` | public static | — | server | `GameServer.canModifyPlayerStats @4–@22 L1397` — true when the role has `Capability.CanModifyPlayerStatsInThePlayerStatsUI` **or** the connection owns that player |

The six-argument `AddXP`'s booleans are, in order: `b1` **unused in the body**, `b2` gates the whole
trait/`getMultiplier`/sandbox multiplier block (`@225 L14219` is the only read of it), `b3` **unused in
the body**, `b4` gates the halo text (`@1271 L14327` is its only read). A scan of the dumped body found
no other `iload_3` or `iload 5`.

### Writing a level, and what caps it

| Member | Signature | Flags | Exposed? | Side | Cite |
|---|---|---|---|---|---|
| `IsoGameCharacter.setPerkLevelDebug` | `(Perk;I)V` | public; in `ILuaGameCharacter` | yes | either; **pushes `SyncPerks` from a client** | `IsoGameCharacter.setPerkLevelDebug @10–@45 L4797` writes `PerkInfo.level` (creating the info if absent); `@46–@63 L4804` `GameClient.client && instanceof IsoPlayer` → `GameClient.sendPerks`. **No Java caller in the jar** (jar-wide scan: 0 references) |
| `IsoGameCharacter.LevelPerk` | `(Perk;Z)V` | public; in `ILuaGameCharacter` | yes | either | `IsoGameCharacter.LevelPerk @48–@56 L4839` increments; `@106–@120 L4843` clamps to 10; `@123–@162 L4846` sets `CharacterStat.FITNESS = level/5 − 1` **only under `Core.debug`**; `@163–@180 L4849` fires `LevelPerk`; `@183–@194 L4850` `GameClient.client` → `sendPerks`. Throws `IllegalArgumentException` on `Perks.MAX` (`@8–@25 L4832`) and `requireNonNull` on a nil perk (`@0 L4829`) |
| `IsoGameCharacter.LevelPerk` | `(Perk)V` | public | yes | either | `IsoGameCharacter.LevelPerk @3 L4869` — forwards with `true` |
| `IsoGameCharacter.LoseLevel` | `(Perk)V` | public; in `ILuaGameCharacter` | yes | either | `IsoGameCharacter.LoseLevel @10–@29 L4813` decrements and floors at 0; `@32–@48 L4817` fires `LevelPerk` with `false`; `@51–@75 L4819` sends `SyncPerks` from a client **only for `Perks.Sneak`**; the null-info branch at `@79 L4824` fires the event with level 0 |
| `IsoGameCharacter.level0` | `(Perk)V` | public; **absent from `ILuaGameCharacter`** | class exposed | either | `IsoGameCharacter.level0 @10–@12 L4875` — sets `PerkInfo.level = 0`, fires **no** event, sends **no** packet. **No Java caller in the jar** |
| `IsoGameCharacter.applyTraits` | `(List)V` | public; absent from `ILuaGameCharacter` | class exposed | either | `IsoGameCharacter.applyTraits @13–@36 L11627` seeds Fitness 5 and Strength 5, then `@455–@458 L11681` calls `LevelPerk` n times and `@467–@479 L11683` `setXPToLevel(perk, getPerkLevel(perk))` |
| `IsoGameCharacter.modifyTraitXPBoost` | `(CharacterTrait;Z)V`, `(CharacterTraitDefinition;Z)V` | public; in `ILuaGameCharacter` | yes | either | `IsoGameCharacter.modifyTraitXPBoost @99–@145 L11615` — adds or subtracts the definition's `getXpBoosts()` entries in the descriptor's boost map |
| the level cap | — | — | — | — | two places: `XP.AddXP @198–@221 L14213` discards any non-negative gain once `getXP(perk) >= perk.getTotalXpForLevel(10)`, and `LevelPerk @106–@120 L4843` clamps `PerkInfo.level` to 10 |
| the XP floor | — | — | — | — | `XP.AddXP @830–@861 L14274` clamps the new XP into `[0, totalXpForLevel(10)]` and rewrites the reported delta to match |

Level thresholds for both perks: `PerkFactory.init @1243 L320` (Fitness) and `@1282 L321` (Strength)
declare 1000, 2000, 4000, 6000, 12000, 20000, 40000, 60000, 80000, 100000 with the trailing
`passiv = true`; `PerkFactory.AddPerk @33–@40 L266` onward multiplies **each** by 1.5 before storing it,
so the effective ladder is 1500/3000/6000/9000/18000/30000/60000/90000/120000/150000 and
`getTotalXpForLevel(10)` is 487,500.

## B — which side owns perk XP and level in multiplayer

| Member | Signature | Flags | Exposed? | Side | Cite |
|---|---|---|---|---|---|
| `NetworkPlayerManager.update` | `()V` | — | — | **server only** | `NetworkPlayerManager.update @0–@3 L19` gates on `GameServer.server`; `@122–@141 L32–L33` calls `syncStats()` **and** `syncXp()` on every player whenever `statsUpdateLimit` fires |
| `NetworkPlayerManager.statsUpdateLimit` | `UpdateLimit` | private static | — | server | `NetworkPlayerManager.<clinit> @17–@23 L10` — **1000 ms** (damage 2000 ms, health 500 ms) |
| `NetworkPlayerAI.syncXp` | `()V` | public | — | server only | `NetworkPlayerAI.syncXp @0–@3 L719` gates on `GameServer.server`; `@32–@50 L722` sends `PacketType.PlayerXp` to that player's own connection |
| `PlayerXpPacket.write` | `(ByteBufferWriter)V` | — | — | sender | `PlayerXpPacket.write @5–@16 L34` — `PlayerID.write` then `getPlayer().getXp().save(bb)` |
| `PlayerXpPacket.parse` | `(ByteBufferReader;IConnection)V` | — | — | receiver, either side | `PlayerXpPacket.parse @6–@38 L43` — `isConsistent`, not dead, then `XP.load(bb, 249)` straight over the receiver's copy |
| `PlayerXpPacket.processServer` | `(PacketType;UdpConnection)V` | — | — | server | `PlayerXpPacket.processServer @3 L56` — `sendToClients`, i.e. a client-sent `PlayerXp` is applied on the server and relayed |
| `XP.save` payload | — | — | — | — | `IsoGameCharacter$XP.save @0 L14433` `characterTraits.save`, `@11 L14434` `totalXp`, `@20 L14435` `level`, `@29 L14436` `lastlevel`, `@38–@113 L14437` the `xpMap` size then each perk id + float, `@116–@183 L14444` the `perkList` size then each perk id + **`PerkInfo.level`**, `@186 L14451` `xpMapMultiplier`. `XP.load @0 L14384` reads the same, traits included |
| `GameClient.sendPerks` | `(IsoPlayer)V` | public static | — | client → server | `GameClient.sendPerks @7–@52 L2812–L2816` — `PacketType.SyncPerks`, `playerIndex` byte, then the **levels** of Sneak (`@24 L2814`), Strength (`@35 L2815`) and Fitness (`@46 L2816`) and nothing else |
| `GameServer.receiveSyncPerks` | `(ByteBufferReader;UdpConnection;S)V` | package-private static | — | server | `GameServer.receiveSyncPerks @36–@54 L4308–L4310` writes `remoteSneakLvl`/`remoteStrLvl`/`remoteFitLvl` — **not** the perk list — then `@57–@172 L4312` relays the same three ints to every other connection |
| `GameClient.receiveSyncPerks` | `(ByteBufferReader;S)V` | public static | — | client | `GameClient.receiveSyncPerks @37–@50 L2827` returns for a null or **local** player, then `@51–@68 L2830–L2832` writes the three `remote*Lvl` fields on the other player's copy |
| `IsoPlayer.remoteStrLvl` | `I` | public **field** | no (Kahlua publishes methods) | — | its only reader in the jar is `IsoPlayer.calculateCritChance @76 L4176` (`crit −= 1.5 × remoteStrLvl` for a player target); jar-wide scan: 6 references, 5 of them the write/parse path |
| `IsoPlayer.remoteFitLvl` | `I` | public field | no | — | jar-wide scan: **4 references, all writes** (`GameClient.receiveSyncPerks @68 L2832`, `GameServer.receiveSyncPerks @54 L4310`, `ConnectedPacket.parse @822 L213`, `ConnectedPacket.write @554 L329`) — **no reader** |
| `ConnectedPacket` | — | — | — | join | `ConnectedPacket.write @268 L298` / `parse @592 L180` carry the whole `XP.save` blob at connect; `write @543 L328` / `parse @815 L212` carry `remoteStrLvl` |
| `SyncPlayerStatsPacket` | — | — | in the exposer set (`@6638`) | — | a per-class scan for `Perk` and `Xp` references returned **zero** — the player-stats packet carries no perk or XP field |
| `IsoPlayer.isLocalPlayer` | `()Z` | public | yes | — | `IsoPlayer.isLocalPlayer @0–@7 L7032` — **returns false unconditionally when `GameServer.server` is set**, so the three gated `AddXP` overloads never run on a dedicated server |
| the `AddXP` Lua event | `(chr, perk, Float amount)` | — | — | **fires only when `GameClient.client` is null** | `IsoGameCharacter$XP.AddXP @1346–@1364 L14336–L14337` — `LuaEventManager.triggerEventGarbage('AddXP', chr, perk, Float.valueOf(delta))`; the amount is the clamped final delta |
| the `LevelPerk` Lua event | `(chr, perk, Integer level, Boolean gained)` | — | — | no side gate | `IsoGameCharacter.LevelPerk @163–@180 L4849` (`true`, `triggerEventGarbage`), `LevelPerk @277–@294 L4864` (`true`, `triggerEvent`, new-info branch), `IsoGameCharacter.LoseLevel @32–@48 L4817` and `@79–@92 L4824` (`false`, `triggerEvent`) |
| vanilla Lua listeners | — | — | — | server-side file | `media/lua/server/XpSystem/XpUpdate.lua:395` `Events.AddXP.Add(xpUpdate.addXp)` and `:397` `Events.LevelPerk.Add(xpUpdate.levelPerk)` |
| `AntiCheatXPUpdate.update` | `(UdpConnection)Z` | — | — | server | `AntiCheatXPUpdate.update @6–@17 L95` short-circuits when the anticheat is disabled, then `@46–@55 L100` fails on any of the connection's players |
| `AntiCheatXPUpdate.isPerkXpGrowthRateTooHigh` | `(IsoPlayer;Perk)Z` | — | — | server | `AntiCheatXPUpdate.isPerkXpGrowthRateTooHigh @38–@56 L70–L71` — flags when `xpNow − xpLastCheck > 1000.0 × getMaxPerkXpMultiplier × getMaxPerkXpBoostMultiplier` |
| `AntiCheat.update` | `(UdpConnection)V` | public | — | server | `AntiCheat.update @41–@46 L129` — a failing anticheat calls `act(connection, "update failed")`, which fans out to `doLogUser`/`doKickUser`/`doBanUser` |
| `NetworkCharacterAI.updateXpChecker` | `()V` | public | class not in the exposer set | server | `NetworkCharacterAI.updateXpChecker @7–@17 L418` copies `xpMap`, `@22–@39 L419` the boost map, `@44–@90 L420` the multiplier map into the checker's snapshot — this is what `GameServer.addXp` calls so a legitimate grant does not trip the anticheat |

The ownership answer in one line: the server's copy is authoritative and is re-pushed whole every
second; a client write reaches the server only through the Lua global `SyncXp(player)`; `SyncPerks` is a
cosmetic three-level side-channel and never writes a perk list.

A mod that writes a level or XP server-side and wants the client to see it immediately can call
`SyncXp` from the client or simply let the 1000 ms `PlayerXp` push carry it — the second is what makes
a server-side write "arrive on the next read", and it is also why the earlier Cooking-level reading
needed no wait.

## C — every Java consumer of the Strength and the Fitness perk level

Both lists are the full jar-wide reverse-reference scan of `PerkFactory$Perks.Strength` (98 references)
and `PerkFactory$Perks.Fitness` (57 references), with the `generation/*` script generators (52 Strength,
12 Fitness references — they emit script text, not behaviour) and the debug panels set aside. Every
consumer reads `getPerkLevel` inside its own body: **none of these formulas passes through Lua**, so
there is nothing to wrap.

### Strength

| Consumer | Formula or branch as read | Lua-wrappable? | Cite |
|---|---|---|---|
| `IsoGameCharacter.getHittingMod` | melee-damage multiplier ladder: 1→0.80, 2→0.85, 3→0.90, 4→0.95, 5→1.00, 6→1.05, 7→1.10, 8→1.15, 9→1.20, 10→1.25; fallthrough (level 0) 0.75 | Java only; sole caller `CombatManager.attackCollisionCheck @2054 L896` | `IsoGameCharacter.getHittingMod @1 L4544`, ladder `@13 L4546` … `@97 L4573`, fallthrough `@101 L4575` |
| `IsoGameCharacter.getShovingMod` | identical ladder 0.80…1.25, fallthrough 0.75 | Java only; callers `IsoGameCharacter.processHitDamage @49 L6225` and `HandWeapon.getStaggerBackTimeMod @47 L2439` | `IsoGameCharacter.getShovingMod @1 L4579`, `@13 L4581` … `@97 L4608`, fallthrough `@101 L4610` |
| `IsoGameCharacter.getWeightMod` | carry-capacity multiplier: 1→0.90, 2→1.07, 3→1.24, 4→1.41, 5→1.58, 6→1.75, 7→1.92, 8→2.09, 9→2.26, 10→2.50; fallthrough 0.80 | Java only; sole caller `BodyDamage.UpdateStrength @318 L2113` | `IsoGameCharacter.getWeightMod @1 L4680`, `@13 L4682` … `@99 L4709`, fallthrough `@102 L4711` |
| `BodyDamage.UpdateStrength` | `maxWeight = (int)(getMaxWeightBase() × getWeightMod()) − penalty`; `penalty` = HUNGRY lvl 2/3/4 → +1/+2/+2, THIRST 2/3/4 → +1/+2/+2, SICK 2/3/4 → +1/+2/+3, BLEEDING 2/3/4 → +1/+1/+1, INJURED 2/3/4 → +1/+2/+3; then clamp `< 0 → 0`; then for a player `maxWeight = (int)(maxWeight × getMaxWeightDelta())` | Java only, but **both inputs are Lua-settable** (`setMaxWeightBase`, `setMaxWeightDelta`); sole caller `BodyDamage.Update @242 L2206` | `BodyDamage.UpdateStrength @302–@327 L2113`, clamp `@328–@343 L2116–L2117`, delta `@346–@381 L2120–L2121`; moodle terms `@2–@299 L2062–L2108` |
| `IsoGameCharacter.getClimbingFailChanceFloat` | additive score, higher is safer: `+2×Fitness +2×Strength +2×Nimble −5×ENDURANCE −8×DRUNK −8×HEAVY_LOAD −5×PAIN`, then the weight-trait terms | Java only | `IsoGameCharacter.getClimbingFailChanceFloat @17 L17323` (Strength), `@4 L17322` (Fitness), `@29 L17324` (Nimble), moodles `@41–@112 L17326–L17329` |
| `IsoGameCharacter.getClimbRopeSpeed` | reads Fitness then Strength (int tier, clamped 0–10 per [body-and-weight](../../facts/body-and-weight.md#weight-traits)) | Java only | `IsoGameCharacter.getClimbRopeSpeed @1 L17409` (Strength), `@8 L17409` (Fitness) |
| `IsoGameCharacter.testDefense` | `score = 30 if ZombieHitReaction == KnifeDeath; + 3×weaponLevel + 2×Fitness + 2×Strength − 5×surroundingZombies − 2×ENDURANCE − 2×HEAVY_LOAD − 3×TIRED …`; early-out when facing FRONT, not crawling, and more than 3 attackers | Java only | `IsoGameCharacter.testDefense @75 L14498` (Strength), `@63 L14497` (Fitness), `@52 L14496` (weapon level), early-out `@0–@30 L14486` |
| `IsoGameCharacter.addCombatMuscleStrain` | strain ×`(15 − Strength)/10`; stomp base 0.30 → right leg, shove base 0.15 → both arms, aimed firearm `recoilDelay × FIREARM_RECOIL_MUSCLE_STRAIN_MODIFIER × weapon.muscleStrainMod × (15−Strength)/10`, ×0.5 on `Auto`, then × sandbox `muscleStrainFactor` | Java only, but the **outputs** are Lua-settable (`addXxxMuscleStrain`, `BodyPart.addStiffness`) | `IsoGameCharacter.addCombatMuscleStrain @12–@39 L17163–L17165` (stomp), `@55–@82 L17172–L17174` (shove), `@119–@199 L17185–L17193` (firearm) |
| `CombatManager.attackCollisionCheck` | stomp damage `Rand.Next(0.7f, 1.0f) + 0.2 × Strength`, then × `Clothing.getStompPower()` or ×0.5 barefoot | Java only | `CombatManager.attackCollisionCheck @2600–@2620 L972`, shoes `@2622–@2658 L973–L977` |
| `IsoPlayer.calculateCritChance` | `+2 × Strength` for the attacker; against another player `−1.5 × target.remoteStrLvl` and a `±(weight − 80)/2` term off `Nutrition.getWeight()`; then `−5×ENDURANCE −5×HEAVY_LOAD −1.3×PANIC` | Java only | `IsoPlayer.calculateCritChance @181 L4188` (Strength), `@76 L4176` (`remoteStrLvl`), weight `@65–@127 L4177–L4180` |
| `IsoDoor.WeaponHit` | door-damage multiplier ladder by Strength: 0→0.50, 1→0.63, 2→0.76, … (continues past the read window) | Java only; note it fires a Lua event first (`LuaEventManager.triggerEvent @63 L1174`) | `IsoDoor.WeaponHit @82–@129 L1184–L1191` |
| `OpenWindowState.onAttemptFinished` | forced-open success roll: Strength > 7 → `Rand.Next(100) < 20`, > 5 → `< 10`, > 3 → `< 6`, > 1 → `< 4` | Java only | `OpenWindowState.onAttemptFinished @146–@249 L202–L209` |
| `IsoMovingObject.separate` | bump-trip score `10 − 3·bumpNbr + Fitness + Strength − 2·DRUNK`, clamped `[1,80]`, trip if `Rand.Next(n) == 0` (already `#0541`) | Java only | `IsoMovingObject.separate @720 L1346` (Strength), `@708 L1345` (Fitness) |
| `HandWeapon.getRecoilDelay(chr)` | `max(0, recoilDelay × (1 − Aiming/40) × (1 − (−10 + 2×Strength)/40) × (1.3 if one-handed with a full off-hand))` | Java only | `HandWeapon.getRecoilDelay @21–@41 L1278–L1279` |
| `HandWeapon.checkJam` | jam roll reads Strength twice | Java only | `HandWeapon.checkJam @48 L2104`, `@70 L2104` |
| `IsoAnimal.canBePicked` | Strength gate on picking an animal up (short-circuited by `isUnlimitedCarry()` or `isGodMod()`) | Java only | `IsoAnimal.canBePicked @36 L3452`, override `@0–@15 L3449–L3450` |
| `ISWorldObjectContextMenuLogic.createMenuEntries` | a Strength gate on a world-object menu entry | Java only | `ISWorldObjectContextMenuLogic.createMenuEntries @2111 L870` |
| `ClimbOverWallState.execute` / `setParams` | Strength read in the wall-climb state | Java only | `ClimbOverWallState.execute @29 L105`, `setParams @327 L364` |
| `ClimbSheetRopeState.execute`, `ClimbDownSheetRopeState.execute` | Strength and Fitness both read per rope tick | Java only | `ClimbSheetRopeState.execute @253 L123`, `ClimbDownSheetRopeState.execute @262 L90` |
| `IsoGameCharacter.hitConsequences`, `IsoPlayer.hitConsequences` | Strength **XP** +2.0 on a knockback that did not kill (`isKnockBackOnNoDeath`); server arm `GameServer.addXp`, single-player arm `XP.AddXP` | the XP amount is Java; the decay/trait reaction is Lua (`Events.AddXP`) | `IsoGameCharacter.hitConsequences @103–@158 L6310–L6317`, `IsoPlayer.hitConsequences @196–@232 L4465–L4470` |
| `Fitness.exerciseRepeat`, `Fitness.incStats` | caches and then awards Strength XP (see `## D`) | the driver is Lua (`ISFitnessAction`) | `Fitness.exerciseRepeat @19 L192`, `Fitness.incStats @195 L351`, `@230 L355` |
| `IsoGameCharacter.applyTraits` | Strength baseline 5 at character creation | Java; `applyTraits` itself is public | `IsoGameCharacter.applyTraits @25–@36 L11628` |
| `XP.AddXP` | the protein multiplier and the level-10 sound skip | Java | `IsoGameCharacter$XP.AddXP @112 L14203`, `@1028 L14296` |

### Fitness

| Consumer | Formula or branch as read | Lua-wrappable? | Cite |
|---|---|---|---|
| `IsoGameCharacter.getFatigueMod` | endurance-cost multiplier: 1→0.95, 2→0.92, 3→0.89, 4→0.87, 5→0.85, 6→0.83, 7→0.81, 8→0.79, 9→0.77, 10→0.75; fallthrough (level 0) **1.0** | Java only; callers `CombatManager.processWeaponEndurance @61 L1200` and `CombatManager.applyMeleeEnduranceLoss @105 L3774` | `IsoGameCharacter.getFatigueMod @1 L4428`, `@13 L4430` … `@99 L4457`, fallthrough `@103 L4459` |
| `IsoGameCharacter.getPacingMod` | endurance-drain multiplier: 1→0.80, 2→0.75, 3→0.70, 4→0.65, 5→0.60, 6→0.57, 7→0.53, 8→0.49, 9→0.46, 10→0.43; fallthrough 0.90 | Java only; callers `IsoPlayer.updateEndurance @161 L3459`, `@438 L3496` | `IsoGameCharacter.getPacingMod @1 L4498`, `@13 L4500` … `@99 L4527`, fallthrough `@103 L4529` |
| `IsoGameCharacter.getRecoveryMod` | base ladder 0→0.70, 1→0.80, 2→0.90, 3→1.00, 4→1.10, 5→1.20, 6→1.30, 7→1.40, 8→1.50, 9→1.55, 10→1.60; then ×0.4 Obese, ×0.7 Overweight, ×0.7 Very Underweight, ×0.3 Emaciated; then **lipids < −1500 → ×0.2, else < −1000 → ×0.5**; then **proteins < −1500 → ×0.2, else < −1000 → ×0.5** | Java only; callers `IsoPlayer.updateStats_Sleeping @35 L3295`, `updateEnduranceWhileSitting @51 L3410`, `updateEnduranceWhileInVehicle @72 L3422`, `updateEndurance @626 L3522`, `@738 L3534` | `IsoGameCharacter.getRecoveryMod @1 L4614`, ladder `@10–@110 L4616–L4647`, traits `@111–@186 L4649–L4659`, lipids `@194–@241 L4664–L4667`, proteins `@242–@289 L4670–L4673` |
| `IsoGameCharacter.calculateCombatSpeed` | `0.8 × weapon.getBaseSpeed()`; ×0.77 two-handed held in one hand; × `getChopTreeSpeed()` for an axe; `− 0.07 × ENDURANCE`; `− 0.07 × HEAVY_LOAD`; `+ 0.03 × weaponLevel`; **`+ 0.02 × Fitness`**; ×0.95 with a bag in the off-hand; × `Rand.Next(1.1, 1.2)`; × `combatSpeedModifier`; × `getArmsInjurySpeedModifier()`; × `Thermoregulator.getCombatModifier()`; clamped to `[0.8, 1.6]`; then ×1.2 for a heavy two-hander | Java only; sole caller `CombatManager.pressedAttack @221 L3162` | `IsoGameCharacter.calculateCombatSpeed @143–@157 L9878` (Fitness), chain `@0–@277 L9857–L9898`, clamp `@237–@252 L9893–L9894` |
| `IsoGameCharacter.updateFitness` | `CharacterStat.FITNESS = Fitness/5 − 1` | **private — not Lua-callable**; the same write also happens in `LevelPerk` and `setXPToLevel` under `Core.debug` | `IsoGameCharacter.updateFitness @0–@24 L10312` |
| `IsoPlayer.setFitnessSpeed` | anim variable `FitnessSpeed = Fitness/5/1.1 − ENDURANCE/20`, capped at 1.5, and when below 0.85 forced to 1.0 with `FitnessStruggle = 1` | public; called from `ISFitnessAction` Lua | `IsoPlayer.setFitnessSpeed @7–@76 L9138–L9146` |
| `IsoGameCharacter.handleLandingImpact` | fall damage and landing severity read Fitness in three places, alongside the weight-trait terms | **protected** | `IsoGameCharacter.handleLandingImpact @288 L2233`, `@726 L2301`, `@740 L2302` |
| `IsoGameCharacter.attackFromWindowsLunge` | window-lunge score reads Fitness | public | `IsoGameCharacter.attackFromWindowsLunge @194 L15197` |
| `ClimbOverFenceState.shouldFallAfterVaultOver` | `Rand.Next(100) < n − Fitness` (already `#0541`) | Java only | `ClimbOverFenceState.shouldFallAfterVaultOver @242 L595` |
| `ClimbThroughWindowState.checkForFallingBack`, `GrappledThrownOutWindowState.checkForFallingBack` | fall-back rolls read Fitness | Java only | `ClimbThroughWindowState.checkForFallingBack @77 L255`, `GrappledThrownOutWindowState.checkForFallingBack @77 L228` |
| `OpenWindowState.exert`, `CloseWindowState.exert` | window exertion reads Fitness | Java only | `OpenWindowState.exert @1 L233`, `CloseWindowState.exert @8 L179` |
| `IsoDoor.WeaponHit` | a `tableswitch` on Fitness for the endurance cost of a door hit | Java only | `IsoDoor.WeaponHit @287–@294 L1217` |
| `IsoPlayer.updateInternal2` | passive Fitness XP +1.0 on a `Rand` roll while moving; `GameServer.addXp` on a server, `XP.AddXP` in single-player | Java, and duplicated in `XpUpdate.lua`'s `onPlayerMove` | `IsoPlayer.updateInternal2 @771–@796 L2365–L2368` |
| `Nutrition.canAddFitnessXp` | blocks Fitness (and, through `AddXP`'s gate, Strength) XP — see `## D` | Java | `Nutrition.canAddFitnessXp @0–@85 L275–L280` |
| `AddXPCommand.Command` | the server console `addxp` command names Fitness | server command | `AddXPCommand.Command @258 L71`, `@276 L72` |
| `Fitness.*` | see `## D` | the driver is Lua | `Fitness.exerciseRepeat @5 L191`, `incStats @205 L352`, `@244 L356` |

### Can "effective strength" be imposed without moving the perk level?

For carry capacity, **yes**, three ways, all public and all uncontested:

| Member | Signature | Flags | Exposed? | Side | Cite |
|---|---|---|---|---|---|
| `IsoGameCharacter.setMaxWeightBase` | `(I)V` | public (absent from `ILuaGameCharacter`) | class exposed | either | `IsoGameCharacter.setMaxWeightBase @2 L3864`; the field is written **only** in `IsoGameCharacter.<init> @458 L540` and by this setter — jar-wide scan of `setMaxWeightBase` callers: **0** |
| `IsoPlayer.setMaxWeightDelta` | `(F)V` | public | yes | either | `IsoPlayer.setMaxWeightDelta @2 L8457`; the field is written **only** in the two `IsoPlayer.<init>` overloads from the STRONG (1.5) / WEAK (0.75) / FEEBLE (0.9) / STOUT (1.25) traits (`IsoPlayer.<init> @1168–@1241 L624–L630` and `@1103–@1176 L699–L705`) — jar-wide scan of `setMaxWeightDelta` callers: **0**. It is re-multiplied in every `UpdateStrength` |
| `IsoGameCharacter.setUnlimitedCarry` | `(Z)V` | public | class exposed | either | callers `IsoGameCharacter.load @522 L5275`, `IsoPlayer.setRole @117 L9404`, `ExtraInfoPacket.processClient @102 L213`, `processServer @329 L288` — so a mod's write here **is** contested by role and by `ExtraInfoPacket` |
| `IsoGameCharacter.setMaxWeight` | `(I)V` | public | class exposed | either | `IsoGameCharacter.setMaxWeight` is called inside `UpdateStrength @325 L2113` itself, so a Lua write to it is overwritten on the next `BodyDamage.Update` — use `setMaxWeightBase`/`setMaxWeightDelta` instead |

Because the STRONG/WEAK/FEEBLE/STOUT traits only reach `maxWeightDelta` in the **constructor**, and
`XpUpdate.lua` adds and removes those traits on every Strength level-up, vanilla already never refreshes
the delta after creation — so a mod owning `setMaxWeightDelta` is not fighting anything.

For everything else, **no**:

| Would-be modifier | Verdict | Cite |
|---|---|---|
| melee damage | no setter; `getHittingMod` recomputes from the level on every hit | `IsoGameCharacter.getHittingMod @1 L4544`; jar-wide grep `setHittingMod`, `setMeleeDamageMod`, `setStrengthMod`, `setEffectiveStrength` → **no class contains that literal** |
| knockback | `IsoGameCharacter.knockbackAttackMod` is a public **field** written only in `<init> @126 L433` and read by `CombatManager.attackCollisionCheck @2918 L1025`, `@2947 L1029` and `IsoGameCharacter.processHitDamage @150 L6239`; Kahlua publishes methods, so Lua cannot reach it | jar-wide grep `setKnockbackMod`, `getKnockbackAttackMod` → **no class contains that literal** |
| combat speed | `IsoGameCharacter.combatSpeedModifier` is **private** with no accessor and is rewritten by `updateSpeedModifiers` from clothing (`@12`, `@58`, `@68`, `@85`, `@98 L10096–L10106`) | jar-wide grep `setCombatSpeedModifier` hits only `Clothing` and `Item` (the script-item field), never `IsoGameCharacter` |
| shove / stagger, climb, defence, stomp, door damage, recoil, jam, muscle strain | each reads `getPerkLevel` live inside a Java body with no Lua step in the chain | the per-consumer cites in the Strength table above |

## D — Fitness and Strength XP-gain sources, gates and decay

| Source or gate | What it does as read | Side | Cite |
|---|---|---|---|
| `Nutrition.canAddFitnessXp` | `Fitness >= 9 && characterHaveWeightTrouble()` → false; `Fitness >= 6` → false when Emaciated, Obese **or** Very Underweight; below 6 → always true | server or host, wherever `AddXP` runs | `Nutrition.canAddFitnessXp @0–@23 L275–L276`, `@24–@83 L277–L278`, `@84 L280` |
| the Fitness gate inside `AddXP` | Fitness perk and `chr instanceof IsoPlayer` and `!getNutrition().canAddFitnessXp()` → **return**, the gain is dropped entirely | same | `IsoGameCharacter$XP.AddXP @63–@106 L14196–L14198` |
| the Strength protein multiplier | Strength perk and `chr instanceof IsoPlayer`: `50 < proteins < 300` → amount ×1.5; `proteins < −300` → amount ×0.7 (the two are sequential, not exclusive) | same | `IsoGameCharacter$XP.AddXP @107–@190 L14203–L14208` |
| the asleep gate | `isAsleep()` → return before anything | same | `IsoGameCharacter$XP.AddXP @0–@10 L14183–L14184` |
| the level-10 cap | non-negative gain and `getXP(perk) >= perk.getTotalXpForLevel(10)` → return | same | `IsoGameCharacter$XP.AddXP @207–@221 L14214–L14215` |
| trait XP boosts | walks `getDescriptor().getXPBoostMap()`: boost 0 → ×0.25 (unless speed-reduction-excluded), boost 1 on Sprinting → ×1.25, boost 1 → ×1.0, boost 2 → ×1.33, boost ≥ 3 → ×1.66 (the last two unless speed-increase-excluded); a perk **absent** from the map → the whole multiplier is set to 0.25 | same | `IsoGameCharacter$XP.AddXP @230–@509 L14221–L14239` |
| learner and profession traits | FAST_LEARNER ×1.3, SLOW_LEARNER ×0.7, PACIFIST ×0.75 on the six melee perks and on Aiming, CRAFTY ×1.3 on a child of Crafting | same | `IsoGameCharacter$XP.AddXP @511–@731 L14242–L14257` |
| `XP.getMultiplier` | applied only when strictly greater than 1 | same | `IsoGameCharacter$XP.AddXP @738–@756 L14261–L14263` |
| sandbox XP multipliers | `multipliersConfig.xpMultiplierGlobalToggle` true → × `xpMultiplierGlobal`; otherwise × the per-perk option looked up by name through `SandboxOptions.getOptionByName(...)` and `Float.parseFloat` of its string value | same | `IsoGameCharacter$XP.AddXP @757–@823 L14266–L14269`; the option set is `SandboxOptions$MultiplierConfig` with `xpMultiplierFitness`, `xpMultiplierStrength` and 34 more siblings plus the global pair |
| the Fitness `CharacterStat` sync | after a level change, Fitness perk → `getStats().set(CharacterStat.FITNESS, level/5 − 1)` | same | `IsoGameCharacter$XP.AddXP @1217–@1250 L14318–L14319`; the same write also sits in `IsoGameCharacter.updateFitness @0 L10312` (private) and, `Core.debug`-gated, in `LevelPerk @123–@162 L4846–L4847` and `setXPToLevel @71–@105 L14473–L14474` |
| exercise XP | `ISFitnessAction:exeLooped` → `Fitness.exerciseRepeat()` → `incRegularity`, `reduceEndurance`, `incFutureStiffness`, `incStats`, `updateExeTimer`, then on a server `GameServer.sendSyncPlayerFields(player, 32)` | Lua drives it; the award is server-side | `Fitness.exerciseRepeat @0–@77 L191–L200`; `media/lua/shared/TimedActions/ISFitnessAction.lua:118-122` (`exeLooped`) and `:127-129` (`serverStart` calls `init` and `setCurrentExercise`) |
| `Fitness.incStats` | from the current exercise's `stiffnessInc` list: `arms` → strXp += 4, `chest` → strXp += 2, `legs` → fitXp += 4, `abs` → fitXp += 2; then `strLvl > 5` → strXp × `(1 + (strLvl−5)/10)` (**integer division**, so the factor is 1 for levels 6–10 and 2 only at 15); same shape for `fitLvl`; both × `currentExe.xpModifier`; then `GameServer.server` → `GameServer.addXp(player, Strength/Fitness, (int)xp)`, else `GameClient.client != null` → **nothing**, else `XP.AddXP` | server or host only | `Fitness.incStats @4–@101 L322–L334`, `@102–@147 L339–L343`, `@148–@167 L346–L347`, `@168–@213 L349–L352`, `@217–@250 L354–L356` |
| combat Strength XP | +2.0 per knockback-without-death | server or host | `IsoGameCharacter.hitConsequences @103–@158 L6310–L6317`; `IsoPlayer.hitConsequences @196–@232 L4465–L4470` |
| passive Fitness XP | +1.0 on a `Rand` roll while moving | server or host | `IsoPlayer.updateInternal2 @771–@796 L2365–L2368` |
| the Lua XP table | `XpUpdate.lua` grants: Fitness 1 and Sprinting 1 while running above the endurance warning, Nimble 1 while aiming and moving, **Strength 2 while inventory weight > maxWeight × 0.5**, Strength 2 on `OnWeaponHitTree`, Fitness 1 per successful non-ranged swing above the endurance warning, **Strength `getLastHitCount()` per non-ranged hit** | the `addXp` global is server-side; `randXp()` itself differs by side (`ZombRand(100 × invMultiplier) == 0` on a server, `ZombRand(700 × invMultiplier) == 0` on a client) | `media/lua/server/XpSystem/XpUpdate.lua:9-38`, `:41-45`, `:47-105`, `:167-172` |
| regularity | `Fitness.incRegularity`: `inc = 0.08 × ln(5)/ln(fitnessLvl/5 + 4)`, added to `regularityMap[exerciseType]`, clamped `[0, 100]` | wherever `exerciseRepeat` runs | `Fitness.incRegularity @0–@116 L220–L236` |
| regularity decay | `Fitness.decreaseRegularity`: for each exercise with a timer, if `now − exeTimer > 86,400,000 ms` (one in-game day) then `regularity −= 0.002` — **no floor clamp on this path** | wherever `Fitness.update` runs | `Fitness.decreaseRegularity @46–@109 L143–L146` |
| `Fitness.update` cadence | early-outs unless `GameTime.getMinutes()/10` changed, so effectively once per ten game minutes; then `decreaseRegularity` and the stiffness-timer walk | sole caller `IsoPlayer.updateInternal2 @409 L2310` | `Fitness.update @0–@49 L88–L99`, stiffness walk `@49–@187 L102–L114` |
| the Fitness Lua surface | `IsoPlayer.getFitness()` public → `Fitness` is in the exposer set; public members include `init`, `setCurrentExercise(String)`, `exerciseRepeat`, `incRegularity`, `reduceEndurance`, `incFutureStiffness`, `incStats`, `resetValues`, `removeStiffnessValue(String)`, `getRegularity(String)`, `getRegularityMap`, `setRegularityMap(HashMap)`, `onGoingStiffness`, `getCurrentExe`, `getCurrentExeStiffnessTimer(String)`, `getCurrentExeStiffnessInc(String)`, `getParent`, `setParent`, `save`, `load`, `initRegularityMapProfession`. `decreaseRegularity`, `increasePain(String)` and `updateExeTimer` are **private** | either | member list and flags of `zombie/characters/BodyDamage/Fitness`; vanilla Lua uses `getFitness():getRegularity` at `media/lua/client/ISUI/ISFitnessUI.lua:194`, `:init()` at `:352` and `removeStiffnessValue` at `media/lua/client/XpSystem/ISUI/ISHealthPanel.lua:278` and `media/lua/server/ClientCommands.lua:547` |
| muscle strain, the stat | `BodyPart.stiffness` is a private float with public `getStiffness()`, `setStiffness(F)`, `addStiffness(F)`; `IsoGameCharacter` adds to it through public `addCombatMuscleStrain(InventoryItem[,I[,F]])`, `addArmMuscleStrain(F)`, `addLeftArmMuscleStrain(F)`, `addBothArmMuscleStrain(F)`, `addBackMuscleStrain(F)`, `addNeckMuscleStrain(F)`, `addRightLegMuscleStrain(F)`; the private statics `BaseMuscleStrainMultiplier` and `meleeWeaponMuscleStrainAdjustment` are not reachable | either | flags of `BodyPart` and `IsoGameCharacter`; `IsoGameCharacter.addCombatMuscleStrain @36–@39 L17165`, `@79–@82 L17174` |
| passive perk decay | **there is none in Java.** The whole mechanism is `XpUpdate.lua:299-331`: per player, `strengthUpTimer += getLoosingXpTick(timer)`; once `> 20000` and the 1200-unit bucket changed, `addXp(player, Perks.Strength, getLoosingXpValue())` then `checkForLosingLevel`; `> 31000` resets to 0; the identical block for Fitness follows. `xpUpdate.addXp` (on the `AddXP` event) subtracts 3000 from the timer on any positive gain, floored at −50000. Timers live in the player's **modData** (`strengthUpTimer`, `strengthMod`, `fitnessUpTimer`, `fitnessMod`), defaulting to −50000 | the loop uses `getOnlinePlayers()` when `isServer()` | `media/lua/server/XpSystem/XpUpdate.lua:176-196` (the reset), `:289-297` (`checkForLosingLevel`), `:299-331` (the decay), `:334-345` (the modData), and `getLoosingXpValue/Tick` cites in `## A` |
| level → trait mapping | on the `LevelPerk` event, Strength level clears WEAK/FEEBLE/STOUT/STRONG then adds WEAK at 0–1, FEEBLE at 2–4, STOUT at 6–8, STRONG at ≥ 9; Fitness level clears UNFIT/OUT_OF_SHAPE/FIT/ATHLETIC then adds UNFIT at 0–1, OUT_OF_SHAPE at 2–4, FIT at 6–8, ATHLETIC at ≥ 9. **Level 5 gets no trait in either ladder.** All of it is Lua and therefore replaceable | the file is `server/` so it also runs in the client VM | `media/lua/server/XpSystem/XpUpdate.lua:319-396` region — Strength block `:325-345`, Fitness block `:346-361` |

## E — absences, each proved by a jar-wide grep

The grep is the disassembler's byte scan over every class entry, so "no class contains that literal" is
the absence of the identifier in any form — declaration, call, descriptor or string constant. Every
search below returned that answer, and none came near the `--max 60` cap.

| Searched literal | Result | What it means |
|---|---|---|
| `SkillRust` | no class contains that literal | no Java skill-rust mechanism |
| `skillRust` | no class contains that literal | same, lower-cased |
| `XPDecay` | no class contains that literal | no Java XP decay |
| `xpDecay` | no class contains that literal | same |
| `LoseXP` | no class contains that literal | no XP-removal member |
| `RemoveXP` | no class contains that literal | same |
| `FitnessUpdater` | no class contains that literal | the class the question asked about does not exist; the real class is `zombie/characters/BodyDamage/Fitness` |
| `leanBodyMass` | no class contains that literal | nothing in the engine models lean mass; the mod must compute it |
| `LeanBodyMass` | no class contains that literal | same |
| `setStrengthLevel` | no class contains that literal | no direct Strength-level setter besides the generic perk methods |
| `setFitnessLevel` | no class contains that literal | same for Fitness |
| `setEffectiveStrength` | no class contains that literal | there is no "effective strength" concept in the engine |
| `setStrengthMod` | no class contains that literal | no Strength modifier setter |
| `setHittingMod` | no class contains that literal | melee damage cannot be overridden without the perk level |
| `setMeleeDamageMod` | no class contains that literal | same |
| `setKnockbackMod` | no class contains that literal | no knockback setter |
| `getKnockbackAttackMod` | no class contains that literal | the field has no getter, so Kahlua cannot reach it |
| `setCombatSpeedModifier` | hits `zombie/inventory/types/Clothing` and `zombie/scripting/objects/Item` only | it is a script-item property, not a character setter; `IsoGameCharacter.combatSpeedModifier` is private with no accessor |
| `MuscleStrainLevel` | no class contains that literal | strain has no level abstraction; it is `BodyPart.stiffness` |
| `muscleStrain` | hits `generation/TimedActionScriptGenerator`, `generation/builders/TimedActionBuilder`, `zombie/SandboxOptions`, `zombie/characters/IsoGameCharacter` | the sandbox option `muscleStrainFactor` and the character's adders — no separate strain stat class |
| `getPerkXp` | no class contains that literal | perk XP is read as `getXp():getXP(perk)`, two calls |
| `setPerkLevel` | hits only `ILuaGameCharacter`, `IsoGameCharacter`, `FirearmPanel`, `ScenePanel` | all four are the `setPerkLevelDebug` prefix; there is no plain `setPerkLevel` |
| `OnLevelPerk` | no class contains that literal | the event name is `LevelPerk`, without the `On` |
| `OnPerkLevel` | no class contains that literal | same |
| `OnAddXP` | no class contains that literal | the event name is `AddXP`, without the `On` |
| `PerksPacket` | no class contains that literal | the perk packets are `SyncPerks` (a `GameClient`/`GameServer` method pair, not a class) and `zombie/network/packets/PlayerXpPacket` |

Two further absences are reverse-scan results rather than greps, and are stated with that bound:

- `IsoPlayer.remoteFitLvl` has **no reader** — the jar-wide scan over every method of every class holding
  the literal found 4 references, all of them writes.
- `setMaxWeightBase` and `setMaxWeightDelta` have **no Java caller** — the same scan returned 0
  references for each.

## Claims candidates

Each line is worded as the claim it would become, with its cite, grade C and the bound `C-only` (a
static bytecode reading of one jar of build 42.20.4; nothing here was measured on a session).

1. A perk's level and a perk's XP are two separate stores and Lua reads each with its own call: the level through `getPerkLevel(perk)` off `PerkInfo.level`, the XP through `getXp():getXP(perk)` off `xpMap` — `jar:IsoGameCharacter.getPerkLevel @11 L4788`, `jar:IsoGameCharacter$XP.getXP @5 L14359` · C · C-only.
2. `XP.AddXP(perk, float)` and its three- and four-argument siblings return without doing anything unless the character is the local player, so all three are no-ops for every player on a dedicated server — `jar:IsoGameCharacter$XP.AddXP @6–@24 L14144`, `jar:IsoPlayer.isLocalPlayer @0–@7 L7032` · C · C-only.
3. Only the five- and six-argument `XP.AddXP` overloads reach the method body without a local-player gate — `jar:IsoGameCharacter$XP.AddXP @0–@9 L14179`, `jar:IsoGameCharacter$XP.AddXP @0 L14183` · C · C-only.
4. The six-argument `XP.AddXP` reads only its second and fourth booleans: the second gates the whole trait, multiplier and sandbox block and the fourth gates the halo text, while the first and third are unused in the body — `jar:IsoGameCharacter$XP.AddXP @225 L14219`, `@1271 L14327` · C · C-only.
5. `XP.AddXP` drops a Fitness gain entirely when `Nutrition.canAddFitnessXp()` is false — `jar:IsoGameCharacter$XP.AddXP @63–@106 L14196–L14198` · C · C-only.
6. `XP.AddXP` multiplies a Strength gain by 1.5 while proteins are strictly between 50 and 300, and by 0.7 while proteins are below −300 — `jar:IsoGameCharacter$XP.AddXP @107–@190 L14203–L14208` · C · C-only.
7. `XP.AddXP` discards any non-negative gain once the perk's XP has reached `Perk.getTotalXpForLevel(10)`, and clamps the stored XP into `[0, totalXpForLevel(10)]` — `jar:IsoGameCharacter$XP.AddXP @207–@221 L14214–L14215`, `@830–@861 L14274–L14280` · C · C-only.
8. A perk absent from the character descriptor's XP-boost map earns XP at a quarter rate: the multiplier is set to 0.25 unless the perk is speed-reduction-excluded — `jar:IsoGameCharacter$XP.AddXP @490–@509 L14238–L14239` · C · C-only.
9. Strength and Fitness cost 1500, 3000, 6000, 9000, 18000, 30000, 60000, 90000, 120000 and 150000 XP per level, 487,500 in total, because `AddPerk` multiplies each declared threshold by 1.5 — `jar:PerkFactory.init @1243 L320`, `@1282 L321`, `jar:PerkFactory.AddPerk @33–@40 L266` · C · C-only.
10. `XP.setXPToLevel(perk, level)` writes the XP map to that level's total and leaves the perk level untouched, firing no event — `jar:IsoGameCharacter$XP.setXPToLevel @54–@70 L14472` · C · C-only.
11. `XP.getMultiplier(perk)` answers 0.0 rather than 1.0 when the perk has no multiplier entry — `jar:IsoGameCharacter$XP.getMultiplier @16 L14107` · C · C-only.
12. `XP.AddXP(HandWeapon, int)` is a declared overload with an empty body — `jar:IsoGameCharacter$XP.AddXP @0 L14367` · C · C-only.
13. A perk level moves only through `LevelPerk`, `LoseLevel`, `setPerkLevelDebug` and `level0`, and the last two have no caller anywhere in the jar — `jar:jar-wide scan of setPerkLevelDebug` (0 references), `jar:jar-wide scan of level0` (0 references) · C · C-only.
14. `LevelPerk` clamps the perk level to 10 and throws on `Perks.MAX` or a nil perk — `jar:IsoGameCharacter.LevelPerk @106–@120 L4843`, `@8–@25 L4832`, `@0 L4829` · C · C-only.
15. `level0(perk)` sets the level to zero and fires no Lua event and sends no packet, unlike `LoseLevel` — `jar:IsoGameCharacter.level0 @10–@12 L4875` · C · C-only.
16. A perk level change made on a client sends `SyncPerks` from `LevelPerk` and `setPerkLevelDebug`, but from `LoseLevel` only for `Perks.Sneak` — `jar:IsoGameCharacter.LevelPerk @183–@194 L4850`, `jar:IsoGameCharacter.setPerkLevelDebug @46–@63 L4804`, `jar:IsoGameCharacter.LoseLevel @51–@75 L4819` · C · C-only.
17. The server owns perk XP and perk level and re-pushes the whole XP object to each player's own connection every 1000 ms — `jar:NetworkPlayerManager.update @0–@141 L19–L33`, `jar:NetworkPlayerManager.<clinit> @17–@23 L10`, `jar:NetworkPlayerAI.syncXp @0–@50 L719–L722` · C · C-only.
18. The `PlayerXp` packet carries the character's traits, total XP, global level, the whole per-perk XP map, the whole per-perk level list and the XP multiplier map, and its receiver loads them straight over its own copy — `jar:IsoGameCharacter$XP.save @0–@186 L14433–L14451`, `jar:PlayerXpPacket.write @5–@16 L34`, `jar:PlayerXpPacket.parse @6–@38 L43` · C · C-only.
19. The only client-to-server perk-XP write path is the Lua global `SyncXp(player)`, which is client-gated and whose server handler applies the packet and relays it to the other clients — `jar:LuaManager$GlobalObject.SyncXp @0–@17 L9830`, `jar:PlayerXpPacket.processServer @3 L56` · C · C-only.
20. The `SyncPerks` packet carries only the Sneak, Strength and Fitness levels and both receivers write them into `remoteSneakLvl`, `remoteStrLvl` and `remoteFitLvl` rather than into the perk list — `jar:GameClient.sendPerks @7–@52 L2812–L2816`, `jar:GameServer.receiveSyncPerks @36–@54 L4308–L4310`, `jar:GameClient.receiveSyncPerks @51–@68 L2830–L2832` · C · C-only.
21. `remoteStrLvl`'s only reader in the jar is the crit-chance calculation and `remoteFitLvl` has no reader at all; both are public fields with no getter, so Lua cannot read either — `jar:IsoPlayer.calculateCritChance @76 L4176`, `jar:jar-wide scan of IsoPlayer.remoteFitLvl` (4 references, all writes) · C · C-only.
22. The player-stats packet carries no perk or XP field — `jar:per-class scan of SyncPlayerStatsPacket for Perk and Xp` (0 references) · C · C-only.
23. The Lua global `addXp(player, perk, amount)` routes to `GameServer.addXp` on a server and does nothing at all on a multiplayer client — `jar:LuaManager$GlobalObject.addXp @8–@38 L9780` · C · C-only.
24. `GameServer.addXp` is capability-gated, calls the six-argument `AddXP` so it bypasses the local-player gate, and then refreshes the anticheat's XP snapshot — `jar:GameServer.addXp @12–@52 L1893–L1898`, `jar:GameServer.canModifyPlayerStats @4–@22 L1397` · C · C-only.
25. The server flags a player whose per-perk XP grew by more than `1000 × maxMultiplier × maxBoostMultiplier` between anticheat checks, and a flagged anticheat logs, kicks or bans — `jar:AntiCheatXPUpdate.isPerkXpGrowthRateTooHigh @38–@56 L70–L71`, `jar:AntiCheat.update @41–@46 L129` · C · C-only.
26. The `AddXP` Lua event fires from `XP.AddXP` only when `GameClient.client` is null, so it never fires on a multiplayer client — `jar:IsoGameCharacter$XP.AddXP @1346–@1364 L14336–L14337` · C · C-only.
27. The `LevelPerk` Lua event fires with the post-change level and a gained flag from both `LevelPerk` (true) and `LoseLevel` (false), with no side gate — `jar:IsoGameCharacter.LevelPerk @163–@180 L4849`, `jar:IsoGameCharacter.LoseLevel @32–@48 L4817` · C · C-only.
28. Carry capacity is `(int)(maxWeightBase × getWeightMod()) − moodlePenalty`, floored at zero, then multiplied by the player's `maxWeightDelta` — `jar:BodyDamage.UpdateStrength @302–@381 L2113–L2121` · C · C-only.
29. `setMaxWeightBase` and `setMaxWeightDelta` are public, have no Java caller in the jar, and are both re-read on every carry-capacity recompute, so a mod can own carry capacity without touching the perk level — `jar:IsoGameCharacter.setMaxWeightBase @2 L3864`, `jar:IsoPlayer.setMaxWeightDelta @2 L8457`, `jar:jar-wide scan of setMaxWeightBase` and `of setMaxWeightDelta` (0 references each) · C · C-only.
30. The STRONG, WEAK, FEEBLE and STOUT traits reach `maxWeightDelta` only in the `IsoPlayer` constructor, so levelling Strength never refreshes it — `jar:IsoPlayer.<init> @1168–@1241 L624–L630`, `jar:jar-wide scan of IsoPlayer.maxWeightDelta` (writes in `<init>` and the setter only) · C · C-only.
31. A Lua write to `setMaxWeight` is overwritten on the next body-damage update, because the recompute calls the same setter — `jar:BodyDamage.UpdateStrength @325 L2113`, `jar:BodyDamage.Update @242 L2206` · C · C-only.
32. Strength level multiplies melee damage 0.80 to 1.25 across levels 1 to 10 and 0.75 at level 0, read live from the perk on every hit with no Lua step and no setter — `jar:IsoGameCharacter.getHittingMod @1–@104 L4544–L4575`, sole caller `jar:CombatManager.attackCollisionCheck @2054 L896` · C · C-only.
33. Strength level multiplies shove and stagger-back by the same 0.80 to 1.25 ladder — `jar:IsoGameCharacter.getShovingMod @1–@104 L4579–L4610`, callers `jar:IsoGameCharacter.processHitDamage @49 L6225` and `jar:HandWeapon.getStaggerBackTimeMod @47 L2439` · C · C-only.
34. Strength level multiplies carry capacity 0.90, 1.07, 1.24, 1.41, 1.58, 1.75, 1.92, 2.09, 2.26, 2.50 across levels 1 to 10, and 0.80 at level 0 — `jar:IsoGameCharacter.getWeightMod @1–@105 L4680–L4711` · C · C-only.
35. Fitness level multiplies weapon endurance cost 0.95 down to 0.75, endurance drain 0.80 down to 0.43, and endurance and muscle recovery 0.70 up to 1.60 — `jar:IsoGameCharacter.getFatigueMod @1–@104 L4428–L4459`, `jar:IsoGameCharacter.getPacingMod @1–@106 L4498–L4529`, `jar:IsoGameCharacter.getRecoveryMod @1–@110 L4614–L4647` · C · C-only.
36. `getRecoveryMod` already reads nutrition: lipids below −1500 multiply it by 0.2 and below −1000 by 0.5, and proteins do the same, after the weight-trait multipliers — `jar:IsoGameCharacter.getRecoveryMod @194–@289 L4664–L4673` · C · C-only.
37. Fitness level adds 0.02 per level to combat speed, which is then clamped to `[0.8, 1.6]` — `jar:IsoGameCharacter.calculateCombatSpeed @143–@157 L9878`, clamp `@237–@252 L9893–L9894` · C · C-only.
38. `IsoGameCharacter.updateFitness`, the method that writes `CharacterStat.FITNESS` from the perk level, is private and therefore not callable from Lua — `jar:IsoGameCharacter.updateFitness @0–@24 L10312` · C · C-only.
39. Strength reduces every combat muscle-strain term by the factor `(15 − StrengthLevel) / 10` — `jar:IsoGameCharacter.addCombatMuscleStrain @12–@39 L17163–L17165`, `@55–@82 L17172–L17174`, `@119–@199 L17185–L17193` · C · C-only.
40. Muscle strain is `BodyPart.stiffness`, a float per body part with public get, set and add accessors, and `IsoGameCharacter` offers seven public adders on top of it — `jar:BodyPart` member list and flags, `jar:IsoGameCharacter` member list and flags · C · C-only.
41. There is no Java skill-rust or XP-decay mechanism: the Strength and Fitness decay is shipped Lua keyed on player modData timers, subtracting one XP per 1200 timer units past 20000 and then calling `LoseLevel` — `jar:jar-wide grep SkillRust, skillRust, XPDecay, xpDecay, LoseXP, RemoveXP` (all absent), `lua:media/lua/server/XpSystem/XpUpdate.lua:299-331` · C · C-only.
42. `getLoosingXpValue()` answers −1 and `getLoosingXpTick()` answers 10 outside the debug cheat, which is what sets the decay rate — `jar:LuaManager$GlobalObject.getLoosingXpValue @27 L9747`, `getLoosingXpTick @48 L9758` · C · C-only.
43. The mapping from Strength and Fitness level to the WEAK/FEEBLE/STOUT/STRONG and UNFIT/OUT_OF_SHAPE/FIT/ATHLETIC traits is shipped Lua on the `LevelPerk` event, with level 5 getting no trait in either ladder — `lua:media/lua/server/XpSystem/XpUpdate.lua:325-361`, `:397` · C · C-only.
44. Exercise awards Strength XP from the arms and chest terms and Fitness XP from the legs and abs terms, through `GameServer.addXp` on a server and through nothing at all on a multiplayer client — `jar:Fitness.incStats @4–@250 L322–L356` · C · C-only.
45. `Fitness` regularity rises by `0.08 × ln(5)/ln(fitnessLvl/5 + 4)` per exercise repetition, clamped to `[0,100]`, and falls by 0.002 per ten-game-minute update for any exercise not done in the last in-game day, with no floor on the decay path — `jar:Fitness.incRegularity @0–@116 L220–L236`, `jar:Fitness.decreaseRegularity @46–@109 L143–L146`, `jar:Fitness.update @0–@49 L88–L99` · C · C-only.
46. `IsoPlayer.getFitness()` is public and `BodyDamage/Fitness` is in the exposer's class set, so a mod can drive regularity, stiffness and the current exercise from Lua, while `decreaseRegularity`, `increasePain` and `updateExeTimer` are private — `jar:IsoPlayer` and `jar:Fitness` member lists and flags, exposer entry at `@601` · C · C-only.
47. The engine models no lean body mass and no effective-strength concept — `jar:jar-wide grep leanBodyMass, LeanBodyMass, setEffectiveStrength, setStrengthMod, setHittingMod, setMeleeDamageMod, setKnockbackMod, setStrengthLevel, setFitnessLevel` (all absent) · C · C-only.
48. Neither knockback nor combat speed is writable from Lua: `knockbackAttackMod` is a public field with no accessor and `combatSpeedModifier` is a private field rewritten from clothing on every speed update — `jar:jar-wide grep getKnockbackAttackMod, setKnockbackMod` (absent), `jar:IsoGameCharacter.updateSpeedModifiers @12–@98 L10096–L10106` · C · C-only.
49. `setUnlimitedCarry` removes the weight limit but is contested: the save load, the role setter and the extra-info packet all write it — `jar:IsoGameCharacter.load @522 L5275`, `jar:IsoPlayer.setRole @117 L9404`, `jar:ExtraInfoPacket.processClient @102 L213`, `processServer @329 L288` · C · C-only.
50. `IsoGameCharacter.applyTraits` seeds both Strength and Fitness at level 5 before applying trait offsets, then levels up to the target and calls `setXPToLevel` — `jar:IsoGameCharacter.applyTraits @13–@36 L11627–L11628`, `@455–@479 L11681–L11683` · C · C-only.
51. `zombie/characters/ILuaGameCharacter` is an interface `IsoGameCharacter` implements and is absent from the exposer's class set, so it is a curated signal of the intended Lua API rather than the exposure gate — `jar:jar-wide grep ILuaGameCharacter` (six classes, none of them the exposer), `jar:LuaManager$Exposer.exposeAll() dump` (no `ILua` entry) · C · C-only.

## Not read

- `XP.AddXPHaloText(Perk, float)` — declared and public, body never dumped, so which of the six booleans it passes is unread.
- `XP.savePerk` / `loadPerk` — private, so the wire encoding of a perk id inside the XP blob is unread.
- The tail of `IsoDoor.WeaponHit`: the Strength ladder was read only to level 2 (`@129 L1191`) and the Fitness `tableswitch` at `@294 L1217` was not followed into its branches.
- The tails of `IsoGameCharacter.getClimbingFailChanceFloat` (past `@154`), `getClimbRopeSpeed`, `testDefense` (past `@140`), `attackFromWindowsLunge`, `handleLandingImpact`, `HandWeapon.checkJam`, `IsoAnimal.canBePicked`, `ISWorldObjectContextMenuLogic.createMenuEntries` and the three climb states — each was confirmed as a Strength or Fitness reader at a named offset, but the arithmetic around that read was not dumped in full. The weight-trait halves of several of them are already settled at [body-and-weight#weight-traits](../../facts/body-and-weight.md#weight-traits).
- `Fitness.reduceEndurance`, `incFutureStiffness`, `resetValues`, `save`, `load`, `init`, `initRegularityMapProfession` and the `Fitness$FitnessExercise` shape (`stiffnessInc`, `xpModifier`, `metabolics`) — named but not dumped.
- `IsoPlayer.updateEndurance` — five `getRecoveryMod` and two `getPacingMod` call sites were located but the surrounding formula was not dumped; the weight-trait terms in it are already `#0541`.
- `AntiCheatXPUpdate.getMaxPerkXpBoostMultiplier` and the `AntiCheat` enum's `<clinit>` — so which server option enables the XP anticheat, and whether its action defaults to log, kick or ban, is unread.
- Whether `SyncPlayerFields` flag 32 carries the `Fitness` object or only some of its fields — `GameServer.sendSyncPlayerFields` was dumped, the packet's own write was not.
- The 32-entry `LevelUpLevels` table was read only to its sixth element, and nothing was read about who consumes `XP.level` / `XP.lastlevel` / `XP.totalXp`.
- `IsoGameCharacter.getLevelUpMultiplier` / `setLevelUpMultiplier` were listed but their effect on `getXpForLevel(int)` (which multiplies by the field) was not traced to a caller.
- Everything about behaviour under a live session: whether `OnPlayerMove` fires on a dedicated server (which decides whether the Lua XP table runs there at all), the real cadence of the 1000 ms `PlayerXp` push against a client read, whether a Lua `setPerkLevelDebug` on the server survives the next push, and whether the exposed-but-uncurated setters (`setMaxWeightBase`, `setMaxWeightDelta`, `level0`) actually resolve under Kahlua. Each is a harness question, not a jar question.
