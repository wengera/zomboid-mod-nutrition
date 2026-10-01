# Exercise and training
Verified against 42.20.4 (b0bbce05d5) · 2026-10-01 · scope: the `Fitness` object (its ten-minute tick, regularity, the per-rep XP, endurance and soreness), the exercise action's path to the server, and every shipped grant of Strength or Fitness XP, Java and Lua; the XP pipeline, the events and skill rust are handed to perks-and-strength, the endurance model to endurance-fatigue-sleep, the packets to mp-model and wire-packets.

## Key facts

- `Fitness.update` runs its body once per ten in-game minutes and is called with no side gate, so the whole fitness tick is not a local-player-only update in the bytecode [T6.1] [T6.2].
- Each rep adds `0.08 × ln(5) / ln(fitnessLvl/5 + 4)` to the exercise's regularity, clamped to `[0, 100]` [T6.6].
- That rise is about 0.0929 per rep at Fitness 0, 0.08 at Fitness 5 and 0.0719 at Fitness 10 [T6.7].
- Regularity falls by 0.002 per ten-minute tick only once more than 86 400 000 ms of game time have passed since the exercise was last done [T6.4].
- Past that one-day grace the fall is 0.288 regularity per in-game day, against roughly 0.08 gained per rep [T6.5] [T6.7].
- A rep's Strength XP is `+4` per `arms` and `+2` per `chest` term, its Fitness XP `+4` per `legs` and `+2` per `abs` term, in the exercise's stiffness list [T6.9].
- The level scaling of that XP uses integer division, so its factor is exactly 1.0 at every level from 6 to 10 [T6.10].
- On a dedicated server the rep's XP goes through `GameServer.addXp` truncated to an integer, and on a multiplayer client the rep grants nothing [T6.11].
- A rep costs a base of 0.015 endurance, scaled by regularity, by 1.3 for a heavy exercise and by the heavy-load moodle [T6.12].
- Soreness is seeded as a 72-step countdown and lands 12 in-game hours after the first rep that seeds it [T6.14] [T6.15].
- When it lands, each ten-minute tick adds 2.5 stiffness to every body part in the loaded group [T6.16].
- The only Java call that runs a rep is in the server's handler of the state packet, when the player is in the fitness state [T6.22].
- `OnWeaponHitXp` has exactly two triggers, one single-player only and one dedicated-server only [T6.31].
- Both `OnWeaponHitXp` triggers pass `hitCount` as the literal `1`, so the vanilla melee Strength grant reads the swing's hit count off the attacker instead [T6.32] [T6.33].

## How it works

<a id="fitness-object"></a>
### The `Fitness` object

Every player carries one `Fitness` object, reached from Lua through the public `IsoPlayer.getFitness()`, and the class is registered with the Lua exposer [T6.21].
Of its declared methods, `decreaseRegularity`, `increasePain` and `updateExeTimer` are private and every other method is public; its seventeen fields are all private [T6.20].
So a mod reaches the regularity map, the stiffness timers and the current exercise through getters and setters, and cannot call the decay, the pain step or the timer stamp directly [T6.20].

**The tick.**
`Fitness.update` divides `GameTime.getMinutes()` by ten and compares the quotient with its `lastUpdate` field, returning at once when the bucket has not changed [T6.1].
The body therefore runs once per ten in-game minutes, per player [T6.1].
It is called from `IsoPlayer.updateInternal2` right after `Nutrition.update`, with no side gate of its own and outside the `SystemDisabler.doCharacterStats` guard that wraps the nutrition call [T6.2].
The only gate above the fitness call in that method is `isAnimal()`; the `isLocal()` test above it guards the aiming reticle and rejoins before the fitness call [T6.3].
Disabling character stats through that switch stops the nutrition update and leaves the fitness tick running [T6.2].
Whether the server's update loop actually reaches that call for every connected player is a run question, stated under [Open](#open).

Each tick first calls `decreaseRegularity`, then counts every soreness countdown down by one, then applies pain to every group whose countdown has expired [T6.1].

