# Wave 2 — jar and Lua: the training signals the engine emits

Build `42.20.4` · jar `b0bbce05d5` · read 2026-09-27 · scope: every engine signal a dedicated server can read to compute a per-player training dose (exercise, melee, running, load, climbing, timed actions), plus what the server sees of client-granted XP.

## Summary for the design

The engine already carries most of the training model this mod wants, and the biggest find is that it is carried on the **server** side of a dedicated session rather than on the client. `Metabolics` is a 24-value MET enum with real exercise-science numbers — Walking5kmh 3.1, Running10kmh 6.9, Running15kmh 9.5, Fitness 6.0, FitnessHeavy 9.0, ForestryAxe 8.0, DiggingSpade 5.5 — and `Thermoregulator.updateMetabolicRate` classifies every player into one of them each tick, reading sprinting, running, sneaking, walking, the weapon being swung, and whether an exercise is in progress; the mod can read the result with one call, `getBodyDamage():getThermoregulator():getMetabolicRate()`, on a class the exposer registers. That makes an aerobic dose a sampling problem rather than a modelling problem.

Fitness exercise is server-authoritative in multiplayer, which is the opposite of the vanilla XP picture the earlier reading established. `Fitness.incStats` grants Strength and Fitness XP through `GameServer.addXp` when `GameServer.server` is set, through `XP.AddXP` in single player, and **grants nothing at all on a multiplayer client**; the rep itself is driven by `StatePacket.processServer` calling `exerciseRepeat()` when a client's state packet says the player is in `FitnessState`, and by `ISFitnessAction:animEvent`'s `isServer()` arm. `Fitness.update()` is likewise ungated at its call site in `IsoPlayer.updateInternal2` — no `isLocal()` test, and unlike `Nutrition.update` it is not behind `SystemDisabler.doCharacterStats` — so regularity decay, the 72-tick soreness countdown and `increasePain` all tick server-side, once per ten in-game minutes.

The exercise mechanics are fully legible and mostly reusable. Regularity rises `0.08 × ln(5)/ln(fitnessLvl/5 + 4)` per rep and decays `0.002` per ten-minute tick once a full in-game day has passed since that exercise was last done — `0.288` per in-game day against roughly `0.08` per rep, so vanilla regularity is a slow, forgiving signal. The XP per rep is `+4` Strength per `arms`, `+2` per `chest`, `+4` Fitness per `legs`, `+2` per `abs`, times the exercise's `xpMod`, truncated to an int on the server; the level-scaling branch `1 + (level−5)/10` uses integer division and is a no-op below level 15, which is almost certainly a vanilla bug the mod should not copy. The whole exercise table is a plain Lua global, `FitnessExercises.exercisesType`, that the mod can extend before `Fitness.init()` runs.

Combat and running reach XP entirely through Lua, and both triggers are side-split rather than side-agnostic. `OnWeaponHitXp` fires from `CombatManager.attackCollisionCheck` in single player only and from `WeaponHit.process` on the dedicated server only; `OnPlayerMove` fires from `IsoPlayer.updateInternal2` in single player only and from `IsoPlayer.updateRemotePlayer` on the dedicated server only, which means a multiplayer client never fires it for its own player. So a server-side mod can hook both events directly and see every swing and every move tick, with `getLastHitCount()` giving the swing's multi-hit count and `currentSpeed` giving a 0/0.5/1.0/1.5 speed class the server sets from the movement packet.

For observability of client-granted XP the answer is blunt: **the server sees the totals, not the grant.** `SyncXp` sends `PacketTypes.PlayerXp`, whose `parse` deserialises the client's whole `XP` object straight into the server's copy with `XP.load` and whose `processServer` only relays to the other clients — so neither the `AddXP` nor the `LevelPerk` event fires on the server for a synced grant. Server-side grants through `GameServer.addXp` do fire both, `AddXP` carrying `(character, perk, amount)` and `LevelPerk` carrying `(character, perk, level, true)`, so the level is available. A day's delta per perk is therefore a snapshot-and-difference of `getXp():getXP(perk)` in player modData, with two traps: a `SyncXp` can move the snapshot without any training, and vanilla skill rust subtracts 1 XP at a time after roughly 13.9 idle in-game days.

What is absent is exactly what a training model needs and must therefore own itself: no distance-run counter, no running-time or sprinting-time accumulator, no step count, no per-day XP, no training-load concept, and no lean-mass, fat-mass or aerobic-capacity field anywhere in the jar — twenty-six jar-wide greps, all clear. `runningTime` exists but resets the moment the player stops, so it is a consecutive-movement timer, not a total. The mod therefore samples each minute and counts on events, and the engine's own `Nutrition.updateCalories` is the template worth copying — including its warning, that the movement branches overwrite the timed-action `caloriesModifier`, so vanilla bills chopping-while-walking as walking.

Two practical cautions for the implementation. `ISTimedActionQueue` is a client-only file, so the server reads the action queue through `player:getCharacterActions()` instead; and `BaseAction` is not in the exposer's class set, so the action's `caloriesModifier` has to come off `LuaTimedActionNew:getTable()` rather than as a field. The anti-cheat bound is `1000 × multiplier × boost` per perk between checks, with Fast Learner explicitly excluded from widening Strength and Fitness — comfortable headroom for any sane dose-to-XP rate, and irrelevant if the mod keeps its own stat in modData. The one gap that could matter is that the anti-cheat's check interval was not read, so the denominator of that bound is unknown.

## A. `zombie/characters/BodyDamage/Fitness` in full

### A.1 Fields (17, all private; flags read with a scratch constant-pool parser)

| member | type | flags | exposed? | side | cite |
|---|---|---|---|---|---|
| `parent` | `IsoGameCharacter` | private | no (via `getParent()`) | both | `Fitness` field table |
| `regularityMap` | `HashMap<String,Float>` | private | via `getRegularityMap`/`setRegularityMap` | both | `Fitness.getRegularity @0 L535` |
| `fitnessLvl` | `int` | private | no | both | `Fitness.exerciseRepeat @0 L191` |
| `strLvl` | `int` | private | no | both | `Fitness.exerciseRepeat @14 L192` |
| `stiffnessTimerMap` | `HashMap<String,Integer>` | private final | via `getCurrentExeStiffnessTimer` | both | `Fitness.update @50 L102` |
| `stiffnessIncMap` | `HashMap<String,Float>` | private final | via `getCurrentExeStiffnessInc` | both | `Fitness.update @214 L121` |
| `bodypartToIncStiffness` | `ArrayList<String>` | private final | via `onGoingStiffness` | both | `Fitness.onGoingStiffness @0 L482` |
| `exercises` | `HashMap<String,FitnessExercise>` | private final | no | both | `Fitness.init @1 L565` |
| `exeTimer` | `HashMap<String,Long>` | private final | no | both | `Fitness.updateExeTimer @0 L206` |
| `lastUpdate` | `int` | private | no | both | `Fitness.update @11 L89` |
| `currentExe` | `Fitness$FitnessExercise` | private | via `getCurrentExe` | both | `Fitness.setCurrentExercise @12 L182` |
| `HOURS_FOR_STIFFNESS` | `int` = 72 | private static final | no | — | `Fitness.incFutureStiffness @93 L292` |
| `BASE_STIFFNESS_INC` | `float` = 0.5 | private static final | no | — | `Fitness.incFutureStiffness @43 L287` |
| `BASE_ENDURANCE_RED` | `float` = 0.015 | private static final | no | — | `Fitness.reduceEndurance @0 L245` |
| `BASE_REGULARITY_INC` | `float` = 0.08 | private static final | no | — | `Fitness.incRegularity @0 L220` |
| `BASE_REGULARITY_DEC` | `float` = 0.002 | private static final | no | — | `Fitness.decreaseRegularity @93 L145` |
| `BASE_PAIN_INC` | `float` = 2.5 | private static final | no | — | `Fitness.increasePain @48 L155` |

The class is in the exposer's class set: a jar grep for `BodyDamage/Fitness` returns `zombie/Lua/LuaManager$Exposer.class` among its eight hits, and `IsoPlayer.getFitness()` is called from six shipped Lua files, so every `public` member below is a door for a mod.

### A.2 `FitnessExercise` (inner class, built from a Lua table)

`Fitness.init()` reads the Kahlua global `FitnessExercises`, takes its `exercisesType` sub-table and builds one `FitnessExercise` per key (`Fitness.init @11–@117 L569–L579`); it returns early if `exercises` is already non-empty (`@0–@10 L565–L566`), so `init()` is idempotent and safe for a mod to call. The constructor reads four keys off the table (`Fitness$FitnessExercise.<init> @9–@78 L67–L73`): `type` (string), `metabolics` (a `Metabolics` object), `stiffness` (a comma-separated string, split into an `ArrayList`), and `xpMod` (float, defaulting to `1` and only overridden when `> 0`). All four fields are package-private with no getters, so a mod reads them only through `getCurrentExe()` returning the object — the fields themselves are not accessible from Lua.

The shipped table is `media/lua/shared/Definitions/FitnessExercises.lua` (65 lines); a mod can add rows to it before the first `init()`.

| exercise | `stiffness` | `metabolics` | `xpMod` | rep period (ms) | Str XP/rep (derived) | Fit XP/rep (derived) |
|---|---|---|---|---|---|---|
| `squats` | `legs` | `Fitness` | 1.0 | 3000 | 0 | 4 |
| `pushups` | `arms,chest` | `Fitness` | 1.0 | 1300 | 6 | 0 |
| `situp` | `abs` | `Fitness` | 1.0 | 1300 | 0 | 2 |
| `burpees` | `legs,arms,chest` | `FitnessHeavy` | 0.8 | 2400 | 4 (4.8 → `(int)`) | 3 (3.2 → `(int)`) |
| `barbellcurl` | `arms,chest` | `FitnessHeavy` | 1.2 | 2200 | 7 (7.2 → `(int)`) | 0 |
| `dumbbellpress` | `arms` | `FitnessHeavy` | 1.8 | 1500 | 7 (7.2 → `(int)`) | 0 |
| `bicepscurl` | `arms` | `FitnessHeavy` | 1.8 | 1900 | 7 (7.2 → `(int)`) | 0 |

The rep periods come from `ISFitnessAction:serverStart` (`media/lua/shared/TimedActions/ISFitnessAction.lua:132-149`), which arms `emulateAnimEvent(self.netAction, period, "ActiveAnimLooped", nil)`. The XP columns are derived from `incStats` (A.4) and the table above, not read off a dump.

### A.3 Public methods and their Lua exposure

| member | signature | flags | exposed? | side | cite |
|---|---|---|---|---|---|
| `<init>` | `(IsoGameCharacter)V` | public | — | both | called from both `IsoPlayer.<init>` overloads |
| `update` | `()V` | public | yes | both, ungated | `IsoPlayer.updateInternal2 @405–@409 L2310` |
| `decreaseRegularity` | `()V` | **private** | no | both | `Fitness.update @46 L99` |
| `increasePain` | `(String)V` | **private** | no | both | `Fitness.update @252 L126` |
| `setCurrentExercise` | `(String)V` | public | yes | both | `Fitness.setCurrentExercise @0–@15 L182` |
| `exerciseRepeat` | `()V` | public | yes | server drives it in MP | `Fitness.exerciseRepeat @0–@77 L191–L202` |
| `updateExeTimer` | `()V` | **private** | no | both | `Fitness.updateExeTimer @0 L206` |
| `incRegularity` | `()V` | public | yes | both | `Fitness.incRegularity @0–@116 L220–L236` |
| `reduceEndurance` | `()V` | public | yes | both | `Fitness.reduceEndurance @0–@185 L245–L269` |
| `incFutureStiffness` | `()V` | public | yes | both | `Fitness.incFutureStiffness @0– L281–L301` |
| `incStats` | `()V` | public | yes | side-branched | `Fitness.incStats @0–@251 L320–L358` |
| `resetValues` | `()V` | public | yes | both | `Fitness.resetValues @0–@21 L364–L367` |
| `removeStiffnessValue` | `(String)V` | public | yes | called from client and server Lua | `ISHealthPanel.lua:278`, `ClientCommands.lua:547` |
| `save` | `(ByteBuffer)V` | public | yes | writer | `SyncPlayerFieldsPacket.writeParam` |
| `load` | `(ByteBuffer,int)V` | public | yes | reader | `SyncPlayerFieldsPacket.parseParam` |
| `onGoingStiffness` | `()Z` | public | yes | both | `Fitness.onGoingStiffness @0–@15 L482` |
| `getCurrentExeStiffnessTimer` | `(String)I` | public | yes | both | member list + field table |
| `getCurrentExe` | `()FitnessExercise` | public | yes | both | `Thermoregulator.updateMetabolicRate` calls it |
| `getCurrentExeStiffnessInc` | `(String)F` | public | yes | both | member list |
| `getParent` / `setParent` | `()IsoGameCharacter` / `(IsoGameCharacter)V` | public | yes | both | member list |
| `getRegularity` | `(String)F` | public | yes | both | `Fitness.getRegularity @0–@25 L535–L540` |
| `getRegularityMap` / `setRegularityMap` | `()HashMap` / `(HashMap)V` | public | yes | both | member list |
| `init` | `()V` | public | yes | both | `Fitness.init @0–@124 L565–L581` |
| `initRegularityMapProfession` | `()V` | public | yes | both | `Fitness.initRegularityMapProfession @0–L592+` |

`getRegularity(type)` returns `0` for an absent key rather than throwing (`@12–@20 L536–L537`), so a mod may read any of the seven exercise names on any player without guarding.

### A.4 How regularity, stiffness, endurance and XP move

**`update()` — the cadence.** `Fitness.update` computes `GameTime.getInstance().getMinutes() / 10` and compares it with the `lastUpdate` field; if the bucket has not changed it returns (`@0–@31 L88–L93`). So the whole body runs **once per 10 in-game minutes**, per player, driven off `IsoPlayer.updateInternal2`. It then calls `decreaseRegularity()`, decrements every `stiffnessTimerMap` entry by 1 and, at zero, moves that body part into `bodypartToIncStiffness` (`@49–@187 L102–L114`); for each part in that list it calls `increasePain(part)` and decrements `stiffnessIncMap[part]` by 1, removing the part when the value reaches 0 (`@187–@311 L119–L135`).

**Regularity decay.** `decreaseRegularity` walks `regularityMap`; for a type that has an `exeTimer` entry, if `GameTime.getCalender().getTimeInMillis() - exeTimer[type] > 86_400_000` (one in-game day of ms) it subtracts `0.002` (`@46–@109 L143–L146`). So regularity is flat for the first in-game day after an exercise and then bleeds `0.002` per 10 in-game minutes — `0.288` per in-game day (derived). A type with no `exeTimer` entry never decays.

**Regularity rise.** `incRegularity` computes `f = 0.08 * ln(5) / ln(fitnessLvl/5 + 4)` and adds it to `regularityMap[currentExe.type]`, clamped to `[0, 100]` (`@0–@116 L220–L236`). At Fitness 5 that is exactly `0.08`; at Fitness 0, `0.0929`; at Fitness 10, `0.0719` (derived) — a higher Fitness level earns regularity more slowly.

**`exerciseRepeat()` — one rep.** It refreshes `fitnessLvl` and `strLvl` from `getPerkLevel(Perks.Fitness)` and `getPerkLevel(Perks.Strength)` (`@0–@25 L191–L192`), then calls, in order, `incRegularity`, `reduceEndurance`, `incFutureStiffness`, `incStats`, `updateExeTimer` (`@28–@45 L194–L198`); finally, if `GameServer.server` is set and the parent is an `IsoPlayer`, it calls `GameServer.sendSyncPlayerFields(player, 32)` (`@48–@74 L199–L200`).

**`updateExeTimer()`** stamps `exeTimer[currentExe.type] = GameTime.getCalender().getTimeInMillis()` (`@0–@26 L206`), which is what resets the one-day decay grace.

**`reduceEndurance()`.** Base `0.015`, scaled by `ln(regularity/50 + 50) / ln(51)` — so a regularity of 0 gives exactly the base and higher regularity makes a rep *more* costly (`@0–@65 L245–L254`); `×1.3` when `currentExe.metabolics == Metabolics.FitnessHeavy` (`@66–@84 L256–L257`); then `× (1 + getMoodles().getMoodleLevel(MoodleType.HEAVY_LOAD) / 3)` with integer division, so the multiplier is 1 below moodle level 3 and 2 at level 3 or 4 (`@85–@105 L260`). The stat write is gated `GameClient.client == null` — i.e. it happens on a dedicated **server** and in single player, never on a multiplayer client (`@106–@126 L262–L263`). When `GameServer.server` is set it then sends `PacketTypes.SyncPlayerStats` with `SyncPlayerStatsPacket.getBitMaskForStat(CharacterStat.ENDURANCE)` (`@127–@185 L266–L269`).

**`incFutureStiffness()`.** For each part in `currentExe.stiffnessInc`: if the part is not already in `stiffnessTimerMap` nor in `bodypartToIncStiffness`, it seeds `stiffnessTimerMap[part] = 72` (`HOURS_FOR_STIFFNESS`, so 72 of the 10-minute update ticks = 12 in-game hours before the soreness lands — derived) (`@63–@101 L291–L292`); the per-rep increment starts at `0.5` and is scaled by `(120 - regularity) / 170` (`@127–@141 L299`), so a regularity of 120+ would zero it and a regularity of 0 gives `0.5 × 120/170 ≈ 0.353`.

**`increasePain(part)`** adds `2.5` to `BodyPart.getStiffness()` on every part in the named group — `arms` = `ForeArm_L` through `UpperArm_R` inclusive, `legs` = `UpperLeg_L` through `LowerLeg_R` inclusive, `chest` = `Torso_Upper` (`@0–@154 L152–L166`).

**`incStats()` — where the XP is.** `strXp` accumulates `+4` per `arms` and `+2` per `chest` in `currentExe.stiffnessInc`; `fitXp` accumulates `+4` per `legs` and `+2` per `abs` (`@4–@102 L322–L334`). Then `if (strLvl > 5) strXp *= 1 + (strLvl - 5)/10` and the same for `fitnessLvl` on `fitXp` (`@102–@147 L339–L343`) — both divisions are **integer** `idiv`, so for levels 6–10 the quotient is 0 and the multiplier is exactly 1.0; the branch is a no-op below Strength/Fitness 15 (derived). Both totals are then multiplied by `currentExe.xpModifier` (`@148–@167 L346–L347`).

The side split is the important part (`@168–@251 L349–L356`):

| condition | what happens | cite |
|---|---|---|
| `GameServer.server != 0` and parent is `IsoPlayer` | `GameServer.addXp(player, Perks.Strength, (float)(int)strXp)` then the same for `Perks.Fitness` — **truncated to int** | `incStats @168–@214 L349–L352` |
| `GameServer.server == 0` and `GameClient.client == null` (single player) | `parent.getXp().AddXP(Perks.Strength, strXp)` and `...Fitness, fitXp` — **not truncated** | `incStats @217–@251 L354–L356` |
| `GameServer.server == 0` and `GameClient.client != null` (MP client) | **nothing** — falls straight to `return` | `incStats @217 @220 ifne 251` |

So exercise XP in multiplayer is granted **server-side only**, through `GameServer.addXp` — the opposite of the vanilla melee/running path in section B.

### A.5 Which side runs `Fitness.update` — and which side runs a rep

`Fitness.update()` is called from `IsoPlayer.updateInternal2()` at `@405–@409 L2310`. Two things about that call site matter:

- It is **not** under `SystemDisabler.doCharacterStats`, unlike `Nutrition.update` immediately above it at `@392–@402 L2306–L2307`. Disabling character stats stops nutrition and leaves fitness ticking.
- The only gate above it in the method is `isAnimal()` at `@325–@329 L2291` (`ifne 416` jumps past both the nutrition and the fitness update). There is no `isLocal()` gate on the fitness call — the `isLocal()` test at `@355–@359 L2302` guards only the aiming reticle and rejoins at `@392`, before the fitness call.

`updateInternal2` is reached from `IsoPlayer.updateInternal1` at `@50–@51 L2200`; the `GameClient.client` branch that diverts to `updateRemotePlayer` and returns is inside the **`isAnimal()`** arm (`updateInternal1 @0–@49 L2189–L2197`), so a player character does not take it. **So `Fitness` does *not* follow the `BodyDamage.Update` local-player gate**: on a dedicated server, `Fitness.update()` ticks for every connected player's server-side `IsoPlayer`, meaning regularity decay, the stiffness countdown and `increasePain` all run server-side. Bound: the call site is ungated in the bytecode; whether the server's cell loop reaches `updateInternal1` for every connected player each tick is a run question.

A **rep** is driven from the network, not from the server's own clock. `StatePacket.processServer` holds the only Java call to `exerciseRepeat`: when `stage == State$Stage.Execute`, the packet's state is `FitnessState.instance()`, the character is an `IsoPlayer`, and that player `isCurrentState(FitnessState.instance())`, it calls `player.getFitness().exerciseRepeat()` (`StatePacket.processServer @414–@474 L180–L183`). The Lua side agrees: `ISFitnessAction:animEvent` runs `exeLooped()` — which is `self.fitness:exerciseRepeat()` — only when `isServer()` or single player (`ISFitnessAction.lua:157-168`, `:121-125`).

### A.6 The driving Lua

| file | what it does | what it sends | events |
|---|---|---|---|
| `media/lua/shared/TimedActions/ISFitnessAction.lua` (225 lines) | the timed action; `new()` sets `caloriesModifier = 3`, `endMS = now + timeToExe*60000` game-ms, calls `fitness:setCurrentExercise(exeDataType)` (`:203-225`) | `serverStart` calls `fitness:init()`, `setCurrentExercise`, then `emulateAnimEvent(netAction, period, "ActiveAnimLooped", nil)` (`:127-150`); `complete`/`serverStop` use `emulateAnimEventOnce(netAction, 100, nil, "FitnessFinished=TRUE")` | `start()` fires `reportEvent("EventFitness")` and `reportEvent("EventUpdateFitness")`; the client arm of `animEvent` fires `reportEvent("EventUpdateFitness")` every loop (`:188`) |
| | `update()` sets `character:setMetabolicTarget(self.exeData.metabolics)` **every frame** (`:51`) and force-stops on climbing, aiming, sitting, any movement key, `ENDURANCE` moodle > 2, or `getGameTime():getCalender():getTimeInMillis() > endMS` (`:32-52`) | sets animation variables `ExerciseType`, `ExerciseStarted`, `ExerciseEnded`, `ExerciseHand`, `FitnessFinished` | |
| `media/lua/client/ISUI/ISFitnessUI.lua` (354 lines) | the panel; `enduranceLevelThreshold = 2` (`:3`); constructor calls `player:getFitness():init()` (`:352`) | queues `ISFitnessAction:new(player, selectedExe, tonumber(exeTime), exeData, exeData.type)` (`:280`) — the exercise duration is a UI text field in in-game minutes | reads `getCurrentRegularity()` = `getFitness():getRegularity(selectedExe) / 150` and draws it `× 1.5` (`:188-194`); inspects `ISTimedActionQueue`'s `queue[1].Type == "ISFitnessAction"` (`:180`, `:212`, `:293`) |
| `media/lua/server/XpSystem/XpUpdate.lua:350` | `xpUpdate.onNewGame` calls `playerObj:getFitness():init()` | — | `Events.OnNewGame` |
| `media/lua/server/ClientCommands.lua:547,558,591` and `media/lua/client/XpSystem/ISUI/ISHealthPanel.lua:278,289,322` | stretching clears soreness: `getFitness():removeStiffnessValue(BodyPartType.ToString(...))` | the client path is mirrored by a `ClientCommands` handler, so soreness clearing is a bus round trip in MP | — |