**Regularity.**
Regularity is a per-exercise number held in a map keyed by the exercise type [T6.6].
`Fitness.incRegularity` computes `0.08 × ln(5) / ln(fitnessLvl/5 + 4)`, the level divided as a float, adds it to the current exercise's entry and clamps the result to `[0, 100]` [T6.6].
A higher Fitness level earns regularity more slowly: about 0.0929 per rep at level 0, exactly 0.08 at level 5 and about 0.0719 at level 10 [T6.7].
`Fitness.decreaseRegularity` walks the map and, for a type that has a last-done stamp, subtracts 0.002 only when more than 86 400 000 ms of game time have passed since that stamp, with no lower clamp on that path [T6.4].
A type with no stamp never decays, and a type done within the last in-game day holds its value [T6.4].
Past the grace the decay is 0.002 times the 144 ten-minute ticks of a day, 0.288 per in-game day; the arithmetic is the part a re-reader redoes [T6.5].
Vanilla regularity is therefore a slow signal, its daily decay a few reps' worth of gain [T6.5] [T6.7].
The decay path has no lower clamp, so a long idle stretch takes regularity below 0 until the next rep's clamp lifts it back [T6.4] [T6.6].
`Fitness.getRegularity(type)` returns 0 for an absent key rather than throwing, so any exercise name can be read on any player without a guard [T6.19].

**One rep.**
`Fitness.exerciseRepeat` refreshes the cached Fitness and Strength levels from `getPerkLevel`, then calls `incRegularity`, `reduceEndurance`, `incFutureStiffness`, `incStats` and `updateExeTimer` in that order [T6.8].
Because regularity rises first, the endurance cost and the soreness increment of a rep read the regularity that rep has just raised [T6.8] [T6.12] [T6.14].
The last call stamps the exercise's last-done time with the game calendar, which is what resets the one-day decay grace [T6.4] [T6.38].
The `32` push `exerciseRepeat` sends on a server after those five calls is stated with its recipient at [mp-model](../platform/mp-model.md) under the sync globals, and the packet's fields at [wire-packets](../facts/wire-packets.md).