There is no `sendClientCommand` in `ISFitnessUI.lua` and none in `ISFitnessAction.lua`: the exercise reaches the server entirely as the timed action's own net-action plus `StatePacket`, and the rep loop is driven by `emulateAnimEvent` on the server's copy of the action.

## B. Combat and running as training

### B.1 Every `Perks.Strength` / `Perks.Fitness` XP grant in the jar

A jar grep for `AddXP` returns 22 classes; scanning each for an `IsoGameCharacter$XP.AddXP` reference narrows the Java-side grant set to six methods plus `Fitness.incStats`. Scanning the classes that hold `PerkFactory$Perks` (62 classes, cap 200, no truncation) for a Strength or Fitness reference turns up the rest as **reads** (`getPerkLevel`), not grants: the climb states, the window states, `IsoMovingObject.separate`, `IsoDoor.WeaponHit`, `IsoGameCharacter.getHittingMod`/`getShovingMod`/`getWeightMod`/`getPacingMod`/`getFatigueMod`/`getRecoveryMod`/`calculateCombatSpeed`/`handleLandingImpact` and `CombatManager.attackCollisionCheck` all only read the level.

| where | perk | amount | condition | side | cite |
|---|---|---|---|---|---|
| `IsoGameCharacter.hitConsequences` | `Strength` | `2.0` | victim survived, weapon not ranged, `weapon.isKnockBackOnNoDeath()`, victim's `xp` non-null | `GameServer.addXp` on the server; `xp.AddXP` when `GameClient.client == null`; **nothing on an MP client** | `IsoGameCharacter.hitConsequences @103–@161 L6310–L6317` |
| `IsoPlayer.updateInternal2` | `Fitness` | `1.0` | `GameClient.client == 0`; `stats.get(ENDURANCE) < stats.getEnduranceDangerWarning()`; `Rand.Next((int)(300 * GameTime.getInvMultiplier())) == 0` | `GameServer.addXp` on the server, else `xp.AddXP`; never on an MP client | `IsoPlayer.updateInternal2 @727–@796 L2362–L2368` |
| `CombatManager.processMaintenanceCheck` | `Maintenance` | (read at `@238`/`@253`) | on a weapon hit | server/`AddXP` split at `@228` | `CombatManager.processMaintenanceCheck @228–@258 L551` |
| `Fitness.incStats` | `Strength`, `Fitness` | per A.2 table | one exercise rep | server-only in MP | `Fitness.incStats @168–@251 L349–L356` |
| `IsoGameCharacter.doDeathSplatterAndSounds`, `IsoPlayer.addMechanicsItem` | not Strength/Fitness | — | — | — | `AddXP` scan |

So **no Java method grants Strength or Fitness XP for a melee swing**. The swing XP is entirely in Lua.

### B.2 Melee and stomps: the Lua path and which side fires it

`media/lua/server/XpSystem/XpUpdate.lua` is the only shipped grant site for swing XP, on the `OnWeaponHitXp` event (`:48-106`, registered at `:385`):

| line | perk | amount | condition |
|---|---|---|---|
| `:70-72` | `Fitness` | `1` | `owner:getStats():get(CharacterStat.ENDURANCE) > owner:getStats():getEnduranceWarning()` and `not weapon:isRanged()` |
| `:74-76` | `Strength` | `owner:getLastHitCount()` | `not weapon:isRanged()` and `getLastHitCount() > 0` |
| `:86-105` | weapon perk (`Axe`/`Blunt`/`Spear`/`LongBlade`/`SmallBlade`/`SmallBlunt`) | `min(damage * 0.9, 3)` | `hitCount > 0`, non-ranged, matching `WeaponCategory` |
| `:41-45` (`OnWeaponHitTree`) | `Strength` | `2` | weapon type is not `"BareHands"` |

Neither Fitness nor Strength here is randomised — every qualifying swing grants. `getLastHitCount()` is a plain field read (`IsoGameCharacter.getLastHitCount @0–@4 L10479`) and is set in `CombatManager.attackCollisionCheck @365` via `setLastHitCount`, so a multi-zombie sweep grants Strength equal to the number of targets in that swing.

**The side gate is in the trigger, not in the Lua.** There are exactly two `OnWeaponHitXp` triggers in the jar (grep `OnWeaponHitXp` → `CombatManager`, `LuaEventManager`, `WeaponHit`):

| trigger | gate | side | cite |
|---|---|---|---|
| `CombatManager.attackCollisionCheck` | `GameClient.client == 0` **and** `GameServer.server == 0` | single player only | `CombatManager.attackCollisionCheck @3414–@3459 L1095–L1097` |
| `WeaponHit.process` | `GameServer.server != 0` | dedicated server only | `WeaponHit.process @322–@344 L107–L108` |

Both pass `hitCount` as a literal `Integer.valueOf(1)`. So on a dedicated server the melee XP chain is: client swings → hit packet → `WeaponHit.process` on the server → `OnWeaponHitXp` server-side → `xpUpdate.onWeaponHitXp` → `addXp(...)` → `GameServer.addXp`. A **server-side mod can hook `OnWeaponHitXp` directly** and see every swing with the attacker, the weapon, the victim and the damage. `WeaponHit.process` also calls `CombatManager.processMaintenanceCheck` right after (`@347–@353 L109`), which is where `OnWeaponHitTree` fires.

A **stomp** is the `isAimAtFloor() && isDoShove()` branch of `attackCollisionCheck`, whose damage is `Rand.Next(0.7f, 1.0f) + 0.2f * getPerkLevel(Perks.Strength)`, then modified by worn `SHOES` (`@2585–@2650 L971–L975`). It grants no Strength XP of its own — it reaches XP only through the same `OnWeaponHitXp` path, and only through `getLastHitCount()`.

Swing effort is separately accounted as endurance: `CombatManager.applyMeleeEnduranceLoss` returns early unless `weapon.isMelee()` and `weapon.isUseEndurance()`, then computes `weapon.getWeight() * ENDURANCE_LOSS_BASE_SCALE * weapon.getFatigueMod(chr) * chr.getFatigueMod() * weapon.getEnduranceMod() * ENDURANCE_LOSS_WEIGHT_MODIFIER + twoHandPenalty`, all `× ENDURANCE_LOSS_FINAL_MULTIPLIER`, where the two-hand penalty is `weight / ENDURANCE_LOSS_TWO_HANDED_PENALTY_DIVISOR / ENDURANCE_LOSS_TWO_HANDED_PENALTY_SCALE` and applies only when the weapon is two-handed but not held in both hands (`applyMeleeEnduranceLoss @0–@138 L3764–L3774`). The constants are `CombatConfigKey` entries, not literals.

### B.3 Running and load

The shipped running grants are `xpUpdate.onPlayerMove` (`XpUpdate.lua:9-38`, registered at `:383`):

| line | perk | amount | condition |
|---|---|---|---|
| `:16-18` | `Fitness` | `1` | `(IsRunning() or isSprinting())` **and** `stats:get(CharacterStat.ENDURANCE) > stats:getEnduranceWarning()`, **and** `randXp()` |
| `:19-21` | `Sprinting` | `1` | same condition, a second independent `randXp()` roll |
| `:27-29` | `Nimble` | `1` | `isAiming()`, `randXp()`, position changed since the last call, no vehicle |
| `:31-35` | `Strength` | `2` | `getInventoryWeight() > getMaxWeight() * 0.5`, and `randXp()` — note this does **not** require moving fast, only that the move event fired |

`xpUpdate.randXp()` is `ZombRand(100 * GameTime.getInstance():getInvMultiplier()) == 0` when `isServer()` and `ZombRand(700 * ...)` otherwise (`:167-173`). Since `XpUpdate.lua` lives under `media/lua/server/`, the 1/100 branch is the dedicated server and the 1/700 branch is single player; an MP client never loads the file.

**`OnPlayerMove` does fire on a dedicated server.** There are two triggers (grep `OnPlayerMove` → `LuaEventManager`, `IsoPlayer`):

| trigger | gate | side | cite |
|---|---|---|---|
| `IsoPlayer.updateInternal2` | `GameClient.client == 0` **and** `GameServer.server == 0`, then `isJustMoved() && !isNpc()` | single player only | `IsoPlayer.updateInternal2 @840–@856 L2384–L2385` |
| `IsoPlayer.updateRemotePlayer` | `this.remote` set; inside the `GameServer.server != 0` arm; then `isJustMoved() && !isNpc()` | dedicated server only | `IsoPlayer.updateRemotePlayer @0–@8 L7352`, `@20–@23 L7360`, `@138–@156 L7386–L7387` |

So on an MP client `OnPlayerMove` never fires for the local player, and on the server it fires once per tick per remote player that moved. Note the server's chance per event is 7× the single-player chance, which partly compensates for the server's own tick rate.

### B.4 The anti-cheat bound on what a mod may grant

`AntiCheatXPUpdate.isPerkXpGrowthRateTooHigh(player, perk)` reads `player.getXp().getXP(perk)`, stores it through `NetworkPlayerAI.setXp(perk, value)` (which returns the **previous** stored value), takes the delta, and compares it with `1000.0 × getMaxPerkXpMultiplier(player, perk) × getMaxPerkXpBoostMultiplier(player, perk)`; over that, it logs `perk %s xp growth is too high: xp=%f max-xp=%f multiplier=%f boost=%f` on `DebugType.Multiplayer` and returns true (`isPerkXpGrowthRateTooHigh @0–@113 L65–L75`).

- `getMaxPerkXpMultiplier` = `max(1, XP.getMultiplier(perk), previously stored multiplier)`, then `× max(1, SandboxOptions.multipliersConfig.xpMultiplierGlobal)` when `xpMultiplierGlobalToggle` is on, else `× max(1, <sandbox option named for the perk>)` when one exists (`@0–@117 L48–L61`).
- `getMaxPerkXpBoostMultiplier` = a `tableswitch` on `max(XP.getPerkBoost(perk), stored boost)` giving `1.0`, `1.33`, `1.66` or `0.25`, then adjusted by the `FAST_LEARNER` trait for perks whose parent is **not** `Perks.PhysicalCategory` (`@0–@114 L24–L37`). Strength and Fitness sit under the physical category, so Fast Learner does not widen their band.
- `AntiCheatXPUpdate.update(connection)` walks `connection.players[]` and returns false on the first player that trips `isXpGrowthRateTooHigh` (`update @18–@63 L99–L105`); it short-circuits to true when the anti-cheat is disabled (`@6–@17 L95–L96`).

The practical bound for a mod: **between two anti-cheat checks on one connection, a single perk's total XP must not rise by more than 1000 × the multipliers.** The check interval itself is not in this method — it is whatever `AbstractAntiCheat.update`'s scheduler gives it, which is a run question.

## C. Activity time accounting a server-side minute pass can read

### C.1 The engine's own MET table — `zombie/characters/BodyDamage/Metabolics`

This is the single most useful thing in the jar for this design: the engine already carries a 24-value MET enum, and `Metabolics` **is** in the exposer's class set (a grep for `BodyDamage/Metabolics` returns `zombie/Lua/LuaManager$Exposer.class`). Values read off `Metabolics.<clinit> @0–@382 L7–L30`:

| constant | MET | constant | MET |
|---|---|---|---|
| `Sleeping` | 0.8 | `HeavyWork` | 6.0 |
| `SeatedResting` | 1.0 | `ForestryAxe` | 8.0 |
| `StandingAtRest` | 1.1 | `Walking2kmh` | 1.9 |
| `SedentaryActivity` | 1.2 | `Walking5kmh` | 3.1 |
| `Default` | 1.5 | `Running10kmh` | 6.9 |
| `DrivingCar` | 1.4 | `Running15kmh` | 9.5 |
| `LightDomestic` | 1.6 | `JumpFence` | 4.0 |
| `HeavyDomestic` | 2.0 | `ClimbRope` | 8.0 |
| `DefaultExercise` | 3.0 | `Fitness` | 6.0 |
| `UsingTools` | 2.5 | `FitnessHeavy` | 9.0 |
| `LightWork` | 3.2 | `MAX` | 10.3 |
| `MediumWork` | 3.9 | `DiggingSpade` | 5.5 |

Public accessors: `getMet()F`, `getWm2()F`, `getW()F`, `getBtuHr()F`, plus the statics `MetToWm2(F)F`, `MetToW(F)F`, `MetToBtuHr(F)F` — so the mod can convert a MET class to watts without writing its own constants.

**The engine already classifies the player into these every tick.** `Thermoregulator.updateMetabolicRate()` (called from `Thermoregulator.update() @49 L~`) starts at `Metabolics.Default`, then:

| condition | target | cite |
|---|---|---|
| `player.isAttacking()` — `tableswitch` on `WeaponType.getWeaponType(player)` | `MediumWork`, `HeavyWork`, `LightWork`, `UsingTools` or `Running15kmh` depending on weapon type | `updateMetabolicRate @17–@193 L771–L802` |
| `isPlayerMoving() && isSprinting()` | `Running15kmh` (9.5) | `@203–@220 L807–L808` |
| `isPlayerMoving() && isRunning()` | `Running10kmh` (6.9) | `@223–@240 L809–L810` |
| `isPlayerMoving() && isSneaking()` | `Walking2kmh` (1.9) | `@243–@260 L811–L812` |
| `currentSpeed > 0` (walking) | `Walking5kmh` (3.1) | `@263–@279 L813–L814` |
| `getFitness().getCurrentExe() != null` — **overrides everything above** | `Metabolics.Fitness` (6.0) | `@282–@299 L817–L818` |
| then blended with `clamp01(1 - stats.get(ENDURANCE)) * Metabolics.DefaultExercise.getMet()` | — | `@302–@320 L822` |

Read back with `getBodyDamage():getThermoregulator():getMetabolicRate()` (or `getMetabolicTarget()`, `getMetabolicRateReal()`); `BodyDamage.getThermoregulator()` is public and `Thermoregulator` is in the exposer's class set. Note the exercise override uses only the flat `Metabolics.Fitness` (6.0), **not** the per-exercise `metabolics` from the table — `FitnessHeavy` (9.0) reaches the thermoregulator only through `ISFitnessAction:update`'s per-frame `character:setMetabolicTarget(self.exeData.metabolics)` (`ISFitnessAction.lua:51`), which is a client-side timed-action call.

### C.2 Per-player state a server-side pass can read each minute

| signal | getter / flag | flags | exposed? | side | cite |
|---|---|---|---|---|---|
| speed class (0 / 0.5 / 1.0 / 1.5) | `IsoPlayer.currentSpeed` **public field, no getter** | public | field access, untested from Lua | **set server-side** from the network flags | `IsoPlayer.updateRemotePlayer @84–@137 L7374–L7383` |
| running / sprinting flags | `IsRunning()Z`, `isSprinting()Z`, `isPlayerMoving()Z`, `isJustMoved()Z` | public | yes (used in shipped Lua) | mirrored from the packet on the server | `XpUpdate.lua:14`, `updateRemotePlayer @91–@112` |
| consecutive-movement timer | `IsoPlayer.runningTime` **public field, no getter** | public | field access, untested | written only in `updateInternal2` | `IsoPlayer.updateInternal2 @169–@189 L2262–L2264` |
| endurance | `getStats():get(CharacterStat.ENDURANCE)`, `getEnduranceWarning()`, `getEnduranceDangerWarning()` | public | yes | server writes it (`updateEndurance`) | `XpUpdate.lua:14`, `IsoPlayer.updateEndurance @210–@242 L3468` |
| the derived fitness stat | `getStats():get(CharacterStat.FITNESS)` = `getPerkLevel(Perks.Fitness)/5 - 1` | public | yes | both | `IsoGameCharacter.updateFitness @0–@25 L10312–L10313` |
| carried load | `getInventoryWeight()F`, `getMaxWeight()I`, `getMaxWeightBase()I`, `getMaxWeightDelta()F` | public, `getInventoryWeight` on `ILuaGameCharacter` | yes | both | `XpUpdate.lua:31` |
| heavy-load moodle | `getMoodles():getMoodleLevel(MoodleType.HEAVY_LOAD)` (0–4) | public | yes | both | `Fitness.reduceEndurance @85–@105 L260`, `IsoPlayer.updateEndurance @249–@305 L3470–L3474` |
| climbing | `isClimbing()Z`, `isClimbingRope()Z`, `getClimbRopeTime()F`, `getClimbData()` | public | yes | both | `IsoGameCharacter` member list; `ISFitnessAction.lua:33` uses `isClimbing()` |
| vaulting / window climb | `isCurrentState(ClimbOverFenceState.instance())`, `...ClimbThroughWindowState.instance()` | public statics | yes | both | `Nutrition.updateCalories @46–@72 L93–L94` |
| swipe (melee) state | `isCurrentState(SwipeStatePlayer.instance())` | public static | yes | both | `Nutrition.updateCalories @33–@43 L93` |
| the timed-action queue | `getCharacterActions()Ljava/util/Stack;`, `hasTimedActions()Z` | public, on `ILuaGameCharacter` | yes | both | `Nutrition.updateCalories @6–@29 L89–L90` |
| the current action's calorie weight | `((BaseAction)getCharacterActions().get(0)).caloriesModifier` | **public field on `BaseAction`, which is NOT in the exposer's class set** | Lua-created actions are `LuaTimedActionNew`, which **is** exposed and offers `getTable()`; read `caloriesModifier` off that table instead | both | `Nutrition.updateCalories @15–@32 L90`; exposer greps |
| the current action's type name | `LuaTimedActionNew.getMetaType()` → the Lua metatable's `Type` string | public | yes | both | `LuaTimedActionNew.getMetaType @0–@39 L226–L229` |
| metabolic rate | `getBodyDamage():getThermoregulator():getMetabolicRate()` / `getMetabolicTarget()` / `getMetabolicRateReal()` | public | yes | both | `BodyDamage.getThermoregulator` member list |
| soreness | `getBodyDamage():getBodyPart(t):getStiffness()`, `getFitness():onGoingStiffness()`, `getCurrentExeStiffnessTimer/Inc(part)` | public | yes | both | § A.3 |
| exercise regularity | `getFitness():getRegularity(type)`, `getRegularityMap()` | public | yes | both | `Fitness.getRegularity @0–@25 L535` |
| XP totals per perk | `getXp():getXP(perk)`, `getPerkLevel(perk)` | public | yes | both | `XpUpdate.lua:311`, `:324` |
| zombie kills | `getZombieKills()`, `setZombieKills()` | public | yes | both | `IsoGameCharacter.hitConsequences @45–@52 L6290` |
| swing multi-hit | `getLastHitCount()I` (on `ILuaGameCharacterDamage`) | public | yes | server sees it via `WeaponHit.process` | `IsoGameCharacter.getLastHitCount @0–@4 L10479` |

`caloriesModifier` values in the shipped actions (from `media/lua/shared/TimedActions/` and the building/farming folders) run `0.5` (`ISReadABook`, `ISResearchRecipe`, `ISRestAction`), `1` (the `ISBaseTimedAction` default, `ISBaseTimedAction.lua:181`), `2` (`ISDismantleAction`), `3` (`ISFitnessAction`), `4` (`ISMultiStageBuild`, `ISPaintAction`, `ISHarvestPlantAction`, `ISShovelAction`, `ISFixAction`, `ISDryMyself`, …), `5` (`ISPlowAction`, `ISCleanBlood`, `ISFillGrave`) and `8` (`ISBuildAction`, `ISPlasterAction`, `ISShovelGround`, `ISChopTreeAction`, `ISBarricadeAction`, `ISDestroyStuffAction`, `ISPickAxeGroundCoverItem`, `ISLightFromKindle`). That is a ready-made effort scale for building, digging and chopping.

### C.3 The engine's own worked example of a minute-pass dose: `Nutrition.updateCalories`

`Nutrition.updateCalories()` is exactly the shape the training dose wants, and reading it saves inventing one (`Nutrition.updateCalories @0–@319 L88–L118`):

1. `mult = 1`; if `getCharacterActions()` is non-empty, `mult = getCharacterActions().get(0).caloriesModifier` (`@2–@32 L89–L90`).
2. If the player is in `SwipeStatePlayer`, `ClimbOverFenceState` or `ClimbThroughWindowState`, `mult = 8.0` — overriding the action modifier (`@33–@74 L93–L94`).
3. `energyMult = getBodyDamage().getThermoregulator().getEnergyMultiplier()` (`@77–@114 L99–L100`).
4. `weightRatio = getWeight() / 80.0` (`@115–@124 L104`).
5. Then one of five mutually exclusive branches, each `setCalories(getCalories() - rate × … × GameTime.getGameWorldSecondsSinceLastUpdate())`:

| branch | condition | rate | `mult` | `energyMult` used? | cite |
|---|---|---|---|---|---|
| running | `IsRunning() && isPlayerMoving()` | 0.13 | forced to **1.0** | no | `@125–@169 L106–L108` |
| sprinting | `isSprinting() && isPlayerMoving()` | 0.13 | forced to **1.3** | no | `@172–@217 L109–L111` |
| walking | `isPlayerMoving()` | 0.13 | forced to **0.6** | no | `@220–@255 L112–L114` |
| asleep | `isAsleep()` | 0.003 | kept from steps 1–2 | yes | `@258–@292 L115–L116` |
| idle | otherwise | 0.016 | kept from steps 1–2 | yes | `@295–@316 L118` |

The consequence a mod must know: **the three movement branches overwrite `mult`**, so a timed action's `caloriesModifier` and the `8.0` climb/swipe override only reach the calorie drain when the player is standing still. Chopping a tree while walking is billed as walking.

### C.4 What the server does and does not run

| method | side gate | cite |
|---|---|---|
| `IsoPlayer.updateEndurance` | returns for an animal and returns when `GameClient.client != 0` → runs on the dedicated server and in single player only | `IsoPlayer.updateEndurance @0–@13 L3427–L3428` |
| `IsoPlayer.updateMovementRates` | called only when `GameServer.server != 0` | `IsoPlayer.updateInternal2 @913–@920 L2402–L2403` |
| `IsoPlayer.updateRemotePlayer` | `remote` only; its body's first arm requires `GameServer.server != 0` | `updateRemotePlayer @0–@23 L7352–L7360` |
| `Fitness.update` | no side gate, not under `SystemDisabler.doCharacterStats` | `IsoPlayer.updateInternal2 @405–@409 L2310` |
| `Nutrition.update` | under `SystemDisabler.doCharacterStats` | `IsoPlayer.updateInternal2 @392–@402 L2306–L2307` |
| `Fitness.incStats` XP grant | `GameServer.addXp` server-side; nothing on an MP client | `Fitness.incStats @168–@251 L349–L356` |
| `Fitness.reduceEndurance` stat write | `GameClient.client == null` → server and SP | `Fitness.reduceEndurance @106–@126 L262–L263` |