**The XP of a rep.**
`Fitness.incStats` walks the current exercise's stiffness list and accumulates Strength XP `+4` per `arms` and `+2` per `chest`, and Fitness XP `+4` per `legs` and `+2` per `abs` [T6.9].
It then multiplies each total by `1 + (level − 5)/10` when the matching level is above 5, and both divisions are integer divisions [T6.10].
The quotient is 0 for every level from 6 to 14, so the factor is exactly 1.0 for levels 6 through 10 and the branch changes nothing below level 15; the arithmetic is the part a re-reader redoes [T6.10].
Both totals are then multiplied by the exercise's `xpMod` [T6.9] [T6.18].
The grant is side-split: on a dedicated server it calls `GameServer.addXp` for Strength and for Fitness with each amount truncated to an integer, in single player it calls `XP.AddXP` untruncated, and on a multiplayer client it grants nothing [T6.11].
What `GameServer.addXp` and `XP.AddXP` then do with the amount — the gates, the multipliers, the events — is stated at [perks-and-strength](../facts/perks-and-strength.md#events).

```text
incStats (per rep)
  strXp = 4·#arms + 2·#chest          fitXp = 4·#legs + 2·#abs
  if strLvl > 5:  strXp *= 1 + (strLvl − 5) / 10      integer division
  if fitLvl > 5:  fitXp *= 1 + (fitLvl − 5) / 10      integer division
  strXp *= xpMod;  fitXp *= xpMod
  server:  GameServer.addXp(player, Strength, (int) strXp); same for Fitness
  single player:  XP.AddXP(Strength, strXp); same for Fitness
  multiplayer client:  nothing
```
The rep's XP as the bytecode computes it [T6.9] [T6.10] [T6.11].

**Endurance.**
`Fitness.reduceEndurance` starts from a base of 0.015 and multiplies it by `ln(regularity/50 + 50) / ln(51)` [T6.12].
That factor is just under 1 at regularity 0, exactly 1 at regularity 50 and just over 1 at 100, so a higher regularity makes a rep marginally dearer, not cheaper [T6.12].
The cost is multiplied by 1.3 when the exercise's metabolics is `FitnessHeavy`, and then by `1 + heavyLoadLevel/3` in integer division, which is 1 below heavy-load level 3 and 2 at levels 3 and 4 [T6.12].
The endurance write is gated on `GameClient.client` being clear, so it happens on a dedicated server and in single player and never on a multiplayer client [T6.13].
On a server it is followed by a player-stats packet carrying the endurance bit [T6.13].
How the rest of the endurance model drains and restores the stat is stated at [endurance-fatigue-sleep](../facts/endurance-fatigue-sleep.md).

**Soreness.**
`Fitness.incFutureStiffness` seeds a countdown of 72 for each group in the exercise's stiffness list that is neither counting down nor already applying pain [T6.14].
The per-rep soreness increment starts at 0.5 and is scaled by `(120 − regularity) / 170`, so a trained exercise seeds less soreness than an untrained one [T6.14].
`Fitness.update` decrements every countdown by one per tick and moves a group to the pain list when its countdown reaches zero [T6.1].
The countdown is keyed by the body group and not by the exercise, so two exercises that load `arms` share one countdown [T6.14].
The countdowns and the pain state are read through `getCurrentExeStiffnessTimer(part)`, `getCurrentExeStiffnessInc(part)` and `onGoingStiffness()`, all public [T6.20].
The 72 steps at one step per ten-minute update put the soreness 12 in-game hours after the rep that seeded it; the arithmetic is the part a re-reader redoes [T6.15].
A later rep of the same group within that window does not reseed the countdown, because the seed is skipped for a group already counting down [T6.14].
Once a group is on the pain list, each tick calls `Fitness.increasePain` for it and takes one step off its accumulated increment, dropping the group once the increment reaches zero [T6.1] [T6.16].
`Fitness.increasePain` adds 2.5 to `BodyPart.getStiffness()` on every part of the group: `ForeArm_L` through `UpperArm_R` for `arms`, `UpperLeg_L` through `LowerLeg_R` for `legs`, `Torso_Upper` for `chest` and `Torso_Lower` for `abs` [T6.16].
The muscle-strain adders that write the same body-part stiffness are stated at [perks-and-strength](../facts/perks-and-strength.md#readers).

**The exercise map.**
`Fitness.init` reads the Kahlua global `FitnessExercises`, takes its `exercisesType` sub-table and builds one exercise object per key [T6.17].
It returns at once when the map is already populated, and when either table is missing, so it is idempotent and safe for a mod to call [T6.17].
A mod that adds rows to `FitnessExercises.exercisesType` before the first `init` therefore adds exercises the Java object will know [T6.17].
The table `init` reads is the global of the Lua state the call runs in, so on a dedicated server it is the server's own copy of the table, a reading of the call and not a measurement [T6.17].
Each exercise object reads four keys off its Lua row: `type`, `metabolics`, a comma-separated `stiffness` string split into a list, and `xpMod`, which defaults to 1 and is overridden only when the row's value is above 0 [T6.18].
All four fields are package-private with no getters, so Lua holds the exercise object from `getCurrentExe()` but cannot read its fields [T6.18].
The body groups a rep loads are therefore read off the Lua table the mod can see, or off the soreness countdown `getCurrentExeStiffnessTimer(part)` returns, not off the Java object [T6.18] [T6.20].

<a id="exercise-path"></a>
### How a rep reaches the server

A rep runs on the server, through the server's emulated animation loop or the state packet's handler [T6.24] [T6.22].
The only Java call to `Fitness.exerciseRepeat` is in `StatePacket.processServer`, reached when the packet's stage is `Execute`, its state is `FitnessState`, and the character is an `IsoPlayer` currently in that state [T6.22].
A multiplayer client never calls `exerciseRepeat` through Java, and the server calls it once per state packet that meets those four tests [T6.22].

The Lua side of the same loop is the timed action `ISFitnessAction` in the shared timed-action folder.
`ISFitnessAction:animEvent` calls `exeLooped()`, which is `self.fitness:exerciseRepeat()`, only when `isServer()` is true or in single player [T6.23].
On a multiplayer client the same event only swaps the hand of a switching exercise and reports an animation event [T6.23] [T6.37].
`ISFitnessAction:serverStart` calls `init` and `setCurrentExercise`, then arms the rep loop with `emulateAnimEvent(netAction, period, "ActiveAnimLooped", nil)` [T6.24].
The period is per exercise: 3000 ms for squats, 1300 for push-ups and sit-ups, 2400 for burpees, 2200 for barbell curls, 1500 for the dumbbell press and 1900 for biceps curls [T6.24].
So on a dedicated server the server's own copy of the action emulates the looped animation event at that period and each loop runs one rep [T6.23] [T6.24].

`ISFitnessAction` carries `caloriesModifier = 3` [T6.25].
Its `update` sets `character:setMetabolicTarget(self.exeData.metabolics)` on every frame it runs [T6.25].
The same `update` force-stops the action on climbing, aiming, sitting on furniture, any movement key, an `ENDURANCE` moodle above the panel's threshold of 2, or the exercise's game-time end passing [T6.26].
The end is the start time plus the duration the player typed into the panel, in in-game minutes [T6.26].

Neither the fitness panel nor the action file contains a `sendClientCommand`, so the exercise reaches the server as the timed action's own net action plus the state packet, with no bus command a mod could intercept [T6.27].
A mod that wants to see reps on the server therefore reads them off the Java side — the regularity map, the soreness timers or the server-side experience grant — and not off a client command [T6.27] [T6.11].

**One rep on a dedicated server, in order.**
The server's copy of the action runs `serverStart`, which initialises the exercise map and sets the current exercise [T6.24] [T6.17].
The server's copy then emulates the looped animation event at the exercise's period [T6.24].
Each looped event reaches `animEvent` on the server, whose server arm calls `exeLooped` and so `exerciseRepeat` [T6.23].
The state packet's server handler is the one Java path to the same call, taken when the player is in the fitness state [T6.22].
Inside the rep, regularity rises, endurance falls and is pushed, soreness is seeded, the experience is granted through `GameServer.addXp`, and the last-done stamp is written [T6.8] [T6.13] [T6.11].
Twelve in-game hours after the first rep of a group, the ten-minute tick starts adding stiffness to that group's body parts [T6.15] [T6.16].
A day after the last rep of an exercise, the same tick starts taking regularity off it [T6.4].
The client, meanwhile, grants nothing, writes no endurance and fires only the animation event of each loop [T6.11] [T6.13] [T6.23].

<a id="training-signals"></a>
### Training signals: every grant of Strength or Fitness XP

Beside the rep grant stated at [the fitness object](#fitness-object), the Java grants of those two perks sit in three more methods: `IsoGameCharacter.hitConsequences`, its `IsoPlayer` override and `IsoPlayer.updateInternal2`; no Java method grants either perk for the swing itself, the two hit grants being keyed on the victim's response, and the swing grants are all Lua [T6.28].

**The hit grants.**
`IsoGameCharacter.hitConsequences` grants the attacker 2.0 Strength XP when the victim survives a non-ranged hit from a weapon whose `isKnockBackOnNoDeath()` is true [T6.29].
It goes through `GameServer.addXp` on the server and `XP.AddXP` in single player, and grants nothing on a multiplayer client [T6.29].
The `IsoPlayer` override of the same method grants the attacker 2.0 Strength on the same side split when a player is the one hit and its first boolean argument is set [T6.28].
Both hit grants are literal amounts, so neither depends on the weapon's damage [T6.28] [T6.29].

**The exhaustion roll.**
`IsoPlayer.updateInternal2` grants 1.0 Fitness XP on a `1/(300 × InvMultiplier)` roll, gated on `GameClient.client` being clear, while endurance is below `getEnduranceDangerWarning()` [T6.30].
The roll sits in the branch taken when the player has not just made a move under its own control [T6.30].
It goes through `GameServer.addXp` on a server and `XP.AddXP` in single player [T6.30].

**The melee trigger.**
`OnWeaponHitXp` has exactly two triggers: `CombatManager.attackCollisionCheck`, gated to single player by requiring both network flags clear, and `WeaponHit.process`, gated to the dedicated server by `GameServer.server` [T6.31].
On a dedicated server the chain is therefore a client swing, the hit packet, `WeaponHit.process` on the server, then the event on the server [T6.31].
A multiplayer client never fires `OnWeaponHitXp`, and a server-side handler sees every hit with the attacker, the weapon, the victim and the damage [T6.31].
Both triggers pass the attacker, the weapon, the object hit and the damage, and then the event's `hitCount` argument as the literal `1`, whatever the swing hit [T6.31] [T6.32].
How a server-side handler of this event is observed firing is stated under [Open](#open).

**The vanilla melee grants.**
The shipped handler grants melee Strength XP equal to `owner:getLastHitCount()` and melee Fitness XP of a flat `1` when endurance is above the endurance warning; neither is randomised [T6.33].
Both require a non-ranged weapon, and the Strength grant also requires a hit count above zero [T6.33].
So a sweep that hits several zombies grants Strength equal to the number of targets that swing reached, through the attacker's own last-hit count rather than the event argument [T6.32] [T6.33].
The handler lives in a `server/` file, so on a dedicated server it runs on the server and grants through the `addXp` global, stated at [perks-and-strength](../facts/perks-and-strength.md#events) [T6.31] [T6.33].
The load Strength grant of the same file's move handler is stated at [perks-and-strength](../facts/perks-and-strength.md#events), and `OnPlayerMove`'s triggers at [lua-platform](../platform/lua-platform.md#events).

**The other shipped grants.**
The same file's move handler grants 1 Fitness XP on its dice roll while the player is running or sprinting and endurance is above the endurance warning [T6.42].
The dice roll's odds per side are stated at [perks-and-strength](../facts/perks-and-strength.md#events).
The same file registers an `OnWeaponHitTree` handler that grants 2 Strength XP for a hit on a tree with any weapon but bare hands [T6.43].
Taking a wooden plank off a barricade grants 2 Strength XP in `ISUnbarricadeAction:complete`, beside 2 Woodwork XP without the multiplier [T6.44].
Dismantling a moveable grants 5 XP of its material's perk, 10 for a medium object and 15 for a large one, while the character's level in that perk is below the `LevelForDismantleXPCutoff` sandbox value [T6.45].
The `Stone` material's perk is Strength, so dismantling a stone object with a hammer is a Strength grant [T6.45].
Every one of these goes through the `addXp` global, the same route as the melee grants [T6.42] [T6.43] [T6.44] [T6.45].

**The stomp.**
A stomp is the `isAimAtFloor() && isDoShove()` branch of `attackCollisionCheck`, whose damage is `Rand.Next(0.7, 1.0) + 0.2 × Strength level` before the shoe modifiers [T6.34].
It grants no Strength XP of its own and reaches XP only through the same `OnWeaponHitXp` path [T6.34] [T6.28].

**What a training model can read.**
Taken together, a server-side mod sees a rep through the server-side grant and the fitness object, a hit through `OnWeaponHitXp`, and exhaustion through the endurance stat; nothing in the engine counts any of them for it [T6.11] [T6.31] [T6.35].
The swing's effort is also charged as endurance by the combat code, stated at [endurance-fatigue-sleep](../facts/endurance-fatigue-sleep.md).

**Which side grants what.**
Every Java grant on this page is side-split the same way: `GameServer.addXp` on a dedicated server, `XP.AddXP` in single player, nothing on a multiplayer client [T6.11] [T6.29] [T6.30].
The rep grant alone truncates its amounts to integers on the server, so a rep whose XP is fractional after `xpMod` is rounded down there and not in single player [T6.11] [T6.9].
The hit and exhaustion grants pass literal amounts of 2.0 and 1.0, which truncation would not change [T6.29] [T6.30].
The melee grants reach the server through the server-only trigger and the server-side handler, so on a dedicated server they are server grants too [T6.31] [T6.33].
A multiplayer client therefore never originates a Strength or Fitness grant from exercise, a hit, a swing or exhaustion [T6.11] [T6.28] [T6.31].

## Walls and bounds
<a id="walls"></a>

- The engine holds no per-player distance-run, running-time, sprinting-time or step counter; a jar-wide search for each of twelve names finds no class [T6.35].
- The engine holds no exercise-rep or exercise-time counter beyond the last-done timestamp the fitness object keeps per exercise type [T6.38].
- The engine holds no per-day XP accumulator and no training-load concept; a jar-wide search for six names finds no class [T6.36].
- The engine fires no Lua event per exercise rep; `EventUpdateFitness` is an animation event reported through `reportEvent`, not a Lua event [T6.37].
- The exercise object's four fields have no getters and the fitness object's decay, pain step and timer stamp are private, so a mod reads the exercise definition off its Lua table and cannot run those three steps [T6.18] [T6.20].
- Every rep and grant mechanism on this page is read from the bytecode and the shipped Lua and none is exercised on a live server [T6.22] [T6.31].

Not covered: `Fitness.save` and `Fitness.load` (which maps survive a save), the profession regularity seeding in `initRegularityMapProfession`, the soreness increment's tail after its regularity scaling, the `FitnessState` class itself, the whole of the fitness panel, the climb states as a per-event training signal, and the thermoregulator's metabolic classification of an exercising player.

## Open
<a id="open"></a>

- Whether `Fitness.update` ticks on the server for a connected player, so that regularity decays and soreness lands there — settled by a seeded exercise and two idle game-days, reading the server's regularity for the predicted fall; -> [X36](../areas/open-questions.md#x36) [#2083/C/open]
- Whether the server-side experience events `AddXP`, `LevelPerk` and `OnWeaponHitXp` fire per grant for a connected player's melee hits and exercise — settled by server-side counters on the three events after a console grant, melee hits and an exercise; -> [X39](../areas/open-questions.md#x39) [#2084/C/open]
- A decision the design takes: whether a training model reads the engine's per-exercise regularity or keeps its own, given that regularity decays only after a one-day grace, by 0.288 a day, with no floor [T6.5] [T6.4].
- A decision the design takes: whether a resistance dose counts reps through the server-side grant or through the fitness object, given that the grant is truncated to an integer and a multiplayer client grants nothing [T6.11].
- A decision the design takes: whether melee training reads the event argument or the attacker's hit count, given that both triggers pass `1` [T6.32].

## See also

- [perks-and-strength](../facts/perks-and-strength.md) — what the grants on this page do inside the XP pipeline, the events, the anti-cheat and skill rust.
- [endurance-fatigue-sleep](../facts/endurance-fatigue-sleep.md) — the endurance model the rep's cost joins.
- [character-stats](../facts/character-stats.md) — the stat registry and the updater that derives the fitness stat from the perk level.
- [perception-speed](../facts/perception-speed.md) — the movement signals a server reads, `currentSpeed` and `runningTime`.
- [mp-model](../platform/mp-model.md) — who pushes the fitness object and the player stats, and to whom.
- [wire-packets](../facts/wire-packets.md) — the fields the player-fields packet carries.
- [lua-platform](../platform/lua-platform.md#events) — the events, including `OnPlayerMove`'s triggers.
- [open-questions](../areas/open-questions.md#x36) — the experiments this page waits on.