Endurance drain detail worth reusing (`IsoPlayer.updateEndurance @40–@347 L3437–L3478`): sneaking multiplies by `1.5`; the running/sprinting/dragging-corpse branch takes `ZomboidGlobals.runningEnduranceReduce` (or `sprintingEnduranceReduce` when sprinting or dragging a corpse) `× base × 0.5 × asthmaMod × GameTime.getMultiplier() × sneakMod`, where `base = 1.4` (`2.9` `OVERWEIGHT`, `0.8` `ATHLETIC`) `× 2.3 × getPacingMod() × getHyperthermiaMod()` and `asthmaMod = 0.7` (`1.0` `ASTHMATIC`); a non-zero `HEAVY_LOAD` moodle multiplies it again by `1.5 / 1.9 / 2.3 / 2.8` by level. A **walking** player with `HEAVY_LOAD` above level 2 takes a second drain at `runningEnduranceReduce × (base×3.0×pacing×hyperthermia) × 0.5 × asthma × sneak × GameTime.getMultiplier() × loadMult / 2.0` (`@350–@556 L3480–L3510`). So load carriage already costs endurance server-side, with a level-keyed multiplier a dose can reuse.

## D. Server-side observability of client-granted XP

### D.1 The packet

| member | signature | flags | exposed? | side | cite |
|---|---|---|---|---|---|
| `SyncXp` (Lua global) | `(IsoPlayer)V` on `LuaManager$GlobalObject` | public static | yes, a bare global | sends **only** when `GameClient.client != 0` | `LuaManager$GlobalObject.SyncXp @0–@20 L9830–L9833` |
| `PacketTypes.PlayerXp` | — | — | — | — | same |
| `PlayerXpPacket.setData` | `([Object)V` — takes the `IsoPlayer` | public | — | — | `PlayerXpPacket.setData @0–@10 L27–L28` |
| `PlayerXpPacket.write` | `(ByteBufferWriter)V` — `PlayerID.write` then `player.getXp().save(bb)` | public | — | client | `PlayerXpPacket.write @0–@19 L32–L37` |
| `PlayerXpPacket.parse` | `(ByteBufferReader,IConnection)V` — `PlayerID.parse`, `isConsistent(conn)`, not dead, then `player.getXp().load(bb, 249)` | public | — | server | `PlayerXpPacket.parse @0–@41 L42–L49` |
| `PlayerXpPacket.processServer` | `(PacketType,UdpConnection)V` — `sendToClients(...)` and nothing else | public | — | server | `PlayerXpPacket.processServer @0–@6 L56` |
| `NetworkPlayerAI.syncXp` | `()V` — the **server→client** direction: sends the same `PlayerXp` packet when the connection is fully connected and not mid-disconnect | public | yes | server | `NetworkPlayerAI.syncXp @0–@53 L719–L725` |

The shipped `SyncXp` callers are both in `media/lua/client/ISUI/PlayerStats/ISPlayerStatsUI.lua` (`:596`, `:671`) — the player-stats UI, not the XP system.

**What the server receives and writes:** the whole `XP` object, not a delta. `write` serialises `XP.save(bb)`; `parse` deserialises straight into `player.getXp()` with `XP.load(bb, 249)`. `processServer` then only relays to the other clients. So the server ends up holding the client's totals, multipliers and perk boosts, and the write bypasses `XP.AddXP` entirely.

### D.2 Which events fire server-side, and for which grant

The event name is `AddXP`, not `OnAddXP` — a jar-wide grep for `OnAddXP` returns **no class contains that literal**.

| grant path | `AddXP` event | `LevelPerk` event | why |
|---|---|---|---|
| a client-granted XP synced up with `SyncXp` | **no** | **no** | `PlayerXpPacket.parse` writes the field through `XP.load`, never through `XP.AddXP` |
| `GameServer.addXp` (the `addXp` global on a server, `Fitness.incStats`, `IsoGameCharacter.hitConsequences`, the server branch of `IsoPlayer.updateInternal2`) | **yes** | **yes** | `GameServer.addXp` calls `player.getXp().AddXP(perk, amount, false, !flag, true, flag)` (`GameServer.addXp @33–@52 L1897`), and `XP.AddXP` triggers the event at `@1346–@1364 L14336–L14337` under `GameClient.client == 0` — satisfied on a server |
| an MP client's own `xp.AddXP` | never runs | never runs | the 2/3/4-arg overloads return unless `isLocalPlayer()`; the `addXp` global's non-server arm requires `GameClient.client == null` (`LuaManager$GlobalObject.addXp @23–@35 L9782–L9783`) |

- `XP.AddXP(perk, amount, …)` triggers `LuaEventManager.triggerEventGarbage("AddXP", chr, perk, Float.valueOf(amount))` when `GameClient.client == 0` (`@1346–@1364 L14336–L14337`). Three arguments: the character, the perk, the amount.
- `LevelPerk` is called from inside `AddXP` when the running total crosses `perk.getTotalXpForLevel(getPerkLevel(perk) + 1)` (`XP.AddXP @963–@1002 L14293–L14295`). `IsoGameCharacter.LevelPerk(perk, boolean)` triggers the Lua event with **four** arguments — `(character, perk, Integer level, Boolean true)` — from two branches, `triggerEventGarbage` at `@163–@180 L4849` and `triggerEvent` at `@277–@294 L4864`. **So yes: the `LevelPerk` event carries both the perk and the new level.** The same method also writes `stats.set(CharacterStat.FITNESS, level/5 - 1)` when the perk is Fitness (`@140–@162 L4847`), and only the **client** arm calls `GameClient.sendPerks` (`@183–@194 L4850–L4851`).
- `GameServer.addXp` is capability-gated: `canModifyPlayerStats(conn, player)` is true when the connection's role has `Capability.CanModifyPlayerStatsInThePlayerStatsUI` **or** `conn.havePlayer(player)` (`GameServer.canModifyPlayerStats @0–@26 L1397`), so a server-side grant to a connected player's own character always passes. It also calls `NetworkPlayerAI.updateXpChecker()` afterwards (`GameServer.addXp @55–@59 L1898`; the method is declared on `NetworkCharacterAI`, per a grep for `updateXpChecker`), which refreshes the anti-cheat baseline so the server's own grant does not trip § B.4.

The `addXp` Lua global is therefore the right call for a server-side mod: `addXp(player, perk, amount)` returns unless `player:isExistInTheWorld()`, then routes to `GameServer.addXp` on a server and to `xp.AddXP` in single player, and does nothing on an MP client (`LuaManager$GlobalObject.addXp @0–@38 L9776–L9785`).

### D.3 Reading the day's XP delta per perk on the server

There is no engine-side per-day XP counter (§ E). The reachable read is `player:getXp():getXP(perk)` (`IsoGameCharacter$XP.getXP(Perk)F`, public, on an exposed class), which is exactly what the shipped skill-rust pass uses (`XpUpdate.lua:311`, `:324`) and what the anti-cheat uses (`isPerkXpGrowthRateTooHigh @0–@8 L65`).

A server-side mod computes a daily delta by snapshotting `getXP(perk)` per player into player modData and differencing it. Two cautions the jar makes concrete:

- `PlayerXpPacket.parse` **overwrites** the server's whole `XP` object from the client's bytes, so a snapshot can move without any server-side grant. A delta taken across a `SyncXp` is a delta of the client's bookkeeping, not of server-side training.
- The shipped skill-rust pass subtracts XP: `xpUpdate.everyTenMinutes` calls `addXp(playerObj, Perks.Strength, getLoosingXpValue())` with `getLoosingXpValue()` returning `-1` (`-100` under the `fastLooseXp` debug cheat) (`LuaManager$GlobalObject.getLoosingXpValue @0–@28 L9742–L9747`), so a daily delta can be negative from rust alone. The rust clock is `getLoosingXpTick(timer)`, returning `10` normally and `30000` under the same cheat (`getLoosingXpTick @0–@50 L9752–L9758`), added to `modData.strengthUpTimer`/`fitnessUpTimer` every ten in-game minutes; rust starts above `20000` and the timer resets above `31000` (`XpUpdate.lua:307-331`). Each positive Strength or Fitness grant subtracts `3000` from that timer with a floor of `-50000` (`XpUpdate.lua:181-192`) — so about 13.9 in-game days of no Strength XP before rust begins from a fully-reset timer (derived from `+10` per ten in-game minutes to reach `20000`).

The sharper server-side signal is not the XP delta at all but the **grant events**: hooking `Events.AddXP` on a `server/` file gives `(character, perk, amount)` for every server-side grant, and `Events.LevelPerk` gives `(character, perk, level, addBuffer)`.

## E. Absences proved by jar-wide grep

Each row is a full-jar byte scan over every class entry (~23.7k), well clear of the `--max 60` cap; the answer quoted is the toolchain's own `no class contains that literal`. An absence is the absence of the identifier in any form — a declaration, a call, a descriptor or a string constant — not the absence of the capability under a name nobody guessed.

| the claim | the literal searched | result |
|---|---|---|
| there is no per-player distance-run counter | `distanceRun`, `runDistance`, `distanceTravelled`, `totalDistance`, `walkedDistance`, `metersRun` | absent (six searches) |
| there is no per-player running-time or sprinting-time accumulator with a getter | `getRunningTime`, `getSprintingTime`, `timeRunning`, `sprintTime`, `runTime` | absent (five searches) |
| there is no step counter | `stepCount` | absent |
| there is no lean-mass, fat-mass or aerobic-capacity model | `leanMass`, `leanBodyMass`, `muscleMass`, `getMuscle`, `bodyFat`, `fatMass`, `aerobic`, `VO2` | absent (eight searches) |
| there is no per-day XP accumulator | `dailyXp`, `xpToday`, `xpGainedToday`, `getXpToday` | absent (four searches) |
| there is no training-load or training-dose concept | `trainingLoad`, `getTrainingDose` | absent |
| there is no exercise-rep or exercise-time counter beyond `Fitness.exeTimer`'s last-done timestamp | `exerciseCount`, `repCount`, `totalReps`, `getExerciseTime` | absent (four searches) |
| there is no `OnAddXP` event — the event is named `AddXP` | `OnAddXP` | absent |
| there is no Lua event fired per exercise rep | `OnExercise`, `OnFitness`, `OnPlayerExercise` | absent (three searches); the shipped Lua uses `reportEvent("EventUpdateFitness")`, an **animation** event, not a `LuaEventManager` event |
| there is no regularity getter under a friendlier name | `getFitnessRegularity` | absent; the reachable name is `Fitness.getRegularity(String)` |

Two further absences established from a member list rather than a grep, because the identifier exists elsewhere in the jar:

- **`IsoPlayer` declares no `getCurrentSpeed()`.** A jar grep for `getCurrentSpeed` hits `IsoPlayer.class`, but the class's own method list (`methods zombie/characters/IsoPlayer`, filtered for `Speed`) declares only `getPathSpeed`, `getMoveSpeed`/`setMoveSpeed`, `calculateWalkSpeed`, `getNetworkSpeedMul`, `getParameterCharacterMovementSpeed`, `calculateInTreesSpeed`, `setFitnessSpeed`, `setCombatSpeed`/`getCombatSpeed`. The `getCurrentSpeed` literal in `IsoPlayer.class` is an outbound call (`BaseVehicle`/`ParameterVehicleSpeed` are the other hits). `currentSpeed` and `runningTime` are **public fields with no accessors**, so reaching them from Lua is a field read on an exposed class and needs a live check.
- **`IsoGameCharacter` declares no metabolic-rate getter.** Its member list holds only `setMetabolicTarget(Metabolics)V` and `setMetabolicTarget(F)V` — no `getMetabolicRate`. The read has to go through `getBodyDamage():getThermoregulator():getMetabolicRate()`.

Two non-jar absences that matter as much:

- **`ISTimedActionQueue` is a client file.** It lives at `media/lua/client/TimedActions/ISTimedActionQueue.lua` and is the only shipped definition (`grep -rln "ISTimedActionQueue = "` over `media/lua` returns that one path). A dedicated server cannot read it; the server-side equivalent is `player:getCharacterActions()`, the `java.util.Stack` of `BaseAction` that `Nutrition.updateCalories` itself uses.
- **`BaseAction` is not in the exposer's class set.** A grep for `CharacterTimedActions/BaseAction` returns 13 classes and `LuaManager$Exposer` is not among them, while a grep for `CharacterTimedActions/LuaTimedActionNew` does hit the exposer. So `caloriesModifier` — declared `public float` on `BaseAction` — is not reachable as a field of an exposed class; the route is `LuaTimedActionNew.getTable()` and the Lua table's own `caloriesModifier`, or `getMetaType()` for the action's `Type` string.

## Training dose proposal

**Everything in this section is derived and untested.** No live run backs any of it; the cites above say what the engine does, and the arithmetic below is this report's own.

### The shape

Run one pass on `Events.EveryOneMinute` in a `media/lua/server/` file, guarded `if not isServer() and isClient() then return end`. On a dedicated server that fires once per in-game minute with every connected player reachable through `getOnlinePlayers()` (the pattern `xpUpdate.everyTenMinutes` already uses, `XpUpdate.lua:299-303`). The minute pass has to **sample** rather than integrate, because nothing in the engine accumulates activity time for it (§ E) — so a one-minute sample is one observation of a MET class and the dose is a sum of samples, with the sampling error that implies. Anything that must be counted rather than sampled — swings, reps, level-ups — is counted by an event hook instead.

### Aerobic dose (sampled)

Read one MET value per player per minute and bank it:

```
met = player:getBodyDamage():getThermoregulator():getMetabolicRate()
```

That single read already folds in the engine's own classification of attacking, sprinting, running, sneaking, walking and exercising, plus the endurance blend (§ C.1). Bank `aerobicDose += max(0, met - 1.5) * 1` (minutes), taking `Metabolics.Default` (1.5) as the do-nothing floor so standing still contributes nothing. The scale is then MET-minutes above rest, which is the standard exercise-science unit and needs no invented constants.

Two corrections the jar justifies:

- **Load carriage.** `getMetabolicRate()` does not see inventory weight — the endurance model does (§ C.4). Multiply by the same level-keyed factor the engine uses: `loadMult = {1, 1.5, 1.9, 2.3, 2.8}[getMoodles():getMoodleLevel(MoodleType.HEAVY_LOAD)]` (`IsoPlayer.updateEndurance @249–@305 L3470–L3474`), or the finer `1 + getInventoryWeight()/getMaxWeight()` if the moodle's four steps are too coarse.
- **Body mass.** `Nutrition.updateCalories` already normalises by `getWeight() / 80.0` (`@115–@124 L104`). Reuse that ratio so a heavier character banks more for the same MET, which is what MET means.

A **credit** term for the vaulting and climbing bursts a one-minute sample will usually miss: bank `Metabolics.JumpFence.getMet()` (4.0) or `Metabolics.ClimbRope.getMet()` (8.0) minus the floor, once per event, from a hook on the climb states rather than from the sample. `Nutrition.updateCalories` treats `SwipeStatePlayer`, `ClimbOverFenceState` and `ClimbThroughWindowState` as a flat `8.0` modifier (`@33–@74 L93–L94`), which is the engine's own answer to the same sampling problem.

### Resistance dose (counted, not sampled)

Sampling cannot see a rep or a swing, so count them on events:

| source | hook | dose per event | from |
|---|---|---|---|
| an exercise rep | `Events.AddXP` on a `server/` file, filtered to `Perks.Strength`/`Perks.Fitness` | the amount, split by which body group the rep loaded | `AddXP` fires server-side for every `GameServer.addXp` grant (§ D.2); the exercise rep's amounts are in § A.2 |
| a melee swing | `Events.OnWeaponHitXp` on a `server/` file | `weapon:getWeight() * getLastHitCount()`, or the same endurance formula `applyMeleeEnduranceLoss` uses | `WeaponHit.process` fires it server-side (§ B.2) |
| a heavy timed action | the current action's `caloriesModifier` read off `LuaTimedActionNew:getTable()`, sampled each minute | `(caloriesModifier - 1)` minutes | the 0.5–8 scale in § C.2 |
| load carriage while walking | `max(0, getInventoryWeight() - getMaxWeight()*0.5)` sampled each minute | that excess, in weight-minutes | the threshold vanilla already uses for its Strength grant (`XpUpdate.lua:31`) |

Reading the reps through `Events.AddXP` rather than through `Fitness` has one decisive advantage: the event carries `(character, perk, amount)` and fires **on the server** for exactly the grants the server made (§ D.2), so it needs no polling and no client trust. Its cost is that it cannot distinguish an exercise rep from a melee swing from rust — the mod has to keep its own per-source tally from the other hooks and treat `AddXP` as the total.

### Which body groups a rep loaded

`Fitness.getCurrentExe()` returns the `FitnessExercise` and `FitnessExercise.stiffnessInc` names the groups, but the field is package-private with no getter, so the mod cannot read it from Lua (§ A.2). Two routes that work: mirror the `FitnessExercises.exercisesType` table (it is a plain Lua global the mod can read directly, and the mod's own rows can be added to it), or infer the group from the soreness the rep seeded — `getFitness():getCurrentExeStiffnessTimer(part)` is public and returns the 72-tick countdown (§ A.4).

### The regularity hook the design probably wants

`Fitness.getRegularity(type)` is the engine's own "have you been training this lately" number, per exercise, clamped `[0, 100]`, rising `~0.08` per rep and decaying `0.002` per ten in-game minutes after one idle in-game day (§ A.4). It is public, it returns 0 for an unknown key, it survives a save (`Fitness.save`/`load`) and it syncs on `SyncPlayerFieldsPacket` bit 32. A lean-mass model that wants a "training regularity" input should read it rather than build one, and should note that vanilla decay is slow: `0.288` per in-game day against `~0.08` per rep.

### Cadence and the anti-cheat

A minute pass that grants XP must stay inside `1000 × multiplier × boost` per perk between anti-cheat checks (§ B.4). At the default multipliers that is 1000 XP per check interval per perk — far above anything a MET-minute dose would want to grant, so the bound is unlikely to bite unless the mod converts dose to XP at a steep rate. A mod that writes only its own modData stat is outside the anti-cheat entirely.

### What would falsify this

- That `Fitness.update()` actually ticks on the server for connected players (the call site is ungated, § A.5, but the server's cell loop reaching `updateInternal1` for every player each tick is unread).
- That `getMetabolicRate()` on a server-side `IsoPlayer` tracks the classification rather than sitting at `Default` — `Thermoregulator.update()` shows no side gate at the `updateMetabolicRate` call, but whether the server's thermoregulator is driven at all is a run question.
- That `IsoPlayer.currentSpeed` and `runningTime` are readable from Lua as public fields of an exposed class.
- That `player:getCharacterActions()` on the server holds the client's current timed action, and that iterating it yields `LuaTimedActionNew` objects whose `getTable()` is callable.
- Whether `Events.EveryOneMinute` fires on a dedicated server at the cadence the pass assumes.

## Claims candidates

One line per fact. All grade **C**, bound **C-only** (a static bytecode or shipped-Lua read of one jar of build `42.20.4`; cadence, side-in-practice and behaviour under a session are not settled). A row marked *(derived)* carries an additional derivation bound: the arithmetic is the part a re-reader has to redo.

1. `Fitness.update` runs its body only when `GameTime.getInstance().getMinutes() / 10` differs from its `lastUpdate` field, so the whole fitness tick fires once per ten in-game minutes. — `jar:Fitness.update @0–@31 L88–L93`
2. `Fitness.update` is called from `IsoPlayer.updateInternal2` with no side gate and outside the `SystemDisabler.doCharacterStats` guard that wraps `Nutrition.update` immediately above it. — `jar:IsoPlayer.updateInternal2 @392–@409 L2306–L2310`
3. The only gate above the fitness call in `updateInternal2` is `isAnimal()`; the `isLocal()` test guards the aiming reticle and rejoins before it. — `jar:IsoPlayer.updateInternal2 @325–@392 L2291–L2306`
4. `Fitness.decreaseRegularity` subtracts `0.002` from a type's regularity only when more than `86_400_000` ms of game time have passed since that type's `exeTimer` stamp. — `jar:Fitness.decreaseRegularity @46–@109 L143–L146`
5. Regularity decays `0.288` per in-game day once the one-day grace has passed. *(derived: `0.002` × 144 ten-minute ticks)* — `jar:Fitness.decreaseRegularity @93 L145`, `jar:Fitness.update @0–@8 L88`
6. `Fitness.incRegularity` adds `0.08 * ln(5) / ln(fitnessLvl/5 + 4)` to the current exercise's regularity, clamped to `[0, 100]`. — `jar:Fitness.incRegularity @0–@116 L220–L236`
7. A higher Fitness level earns regularity more slowly: `0.0929` at level 0, `0.08` at level 5, `0.0719` at level 10. *(derived)* — `jar:Fitness.incRegularity @6–@36 L224–L225`
8. `Fitness.exerciseRepeat` refreshes `fitnessLvl` and `strLvl` from `getPerkLevel`, then calls `incRegularity`, `reduceEndurance`, `incFutureStiffness`, `incStats` and `updateExeTimer` in that order. — `jar:Fitness.exerciseRepeat @0–@45 L191–L198`
9. `Fitness.exerciseRepeat` sends `GameServer.sendSyncPlayerFields(player, 32)` when `GameServer.server` is set and the parent is an `IsoPlayer`. — `jar:Fitness.exerciseRepeat @48–@74 L199–L200`
10. `SyncPlayerFieldsPacket` field 32 is the fitness object: `writeParam` calls `Fitness.save` and `parseParam` calls `Fitness.load`. — `jar:method scan of SyncPlayerFieldsPacket for BodyDamage/Fitness refs`
11. `Fitness.incStats` accumulates Strength XP `+4` per `arms` and `+2` per `chest` in the exercise's stiffness list, and Fitness XP `+4` per `legs` and `+2` per `abs`. — `jar:Fitness.incStats @4–@102 L322–L334`
12. `Fitness.incStats`'s level scaling `1 + (level - 5)/10` uses integer division, so it is exactly 1.0 for Strength or Fitness levels 6 through 10 and the branch is a no-op below level 15. *(derived)* — `jar:Fitness.incStats @102–@147 L339–L343`
13. On a dedicated server `Fitness.incStats` grants exercise XP through `GameServer.addXp` with the amount truncated to an int; in single player it calls `XP.AddXP` untruncated; on a multiplayer client it grants nothing. — `jar:Fitness.incStats @168–@251 L349–L356`
14. `Fitness.reduceEndurance` scales its `0.015` base by `ln(regularity/50 + 50)/ln(51)`, by `1.3` for a `FitnessHeavy` exercise, and by `1 + HEAVY_LOAD_level/3` with integer division. — `jar:Fitness.reduceEndurance @0–@105 L245–L260`
15. `Fitness.reduceEndurance` writes the endurance stat only when `GameClient.client == null`, then sends `PacketTypes.SyncPlayerStats` with the `ENDURANCE` bit mask when `GameServer.server` is set. — `jar:Fitness.reduceEndurance @106–@185 L262–L269`
16. `Fitness.incFutureStiffness` seeds `stiffnessTimerMap[part] = 72` and scales its `0.5` per-rep increment by `(120 - regularity)/170`. — `jar:Fitness.incFutureStiffness @63–@141 L291–L299`
17. Soreness from an exercise lands 12 in-game hours later: 72 countdown steps at one step per ten-in-game-minute update. *(derived)* — `jar:Fitness.incFutureStiffness @93 L292`, `jar:Fitness.update @0–@8 L88`
18. `Fitness.increasePain` adds `2.5` to `BodyPart.getStiffness()` on `ForeArm_L` through `UpperArm_R` for `arms`, `UpperLeg_L` through `LowerLeg_R` for `legs`, and `Torso_Upper` for `chest`. — `jar:Fitness.increasePain @0–@154 L152–L166`
19. `Fitness.init` builds its exercise map from the Kahlua global `FitnessExercises.exercisesType` and returns early when the map is already populated, so it is idempotent. — `jar:Fitness.init @0–@124 L565–L581`
20. `Fitness$FitnessExercise` reads `type`, `metabolics`, a comma-separated `stiffness` string and `xpMod` (default 1, overridden only when `> 0`) off the Lua table; all four fields are package-private with no getters. — `jar:Fitness$FitnessExercise.<init> @9–@78 L67–L73`
21. `Fitness.getRegularity` returns 0 for an absent key rather than throwing. — `jar:Fitness.getRegularity @12–@20 L536–L537`
22. `Fitness.decreaseRegularity`, `increasePain` and `updateExeTimer` are private; every other declared member of `Fitness` is public. — `jar:constant-pool access-flag parse of Fitness`
23. The `Fitness` class is in the exposer's class set. — `jar:jar-wide grep BodyDamage/Fitness`
24. The only Java call to `Fitness.exerciseRepeat` is in `StatePacket.processServer`, reached when the packet's stage is `Execute`, its state is `FitnessState.instance()`, and the character is an `IsoPlayer` currently in that state. — `jar:StatePacket.processServer @414–@474 L180–L183`
25. `ISFitnessAction:animEvent` calls `exeLooped()` — and so `exerciseRepeat` — only when `isServer()` or in single player. — `lua:media/lua/shared/TimedActions/ISFitnessAction.lua:157-168`
26. `ISFitnessAction:serverStart` arms the rep loop with `emulateAnimEvent(netAction, period, "ActiveAnimLooped", nil)` at per-exercise periods of 3000, 1300, 1300, 2400, 2200, 1500 and 1900 ms. — `lua:media/lua/shared/TimedActions/ISFitnessAction.lua:132-149`
27. `ISFitnessAction` carries `caloriesModifier = 3` and sets `character:setMetabolicTarget(self.exeData.metabolics)` every frame of its update. — `lua:media/lua/shared/TimedActions/ISFitnessAction.lua:51,222`
28. `ISFitnessAction` force-stops on climbing, aiming, sitting on furniture, any movement key, an `ENDURANCE` moodle above 2, or the exercise duration expiring. — `lua:media/lua/shared/TimedActions/ISFitnessAction.lua:32-49`
29. Neither `ISFitnessUI.lua` nor `ISFitnessAction.lua` contains a `sendClientCommand`: the exercise reaches the server as the timed action's net action plus `StatePacket`. — `lua:grep sendClientCommand over both files`
30. There is no Java method that grants Strength or Fitness XP for a melee swing; the only Java grants of those two perks are `Fitness.incStats`, `IsoGameCharacter.hitConsequences` and `IsoPlayer.updateInternal2`. — `jar:jar-wide grep AddXP narrowed by a per-method reference scan of all 22 hit classes`
31. `IsoGameCharacter.hitConsequences` grants `2.0` Strength XP when the victim survives a non-ranged hit from a weapon with `isKnockBackOnNoDeath()`, through `GameServer.addXp` on the server and `XP.AddXP` in single player, and nothing on a multiplayer client. — `jar:IsoGameCharacter.hitConsequences @103–@161 L6310–L6317`
32. `IsoPlayer.updateInternal2` grants `1.0` Fitness XP on a `1/(300 × InvMultiplier)` roll while endurance is below `getEnduranceDangerWarning()`, gated `GameClient.client == 0`. — `jar:IsoPlayer.updateInternal2 @727–@796 L2362–L2368`
33. `OnWeaponHitXp` has exactly two triggers: `CombatManager.attackCollisionCheck`, gated to single player by requiring both network flags clear, and `WeaponHit.process`, gated to the dedicated server by `GameServer.server != 0`. — `jar:CombatManager.attackCollisionCheck @3414–@3459 L1095–L1097`, `jar:WeaponHit.process @322–@344 L107–L108`
34. Both `OnWeaponHitXp` triggers pass `hitCount` as the literal `1`. — `jar:CombatManager.attackCollisionCheck @3455 L1097`, `jar:WeaponHit.process @340 L108`
35. Vanilla's melee Strength XP is `owner:getLastHitCount()` and its melee Fitness XP is a flat `1` above the endurance warning; neither is randomised. — `lua:media/lua/server/XpSystem/XpUpdate.lua:70-76`
36. A stomp is the `isAimAtFloor() && isDoShove()` branch of `attackCollisionCheck`, whose damage is `Rand.Next(0.7, 1.0) + 0.2 × Strength level` before shoe modifiers; it grants no Strength XP of its own. — `jar:CombatManager.attackCollisionCheck @2585–@2650 L971–L975`
37. `OnPlayerMove` has exactly two triggers: `IsoPlayer.updateInternal2`, gated to single player by requiring both network flags clear, and `IsoPlayer.updateRemotePlayer`, inside the `GameServer.server != 0` arm and so dedicated-server only. — `jar:IsoPlayer.updateInternal2 @840–@856 L2384–L2385`, `jar:IsoPlayer.updateRemotePlayer @20–@156 L7360–L7387`
38. On a multiplayer client `OnPlayerMove` never fires for the local player, because `updateRemotePlayer` returns false unless `remote` is set. — `jar:IsoPlayer.updateRemotePlayer @0–@8 L7352–L7353`
39. `IsoPlayer.currentSpeed` is set server-side from the network movement flags to 1.5 when sprinting, 1.0 when running, 0.5 when walking and 0.0 when still. — `jar:IsoPlayer.updateRemotePlayer @84–@137 L7374–L7383`
40. `xpUpdate.randXp` is `1/(100 × InvMultiplier)` when `isServer()` and `1/(700 × InvMultiplier)` otherwise, so the dedicated server rolls seven times as often per move event as single player. — `lua:media/lua/server/XpSystem/XpUpdate.lua:167-173`
41. Vanilla grants `2` Strength XP on a `randXp()` roll whenever `getInventoryWeight() > getMaxWeight() * 0.5` and a move event fired, with no requirement to be moving fast. — `lua:media/lua/server/XpSystem/XpUpdate.lua:31-35`
42. `AntiCheatXPUpdate.isPerkXpGrowthRateTooHigh` bounds one perk's XP delta between checks at `1000 × getMaxPerkXpMultiplier × getMaxPerkXpBoostMultiplier`, logging on `DebugType.Multiplayer` when it trips. — `jar:AntiCheatXPUpdate.isPerkXpGrowthRateTooHigh @0–@113 L65–L75`
43. `getMaxPerkXpBoostMultiplier` resolves to 1.0, 1.33, 1.66 or 0.25 by perk boost, and the `FAST_LEARNER` adjustment applies only to perks whose parent is not `Perks.PhysicalCategory` — so it does not widen Strength or Fitness. — `jar:AntiCheatXPUpdate.getMaxPerkXpBoostMultiplier @0–@114 L24–L37`
44. `AntiCheatXPUpdate.update` walks `connection.players[]` and returns false on the first player that trips the per-perk check. — `jar:AntiCheatXPUpdate.update @18–@63 L99–L105`
45. `Metabolics` is a 24-value MET enum in the exposer's class set, with `getMet`, `getWm2`, `getW`, `getBtuHr` and the static `MetToWm2`, `MetToW`, `MetToBtuHr`. — `jar:Metabolics.<clinit> @0–@382 L7–L30`, `jar:jar-wide grep BodyDamage/Metabolics`
46. The MET values are Sleeping 0.8, SeatedResting 1.0, StandingAtRest 1.1, SedentaryActivity 1.2, DrivingCar 1.4, Default 1.5, LightDomestic 1.6, Walking2kmh 1.9, HeavyDomestic 2.0, UsingTools 2.5, DefaultExercise 3.0, Walking5kmh 3.1, LightWork 3.2, MediumWork 3.9, JumpFence 4.0, DiggingSpade 5.5, Fitness 6.0, HeavyWork 6.0, Running10kmh 6.9, ClimbRope 8.0, ForestryAxe 8.0, FitnessHeavy 9.0, Running15kmh 9.5, MAX 10.3. — `jar:Metabolics.<clinit> @0–@382 L7–L30`
47. `Thermoregulator.updateMetabolicRate` classifies the player each tick into `Running15kmh` when sprinting, `Running10kmh` when running, `Walking2kmh` when sneaking, `Walking5kmh` when `currentSpeed > 0`, a weapon-type-keyed value when attacking, and `Metabolics.Fitness` whenever `getFitness().getCurrentExe()` is non-null — the exercise case overriding the rest. — `jar:Thermoregulator.updateMetabolicRate @17–@299 L771–L818`
48. The exercise override in `updateMetabolicRate` uses the flat `Metabolics.Fitness` (6.0) and never the per-exercise `metabolics`; `FitnessHeavy` reaches the thermoregulator only through `ISFitnessAction:update`'s per-frame `setMetabolicTarget`. — `jar:Thermoregulator.updateMetabolicRate @282–@299 L817–L818`, `lua:ISFitnessAction.lua:51`
49. `IsoGameCharacter.updateFitness` sets `CharacterStat.FITNESS` to `getPerkLevel(Perks.Fitness) / 5 - 1`. — `jar:IsoGameCharacter.updateFitness @0–@25 L10312–L10313`
50. `Nutrition.updateCalories` takes its calorie multiplier from `getCharacterActions().get(0).caloriesModifier`, overrides it to `8.0` in `SwipeStatePlayer`, `ClimbOverFenceState` or `ClimbThroughWindowState`, and then overwrites it again to 1.0 running, 1.3 sprinting or 0.6 walking — so a timed action's modifier and the climb override only reach the drain while the player is stationary. — `jar:Nutrition.updateCalories @2–@255 L89–L114`
51. `Nutrition.updateCalories` normalises its drain by `getWeight() / 80.0` and applies the thermoregulator's energy multiplier only on the asleep and idle branches. — `jar:Nutrition.updateCalories @77–@316 L99–L118`
52. `IsoPlayer.updateEndurance` returns for an animal and returns when `GameClient.client != 0`, so it runs on a dedicated server and in single player only. — `jar:IsoPlayer.updateEndurance @0–@13 L3427–L3428`
53. `IsoPlayer.updateEndurance` multiplies its drain by `1.5` when sneaking, by `1.4` base (`2.9` OVERWEIGHT, `0.8` ATHLETIC) `× 2.3 × getPacingMod() × getHyperthermiaMod()`, by `0.7` (`1.0` ASTHMATIC), and by 1.5/1.9/2.3/2.8 for `HEAVY_LOAD` levels 1–4. — `jar:IsoPlayer.updateEndurance @40–@347 L3437–L3478`
54. A walking player with a `HEAVY_LOAD` moodle above level 2 takes a second endurance drain at `runningEnduranceReduce × (base × 3.0 × pacing × hyperthermia) × 0.5 × asthma × sneak × GameTime.getMultiplier() × loadMult / 2.0`. — `jar:IsoPlayer.updateEndurance @350–@556 L3480–L3510`
55. `IsoPlayer.updateMovementRates` is called only when `GameServer.server != 0`. — `jar:IsoPlayer.updateInternal2 @913–@920 L2402–L2403`
56. `IsoPlayer.runningTime` accumulates `GameTime.getThirtyFPSMultiplier()` per tick while the deferred-movement vector is non-zero and resets to 0 the moment it is zero, so it is a consecutive-movement timer and not a daily total. — `jar:IsoPlayer.updateInternal2 @161–@189 L2262–L2264`
57. `caloriesModifier` on the shipped timed actions ranges from `0.5` (reading, resting, researching) through the `1` default to `8` (building, plastering, shovelling ground, chopping trees, barricading, destroying, pickaxing, kindling). — `lua:grep caloriesModifier over media/lua`
58. `LuaTimedActionNew.getMetaType` returns the Lua action table's metatable `Type` string, or the empty string. — `jar:LuaTimedActionNew.getMetaType @0–@39 L226–L229`
59. `SyncXp(player)` sends `PacketTypes.PlayerXp` only when `GameClient.client != 0`, so it is a client-to-server push. — `jar:LuaManager$GlobalObject.SyncXp @0–@20 L9830–L9833`
60. `PlayerXpPacket.write` serialises the whole `XP` object with `XP.save`; `parse` deserialises it straight back with `XP.load(bb, 249)`; `processServer` only calls `sendToClients`. — `jar:PlayerXpPacket.write @0–@19 L32–L37`, `jar:PlayerXpPacket.parse @0–@41 L42–L49`, `jar:PlayerXpPacket.processServer @0–@6 L56`
61. Because `PlayerXpPacket.parse` writes through `XP.load` and never through `XP.AddXP`, a client-granted XP synced up with `SyncXp` fires neither the `AddXP` nor the `LevelPerk` event on the server. — `jar:PlayerXpPacket.parse @24–@41 L46`, `jar:IsoGameCharacter$XP.AddXP @1346–@1364 L14336–L14337`
62. `XP.AddXP` triggers the Lua event `AddXP` with `(character, perk, Float amount)` when `GameClient.client == 0`, so it fires on a dedicated server and in single player but never on a multiplayer client. — `jar:IsoGameCharacter$XP.AddXP @1346–@1364 L14336–L14337`
63. `IsoGameCharacter.LevelPerk` triggers the Lua event `LevelPerk` with four arguments — the character, the perk, the new level as an `Integer`, and `Boolean.TRUE` — from both of its branches, and only the client arm calls `GameClient.sendPerks`. — `jar:IsoGameCharacter.LevelPerk @163–@194 L4849–L4851`, `@277–@294 L4864`
64. `XP.AddXP` calls `LevelPerk` when the running total crosses `perk.getTotalXpForLevel(getPerkLevel(perk) + 1)`. — `jar:IsoGameCharacter$XP.AddXP @963–@1002 L14293–L14295`
65. `GameServer.addXp` returns unless a connection exists for the player and `canModifyPlayerStats` passes, then calls `XP.AddXP` and `NetworkCharacterAI.updateXpChecker()`. — `jar:GameServer.addXp @0–@62 L1889–L1900`
66. `GameServer.canModifyPlayerStats` passes when the connection's role holds `Capability.CanModifyPlayerStatsInThePlayerStatsUI` **or** the connection owns that player, so a server-side grant to a connected player's own character always passes. — `jar:GameServer.canModifyPlayerStats @0–@26 L1397`
67. The `addXp` Lua global returns unless `isExistInTheWorld()`, routes to `GameServer.addXp` on a server and to `XP.AddXP` in single player, and does nothing on a multiplayer client. — `jar:LuaManager$GlobalObject.addXp @0–@38 L9776–L9785`
68. `NetworkPlayerAI.syncXp` is the server-to-client direction of the same `PlayerXp` packet, sent only when the connection is fully connected and not a delayed disconnect. — `jar:NetworkPlayerAI.syncXp @0–@53 L719–L725`
69. `getLoosingXpValue()` returns `-1` and `getLoosingXpTick(t)` returns `10` outside debug, so skill rust removes 1 XP at a time on a timer that rises 10 per ten in-game minutes. — `jar:LuaManager$GlobalObject.getLoosingXpValue @0–@28 L9742–L9747`, `jar:LuaManager$GlobalObject.getLoosingXpTick @0–@50 L9752–L9758`
70. About 13.9 in-game days of no Strength XP pass before rust begins from a fully-reset timer. *(derived: 20000 threshold ÷ 10 per ten in-game minutes)* — `jar:LuaManager$GlobalObject.getLoosingXpTick @48–@50 L9758`, `lua:XpUpdate.lua:307-309`
71. Each positive Strength or Fitness grant subtracts 3000 from its rust timer, floored at −50000. — `lua:media/lua/server/XpSystem/XpUpdate.lua:181-192`
72. There is no `OnAddXP` event in the jar; the event is named `AddXP`. — `jar:jar-wide grep OnAddXP`
73. The engine holds no per-player distance-run, running-time, sprinting-time or step counter. — `jar:jar-wide greps distanceRun, runDistance, distanceTravelled, totalDistance, walkedDistance, metersRun, getRunningTime, getSprintingTime, timeRunning, sprintTime, runTime, stepCount`
74. The engine holds no lean-mass, fat-mass or aerobic-capacity concept. — `jar:jar-wide greps leanMass, leanBodyMass, muscleMass, getMuscle, bodyFat, fatMass, aerobic, VO2`
75. The engine holds no per-day XP accumulator and no training-load concept. — `jar:jar-wide greps dailyXp, xpToday, xpGainedToday, getXpToday, trainingLoad, getTrainingDose`
76. The engine fires no Lua event per exercise rep; `EventUpdateFitness` is an animation event reported through `reportEvent`, not a `LuaEventManager` event. — `jar:jar-wide greps OnExercise, OnFitness, OnPlayerExercise`, `lua:ISFitnessAction.lua:188`
77. The engine holds no exercise-rep or exercise-time counter beyond `Fitness.exeTimer`'s last-done timestamp per exercise type. — `jar:jar-wide greps exerciseCount, repCount, totalReps, getExerciseTime`
78. `IsoPlayer` declares no `getCurrentSpeed()`; `currentSpeed` and `runningTime` are public fields with no accessors. — `jar:member list of IsoPlayer filtered for Speed`, `jar:field table of IsoPlayer`
79. `IsoGameCharacter` declares no metabolic-rate getter — only `setMetabolicTarget(Metabolics)` and `setMetabolicTarget(float)`; the read goes through `BodyDamage.getThermoregulator().getMetabolicRate()`. — `jar:member list of IsoGameCharacter`
80. `CharacterTimedActions/BaseAction` is not in the exposer's class set while `LuaTimedActionNew` is, so `BaseAction.caloriesModifier` is not reachable as a field from Lua. — `jar:jar-wide greps CharacterTimedActions/BaseAction and CharacterTimedActions/LuaTimedActionNew filtered for Exposer`
81. `ISTimedActionQueue` is defined only in `media/lua/client/TimedActions/ISTimedActionQueue.lua`, so a dedicated server cannot read it; `getCharacterActions()` is the server-side equivalent. — `lua:grep -rln "ISTimedActionQueue = " over media/lua`

## Not read

Method bodies this report cites by name or by a windowed dump but did not read end to end, and questions it hands on:

- `IsoPlayer.updateInternal2` was read only in windows (`@0–@430`, `@700–@1000`) out of a method that runs past offset 3900. A branch above or below those windows could gate the fitness call or a second XP grant; the `isAnimal()` gate at `@325` is the only one found in the windows read.
- `CombatManager.attackCollisionCheck` was read only at `@0–@100`, `@2580–@2640` and `@3400–@3480`, out of a body running past offset 3900. The `Perks.Strength` reference at `@2608` was read; other perk references in the unread stretches were not.
- `IsoGameCharacter$XP.AddXP(Perk,F,Z,Z,Z,Z)` was read at `@0–@500`, `@960–@1100` and `@1330–@1367`. The multiplier and boost arithmetic between `@500` and `@960` was not read, so what the amount is actually multiplied by before the total is written is unread; only the protein branch, the Fitness gate, the level-up call and the event trigger were.
- `Fitness.incFutureStiffness` was read only to `@143`; its tail (which writes `stiffnessIncMap`) was not.
- `Fitness.increasePain` was read to `@154`; the `abs` group's body-part range was not reached.
- `Fitness.initRegularityMapProfession` was read to `@148`: Fire Officer, Fitness Instructor and Security Guard each seed regularity, and the base roll is `Rand.Next(7, 12)` with `Rand.Next(10, 20)` for the Fire Officer flag, but the remaining profession branches and the map write were not read.
- `Fitness.save` and `Fitness.load` were never dumped, so exactly which of the five maps survive a save, and what version gate `load` applies, is unread.
- `Thermoregulator.update()` was only grepped for side gates (none found at the `updateMetabolicRate` call, `@49`); the method was not read, so what drives it and how often is unread. `Thermoregulator.getEnergyMultiplier` and `getMetabolicRateIncMultiplier`/`DecMultiplier` were not dumped.
- `Thermoregulator.updateMetabolicRate`'s `tableswitch` on `WeaponType` was read for its target constants but not mapped weapon-type-by-weapon-type; which weapon gives `HeavyWork` rather than `MediumWork` is unread.
- `Nutrition.updateCalories` was read whole to `@319`; anything after `@319` (if the method continues) was not.
- `IsoPlayer.updateEndurance` was read to `@600`; the `@557` onward fatigue branch was only partly read and `updateEnduranceWhileSitting`/`updateEnduranceWhileInVehicle` were not dumped.
- `IsoPlayer.updateRemotePlayer` was read to `@175` plus a grep of the whole body for side gates; the `GameServer.server` branches at `@1238` and `@1363` were not read.
- `IsoPlayer.updateMovementRates` was never dumped, so what the server computes there is unread.
- `StatePacket.processServer` was read to `@480`; the tail from `@475` was not.
- `AbstractAntiCheat.update` was not dumped, so the anti-cheat check interval — the denominator of the 1000-XP bound — is unread. This is the single most load-bearing gap in § B.4.
- `NetworkCharacterAI.updateXpChecker` and `NetworkPlayerAI.setXp`/`setXpMultiplier`/`setXpBoost` were not dumped; the anti-cheat's stored-baseline semantics are inferred from `isPerkXpGrowthRateTooHigh`'s use of their return values.
- `XP.save`, `XP.load`, `XP.savePerk`, `XP.loadPerk` and `XP.getMultiplier`/`addXpMultiplier` were not dumped, so what the `PlayerXpPacket` round trip actually overwrites (perk XP only, or multipliers and boosts as well) is unread. The claim in § D.1 that the whole object is overwritten rests on the `save`/`load` call, not on their bodies.
- `SyncPlayerFieldsPacket.writeParam`/`parseParam` were established by a per-method reference scan, not by a dump, so that bit 32 is the fitness field is an inference from the reference and the `sendSyncPlayerFields(player, 32)` literal, not a read of the switch.
- The `FitnessState` class itself (`zombie/ai/states/FitnessState`) was not opened, so what its `execute` does on the server beyond driving the state packet is unread.
- `ISFitnessUI.lua` was grepped, not read whole; what the panel sends when the player picks a weight or a duration beyond the `ISFitnessAction:new` call at `:280` is unread.
- `IsoGameCharacter.isClimbing`, `isClimbingRope`, `getClimbRopeTime`, `getClimbData` and the climb states' `execute` bodies were not dumped; whether a climb is observable per-event on the server, and with what duration, is unread.
- Exposure was tested by the grep-for-the-exposer-class shortcut rather than by reading the exposer dump end to end. That is weaker than the library's own exposure test: a hit says the exposer's constant pool holds the class name, which is strong evidence of registration but not the read-in-full membership check. `Fitness`, `Metabolics`, `Thermoregulator`, `IsoPlayer` and `LuaTimedActionNew` hit; `BaseAction` did not.
- Whether `Events.EveryOneMinute`, `Events.AddXP` and `Events.LevelPerk` actually fire on a dedicated server at the cadence the dose proposal assumes is a run question and was not touched.
- No live run, no harness probe, and no reading of the install's own logs backs any sentence in this report.
