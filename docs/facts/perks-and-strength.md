# Perks and strength
Verified against 42.20.4 (b0bbce05d5) · 2026-09-30 · scope: the Strength and Fitness perks — the level and experience stores, every experience write and its gates, the level writes and their two events, the Java readers of the two levels, carry capacity, the experience anti-cheat, skill rust and the band-trait remap; exercise and training signals, endurance and fatigue, and the packets' field lists are handed off.

## Key facts

- A perk's level and its experience are two stores on the character, read with `getPerkLevel(perk)` and `getXp():getXP(perk)`, each answering 0 when the perk has no entry [#0918/M/n=1, #2101/C/C-only].
- Strength and Fitness cost 1500, 3000, 6000, 9000, 18000, 30000, 60000, 90000, 120000 and 150000 experience per level, 487 500 in all to reach level 10 [#2102/C/arith.].
- `AddXP` discards any non-negative amount once a perk's experience has reached the level-10 total and clamps the stored experience between 0 and that total [#2109/C/C-only].
- A Fitness amount is dropped whole, a negative one included, whenever `Nutrition.canAddFitnessXp()` answers false; the gate names Fitness alone and never touches Strength [#2111/C/C-only].
- A Strength amount is multiplied by 1.5 while the protein store is strictly between 50 and 300 and by 0.7 while it is below −300, with no sandbox guard [#2112/C/C-only].
- The two-, three- and four-argument `AddXP` overloads do nothing on a dedicated server, because each returns unless the player is local and no player is local on a server [#2105/C/C-only].
- The `addXp(player, perk, amount)` global routes to `GameServer.addXp` on a server and does nothing at all on a multiplayer client [#2130/C/C-only].
- The Lua event `AddXP` fires only where `GameClient.client` is false, so never on a multiplayer client [#2125/C/C-only].
- Strength multiplies melee damage by 0.80 at level 1 rising 0.05 a level to 1.25 at level 10, and by 0.75 at level 0 [#2135/C/C-only].
- Carry capacity is the base maximum weight times the Strength weight multiplier, less the moodle penalty, floored at 0, then times the player's `maxWeightDelta` [#0513/M/n=1, #2142/C/C-only].
- `setMaxWeightBase` and `setMaxWeightDelta` have no caller in the jar and are re-read on every recompute, so a mod can own carry capacity without moving the level [#2143/C/C-only].
- The server's anti-cheat flags a perk whose experience rose by more than `1000 × multiplier × boost` between two checks [#2147/C/C-only].
- Skill rust begins about 13.9 in-game days after a timer at 0, and about 48.6 after the −50000 default, with no Strength or Fitness gain [#2155/C/arith.].
- Strength and Fitness levels become band traits in shipped Lua on the `LevelPerk` event, and level 5 gets no trait in either ladder [#2157/C/C-only].

## How it works

<a id="stores"></a>
### Level and experience, two stores

A perk's level is `PerkInfo.level` in the character's perk list, read with `getPerkLevel(perk)`, which answers 0 when the character holds no entry for the perk [#2101/C/C-only].
Its experience is a float in the experience object's per-perk map, read with `getXp():getXP(perk)`, which answers 0 when the map has no entry [#2101/C/C-only].
Reading the experience takes two calls and never one, and a level the server sets reaches the client's next read [#0918/M/n=1].
No level setter writes experience, and no experience write moves the level except through the threshold crossings under [#level-writes](#level-writes) [#2117/C/C-only] [#2119/C/C-only] [#2122/C/C-only].
A mod that writes one store therefore leaves the other where it was, and the pair can disagree until the mod writes both [#2103/C/C-only] [#2119/C/C-only].

Strength and Fitness share one threshold ladder: `PerkFactory.init` declares the second column for both, and `AddPerk` multiplies every declared threshold by 1.5 before it stores it, so the cost of each level and the cumulative total needed to reach it are these [#2102/C/arith.].

| Level | Declared | Cost of the level | Cumulative |
|---|---|---|---|
| 1 | 1000 | 1500 | 1500 |
| 2 | 2000 | 3000 | 4500 |
| 3 | 4000 | 6000 | 10500 |
| 4 | 6000 | 9000 | 19500 |
| 5 | 12000 | 18000 | 37500 |
| 6 | 20000 | 30000 | 67500 |
| 7 | 40000 | 60000 | 127500 |
| 8 | 60000 | 90000 | 217500 |
| 9 | 80000 | 120000 | 337500 |
| 10 | 100000 | 150000 | 487500 |

`getTotalXpForLevel(n)` sums the per-level costs from the first level to the n-th, skipping any entry of −1, and it is the cumulative column every threshold test on this page reads [#2102/C/arith.].
`getXpForLevel` answers −1 for any level outside 1 to 10, so `getTotalXpForLevel` of any level above 10 equals the level-10 total and the Java ladder has no rung past 10 [#2859/C/C-only].

`XP.setXPToLevel(perk, level)` writes the experience map to that level's cumulative total and leaves the perk level untouched, firing no event [#2103/C/C-only].
Its one other write, the Fitness stat, sits behind `Core.debug` and so never runs on a release server [#2103/C/C-only].
`IsoGameCharacter.applyTraits` seeds both Strength and Fitness at level 5 before it applies the chosen traits' offsets [#2104/C/C-only].
It then raises each perk to its target through `LevelPerk`, one step at a time, and calls `setXPToLevel` so the experience matches the level [#2104/C/C-only].
Because it levels through `LevelPerk`, character creation fires the level event once per step, and the event's band-trait writes land then [#2104/C/C-only] [#2127/C/C-only].
The default fixture's admin starts with Strength experience 37500, level 5's total, at level 5 [#2874/M/n=1].

<a id="xp-grants"></a>
### Experience grants and their gates

The experience object declares `AddXP` in six overloads, and which one a caller reaches decides whether anything happens on a dedicated server.
The two-, three- and four-argument overloads return at once unless the character is an `IsoPlayer` whose `isLocalPlayer()` answers true [#2105/C/C-only].
`isLocalPlayer()` answers false unconditionally whenever `GameServer.server` is set, so on a dedicated server all three do nothing for every player [#2105/C/C-only].
The five-argument overload forwards straight to the six-argument one, which holds the body, so those two are the only overloads that reach it with no local-player gate [#2106/C/C-only].
The six-argument body reads only its second and fourth booleans: the second gates the whole trait, multiplier and sandbox block and the fourth gates the halo text, while the first and third are never read [#2107/C/C-only].
The sixth overload, `AddXP(HandWeapon, int)`, is declared with a bare `return` for a body [#2108/C/C-only].

The six-argument body runs these steps in this order, and each gate returns before any experience is written [#2161/C/C-only] [#2107/C/C-only] [#2109/C/C-only] [#2111/C/C-only] [#2112/C/C-only] [#2114/C/C-only] [#2122/C/C-only] [#2123/C/C-only] [#2125/C/C-only]:

```
IsoGameCharacter$XP.AddXP(perk, amount, b1, b2, b3, b4)
  @0–@10       isAsleep()                                   -> return, the amount dropped
  @63–@106     Fitness, IsoPlayer, !canAddFitnessXp()       -> return, the amount dropped
  @107–@171    Strength, IsoPlayer, 50 < proteins < 300     -> amount *= 1.5
  @172–@190    Strength, IsoPlayer, proteins < -300         -> amount *= 0.7
  @198–@221    amount >= 0 and xp >= totalXpForLevel(10)    -> return
  @225         b2 false                                     -> skip the trait, multiplier and sandbox block
  @824–@861    xp = clamp(xp + amount, 0, totalXpForLevel(10)); amount = the change made
  @963–@1116   crossing totalXpForLevel(level + 1) upward   -> LevelPerk, looping below 10
  @1119–@1193  crossing totalXpForLevel(level) downward     -> LoseLevel, looping
  @1196–@1250  Fitness, IsoPlayer                           -> FITNESS stat = level / 5 - 1
  @1271        b4 true                                      -> halo text
  @1346–@1364  GameClient.client false                      -> Lua event AddXP(chr, perk, amount)
```

The first gate is sleep: the body returns before anything else when the character `isAsleep()`, so every amount to a sleeping character is dropped, whatever the perk and whatever the caller [#2161/C/C-only].
The Fitness gate: when the perk is `Perks.Fitness` and the character is an `IsoPlayer`, a false `Nutrition.canAddFitnessXp()` returns before any multiplier, so the whole amount is dropped, a negative one included [#2111/C/C-only].
The gate names the Fitness perk alone, so no Strength amount is ever dropped by it [#2111/C/C-only].
The predicate's thresholds, which read the weight-band traits, are stated at [body-and-weight.md#weight-traits](body-and-weight.md#weight-traits).

The protein branch: when the perk is `Perks.Strength` and the character is an `IsoPlayer`, a protein store strictly between 50 and 300 multiplies the amount by 1.5, and a protein store below −300 multiplies it by 0.7 [#2112/C/C-only].
The two tests run one after the other rather than as alternatives, and no sandbox option guards either [#2112/C/C-only].
Both thresholds lie inside the protein store's clamp range, so both arms are reachable in play; neither is exercised on a live server [#0023/M/n=2, #2112/C/C-only].
The branch reads the protein store of whichever side runs the body, and which side that is for a connected player's grants is under [## Open](#open).
SkillRecoveryJournal ships a protein-keyed multiplier of the same shape for its own exercise grants, a copy of this vanilla branch [#1584].
Protein's other reader outside the weight model, the recovery multiplier, and why its protein arms never fire under the store's clamp, are stated at [nutrition-core.md#macro-effects](nutrition-core.md#macro-effects).

The cap: `AddXP` discards any non-negative amount once the perk's experience has reached `getTotalXpForLevel(10)` [#2109/C/C-only].
Past that test it clamps the stored experience into the range from 0 to the same total and rewrites the amount it reports to the change it made [#2109/C/C-only].
The quarter rate: when the multiplier block runs, a perk absent from the character descriptor's experience-boost map earns at a multiplier of 0.25 unless it is excluded from speed reduction [#2110/C/C-only].
The exclusion names Sprinting, Fitness and Strength, so neither of this page's perks ever earns at the quarter rate [#2110/C/C-only].
`XP.getMultiplier(perk)` answers 0.0, not 1.0, when the perk has no multiplier entry, and `AddXP` applies the multiplier only when it is strictly greater than 1, so an absent entry changes nothing [#2113/C/C-only].
At the end of every Fitness amount that reaches the store, whether or not a level changed, `AddXP` writes `CharacterStat.FITNESS` as the Fitness level divided by 5, less 1 [#2114/C/C-only].
The private method that carries the same formula is stated at [character-stats.md#updaters](character-stats.md#updaters).

Shipped Lua grants on top of the Java grants, all through the `addXp` global from the install's server file `XpUpdate.lua`.
Its dice roll `xpUpdate.randXp()` succeeds on a roll of 1 in 100 times the inverse time multiplier when `isServer()` is true, and 1 in 700 times it otherwise [#2115/C/C-only].
On the move event it grants 2 Strength experience on a `randXp()` roll whenever the inventory weight exceeds half the maximum weight, with no requirement to be moving fast [#2116/C/C-only].
Which side fires the move event is stated at [lua-platform.md#events](../platform/lua-platform.md#events).
The melee, tree, exercise and endurance-warning grants are stated at [exercise-and-training.md#training-signals](exercise-and-training.md#training-signals).
For a server-side grant the protein branch reads the server's store, with the client's store having just answered 200 and reverting within a second [#2872/M/n=1].

<a id="level-writes"></a>
### Level writes

Outside a load of the whole experience object, a perk level is written by four methods and no others: `LevelPerk`, `LoseLevel`, `setPerkLevelDebug` and `level0` [#2117/C/C-only].
`level0` has no caller anywhere in the jar, and `setPerkLevelDebug`'s only Java callers are two debug windows that bind it to a slider, so both exist for Lua and the debug tools [#2117/C/C-only].
`LevelPerk(perk)` raises the level by one and clamps it to 10 [#2118/C/C-only].
It throws on `Perks.MAX` and on a nil perk [#2118/C/C-only].
`LoseLevel(perk)` lowers the level by one, with the floor and the event it fires stated under [#events](#events).

`setPerkLevelDebug(perk, n)` writes `PerkInfo.level`, minting the entry when the perk has none, and does nothing else [#2119/C/C-only].
It neither reads nor writes experience and fires no `LevelPerk` event, and its only push is `GameClient.sendPerks`, taken on a client alone [#2119/C/C-only].
On a dedicated server it is therefore a bare field write, and the server's periodic experience push to the owning client, stated on [mp-model.md](../platform/mp-model.md#sync-globals), is what carries the new level down.
`level0(perk)` sets the level to zero and fires no Lua event and sends no packet [#2120/C/C-only].
Run on a client, `LevelPerk` and `setPerkLevelDebug` send `SyncPerks`, but `LoseLevel` sends it only for `Perks.Sneak` [#2121/C/C-only].
What `SyncPerks` carries is stated on [wire-packets.md](wire-packets.md#experience-packet).

`AddXP` calls `LevelPerk` when the running total crosses `getTotalXpForLevel(level + 1)`, the total before the amount below that threshold and the total after it at or above, and it loops while the level stays below 10 [#2122/C/C-only].
The level-down test is the mirror crossing on `getTotalXpForLevel(level)` and calls `LoseLevel` [#2123/C/C-only].
Both directions are crossing tests, so a level a mod lowers is neither walked back up nor pushed further down by the experience system, and the mod owns it from its first write [#2123/C/C-only].
The one absolute test is Lua: `xpUpdate.checkForLosingLevel` calls `LoseLevel` whenever the perk's experience is below the cumulative requirement of its stored level, for a stored level from 1 to 10 [#2124/C/C-only].
It runs only for Strength and Fitness, only from the ten-minute rust pass, and only on a tick where that perk's rust timer is above 20000 and has entered a new 1200-unit bucket [#2124/C/C-only].
A level written above the experience it implies is therefore pulled down one step per rust step, and not on every ten-minute tick [#2124/C/C-only].
Each such step fires the level event with a gained flag of false and so rewrites the band traits [#2127/C/C-only] [#2157/C/C-only].
On a dedicated server a level-only `setPerkLevelDebug` write below the experience-implied level holds: Strength written from 5 to 3 with 37600 experience stayed at 3 on the server for 30 s of reads and the owning client read 3 within 2 s of the request [#2867/M/n=1]. An admin client's `SyncXp` sent while the client mirrored that level left it and the experience unchanged and fired no event, which does not show what a sync carrying a different level would do [#2869/M/n=1].

<a id="events"></a>
### The two events and the grant route

`AddXP` fires the Lua event `AddXP` only when `GameClient.client` is false, so it never fires on a multiplayer client and does fire on a dedicated server [#2125/C/C-only].
Its arguments are the character, the perk and the amount as a `Float`, the amount being the final one, after every multiplier and the clamp [#2126/C/C-only].
`LoseLevel` lowers the level by one, floored at 0, and the `LevelPerk` event fires after the level write from `LevelPerk` with a gained flag of true and from `LoseLevel` with false, and neither carries a side gate [#2127/C/C-only].
`LevelPerk` fires it with four arguments — the character, the perk, the new level as an `Integer` and a `Boolean` — from both of its branches, and the fourth argument is the constant true whatever the method's own boolean parameter [#2128/C/C-only].
The event's listener in the server file `XpUpdate.lua` does four jobs: it re-checks the auto-learned craft recipes, rewrites the Strength band traits, rewrites the Fitness band traits, and learns the Farming, Mechanics and Electricity recipes at high levels [#2129/C/C-only].
A level written without firing the event leaves all four stale [#2129/C/C-only].
A grant a client syncs up to the server fires neither event there, because the receiver loads the whole experience object in place of calling `AddXP`, as [wire-packets.md](wire-packets.md#experience-packet) and [mp-model.md](../platform/mp-model.md#sync-globals) state.

The `addXp(player, perk, amount)` global returns at once unless `player:isExistInTheWorld()` answers true [#2131/C/C-only].
It then routes to `GameServer.addXp` when `GameServer.server` is set and does nothing at all on a multiplayer client [#2130/C/C-only].
`GameServer.addXp` returns when no connection holds the player, when `canModifyPlayerStats` fails, and for a nil or dead player [#2133/C/C-only].
`canModifyPlayerStats` passes when the connection's role holds `CanModifyPlayerStatsInThePlayerStatsUI` or when the connection owns that player, so a server-side grant to a connected player's own character always passes [#2134/C/C-only].
Past its gates, `GameServer.addXp` calls the six-argument `AddXP` with the no-multiplier flag inverted into the second boolean, the third set and the halo flag fourth, so it never meets the local-player gate [#2132/C/C-only].
It then refreshes the anti-cheat's experience snapshot through `updateXpChecker` [#2132/C/C-only].
A grant through `addXp` on the server therefore fires the `AddXP` event there unless the character is asleep, and the `LevelPerk` event too when it crosses a threshold [#2161/C/C-only] [#2125/C/C-only] [#2130/C/C-only].
The `AddXP` Lua event fires on the server for every `addXp` grant, with the amount and the current (even debug-written) level, and for the rust step's -1 [#2871/M/n=1].
`LevelPerk` fires on the server once per level crossed, up or down, and vanilla's band listener remaps on both [#2895/M/n=1][#2084/M/n=1].

<a id="readers"></a>
### The Java readers of the two levels

The ladders below read `getPerkLevel` live on every call, so a level write takes effect at the next call, and no method caches the level or exposes the multiplier for a write [#2135/C/C-only] [#2159/C/C-only].
Strength sets the melee-damage and shove multipliers on one ladder and the carry-weight multiplier on another, Fitness sets the weapon endurance-cost multiplier, and level 0 is each method's fallthrough [#2135/C/C-only] [#2136/C/C-only] [#2137/C/C-only] [#2138/C/C-only]:

| Level | Hitting and shoving (Strength) | Carry weight (Strength) | Weapon endurance cost (Fitness) |
|---|---|---|---|
| 0 | 0.75 | 0.80 | 1.00 |
| 1 | 0.80 | 0.90 | 0.95 |
| 2 | 0.85 | 1.07 | 0.92 |
| 3 | 0.90 | 1.24 | 0.89 |
| 4 | 0.95 | 1.41 | 0.87 |
| 5 | 1.00 | 1.58 | 0.85 |
| 6 | 1.05 | 1.75 | 0.83 |
| 7 | 1.10 | 1.92 | 0.81 |
| 8 | 1.15 | 2.09 | 0.79 |
| 9 | 1.20 | 2.26 | 0.77 |
| 10 | 1.25 | 2.50 | 0.75 |

`getHittingMod` has one caller, `CombatManager.attackCollisionCheck`, which reads it on every hit [#2135/C/C-only].
`getShovingMod` is read by `processHitDamage` and by the weapon's stagger-back time [#2136/C/C-only].
`getWeightMod` feeds the carry-capacity formula under [#carry-capacity](#carry-capacity) [#2137/C/C-only].
`getFatigueMod` scales the endurance a weapon swing costs [#2138/C/C-only].
The pacing and recovery ladders, which scale endurance drain and regeneration by Fitness, are stated at [endurance-fatigue-sleep.md#regen](endurance-fatigue-sleep.md#regen).
Combat speed adds 0.02 per Fitness level before the whole chain is clamped to the range 0.8 to 1.6 [#2139/C/C-only].
The rest of combat speed's chain is stated at [perception-speed.md#combat](perception-speed.md#combat).
The weight-band traits enter many of the same methods as terms of their own, tabled at [body-and-weight.md#weight-traits](body-and-weight.md#weight-traits) [#0541/C/C-only].

Every combat muscle-strain term is multiplied by `(15 − StrengthLevel) / 10`, the stomp, the shove and the aimed firearm alike, so strain falls as Strength rises [#2140/C/C-only].
Muscle strain is `BodyPart.stiffness`, a float per body part with public `getStiffness`, `setStiffness` and `addStiffness` [#2141/C/C-only].
`IsoGameCharacter` adds to it through seven public adders: `addCombatMuscleStrain` and the arm, left-arm, both-arm, back, neck and right-leg helpers [#2141/C/C-only].
The one reader of another player's Strength level is the crit-chance term, stated under [walls](#walls).

<a id="carry-capacity"></a>
### Carry capacity

`BodyDamage.UpdateStrength` sets the maximum weight to `(int)(getMaxWeightBase() × getWeightMod())` less a moodle penalty and floors the result at 0 [#2142/C/C-only].
For a player it then multiplies that by `getMaxWeightDelta()` and truncates again [#2142/C/C-only].
Because the delta multiplies after the floor, a delta of 0 zeroes carry capacity whatever the Strength level [#2142/C/C-only].
The moodle penalty's terms are stated at [body-and-weight.md#moodles](body-and-weight.md#moodles) [#0513/M/n=1].
`setMaxWeightBase(int)` and `setMaxWeightDelta(float)` are public, have no caller anywhere in the jar, and are re-read on every recompute, and `maxWeightDelta` itself is confined to `IsoPlayer` [#2143/C/C-only].
A mod can therefore own carry capacity through those two setters without touching the perk level; neither setter is exercised from Lua on a live server [#2143/C/C-only].
No vanilla Lua file calls either setter: every `setMaxWeight` in the install's `media/lua` is a fish configuration's own method [#2162/C/snapshot].
The STRONG, WEAK, FEEBLE and STOUT traits reach `maxWeightDelta` only in the two `IsoPlayer` constructors, as 1.5, 0.75, 0.9 and 1.25 [#2144/C/C-only].
A Strength level change that swaps those traits therefore never refreshes the delta, and a mod that owns it fights nothing in the jar [#2144/C/C-only].
A Lua write to `setMaxWeight` lasts only until the next body-damage update, because the recompute calls the same setter [#2145/C/C-only].
`setUnlimitedCarry` removes the limit but is contested: the save load, the role setter and both arms of the extra-info packet write it [#2146/C/C-only].

<a id="anti-cheat"></a>
### The experience anti-cheat

On the server, `AntiCheatXPUpdate.isPerkXpGrowthRateTooHigh` flags a perk whose experience rose by more than `1000 × getMaxPerkXpMultiplier × getMaxPerkXpBoostMultiplier` since the last check [#2147/C/C-only].
When it trips it logs the perk, the growth and both multipliers as a multiplayer error [#2147/C/C-only].
The bound is per perk and per check, so a steady trickle of small grants never trips it as long as each interval's growth stays under the bound [#2147/C/C-only].
The boost multiplier resolves to 1.0, 1.33, 1.66 or 0.25 by the perk's boost [#2149/C/C-only].
Its Fast Learner widening applies only to perks outside the physical category, so it never widens Strength or Fitness [#2149/C/C-only].
`AntiCheatXPUpdate.update` returns true at once when the check is disabled, and otherwise walks the connection's players and fails on the first one that trips [#2150/C/C-only].
A failing check makes `AntiCheat.update` call `act(connection, "update failed")`, which logs, kicks or bans the user, unless the connection is a delayed disconnect [#2148/C/C-only].
A grant through `GameServer.addXp` refreshes the checker's snapshot after it lands [#2132/C/C-only].
Each player is checked at most once per 60000 ms, by a limiter that steps one interval at a time [#2860/C/C-only], from the server's main loop, which skips the check while the server fast-forwards time [#2861/C/C-only].
The growth is the rise since the checker's stored value, so a fall never trips it, and only `XP.load`, `GameServer.addXp` and the console `addxp` re-seed that value, while `setXPToLevel` and a direct `AddXP` do not [#2862/C/C-only].
The multiplier is never below 1, so a Strength with no boost at the default sandbox trips above 250 per check [#2863/C/C-only].
The check is the server option `AntiCheatXP`, whose values 1 to 4 are ban, kick, log and disabled, defaulting to kick [#2864/C/C-only].
A trip is acted on only for a connection whose role lacks `CantBeKickedByAnticheat`: it is counted and logged, and outside debug mode the second trip before the count decays, by 1 every 150 s, bans at value 1 and kicks at value 2 [#2865/C/C-only].
The admin, moderator, gm and observer roles hold that capability, so only a user or priority connection can be kicked or banned by the check [#2866/C/C-only].
On the admin connection a checker-free 1000-experience burst drew no kick and no line under `AntiCheatXP=2` [#2873/M/n=1]; whether it trips for a non-admin connection is open [#2085/C/open].
Whether a server-side burst trips the check on a live server is under [## Open](#open).

<a id="skill-rust"></a>
### Skill rust

The engine has no Java skill-rust or experience-decay mechanism: the Strength and Fitness decay is the ten-minute pass of the server file `XpUpdate.lua`, which walks the online players when `isServer()` is true and the local players otherwise [#2151/C/C-only].
For each perk it credits −1 experience each time the rust timer, once above 20000, enters a new 1200-unit bucket, but only while the perk's experience is above 0, and then runs the level check under [#level-writes](#level-writes) [#2151/C/C-only].
It resets the timer to 0 once the timer passes 31000 [#2151/C/C-only].
The pass's state is four keys in the player's modData — `strengthUpTimer`, `strengthMod`, `fitnessUpTimer` and `fitnessMod` — each timer defaulting to −50000 and each bucket to 0 [#2152/C/C-only].
`getLoosingXpValue()` answers −1 and `getLoosingXpTick()` answers 10, or −100 and 30000 under the debug `fastLooseXp` cheat [#2153/C/C-only].
So rust removes one experience point per step, on a timer that rises by 10 per ten in-game minutes [#2154/C/C-only].
From a timer at 0, where the reset leaves it, rust begins after about 13.9 in-game days with no gain in that perk, and from the −50000 default and floor after about 48.6 [#2155/C/arith.].
Every positive Strength or Fitness amount on the `AddXP` event subtracts 3000 from that perk's timer, floored at −50000 [#2156/C/C-only].
Because the `AddXP` event never fires on a multiplayer client, the 3000 subtraction runs on the server alone [#2125/C/C-only] [#2156/C/C-only].
The pass's local-players arm runs in any Lua state that loads the file, so a connected client's own copy of the timers may rise without the subtraction and run `LoseLevel` on its copy of the level; whether the pass fires in a connected client's state is unmeasured [#2151/C/C-only].
A rust step forced by writing the timer to 30000 took one experience and left a level written below its experience-implied level untouched [#2868/M/n=1].

<a id="trait-remap"></a>
### The band-trait remap

On the `LevelPerk` event the listener removes WEAK, FEEBLE, STOUT and STRONG and adds WEAK at Strength 0 to 1, FEEBLE at 2 to 4, STOUT at 6 to 8 and STRONG at 9 or more [#2157/C/C-only].
For Fitness it removes UNFIT, OUT_OF_SHAPE, FIT and ATHLETIC and adds them on the same bands, and level 5 gets no trait in either ladder [#2157/C/C-only].
The mapping is shipped Lua and so replaceable, and because it removes all four traits before it adds one, it also strips a band trait another mod granted for its own reason [#2157/C/C-only].
Both vanilla handlers that move a Strength or Fitness level or its traits outside Java are registered by the server file `XpUpdate.lua`, the `LevelPerk` listener and the ten-minute rust pass, so the level a mod's clamp reads can move on the ten-minute tier as well as on a grant [#2158/C/C-only].
A level written through `setPerkLevelDebug` or `level0` fires no event, so the band traits keep whatever the last real level change set [#2119/C/C-only] [#2120/C/C-only] [#2129/C/C-only].
The band traits are also what the player constructor turned into `maxWeightDelta`, and a later swap does not refresh it, as [#carry-capacity](#carry-capacity) states.
A load of the experience object replaces the character-trait list along with the levels, as [wire-packets.md](wire-packets.md#experience-packet) states, and how a trait change reaches the client is on [mp-model.md](../platform/mp-model.md#sync-globals).
A server debug level write runs no remap: Strength written to 3, FEEBLE's band, never gained FEEBLE on either side and counted no `LevelPerk` [#2870/M/n=1].

## Walls and bounds
<a id="walls"></a>

Every row this page owns is a reading of the jar or of the install's shipped Lua for build `42.20.4`, and none of it is exercised on a live server.
The engine has no lean-mass, fat-mass or aerobic-capacity field and no effective-strength concept: no setter overrides a Strength-derived modifier, and no Strength or Fitness level setter exists besides the generic perk methods [#2159/C/C-only].
`remoteStrLvl` and `remoteFitLvl` are public fields with no getter, so Lua cannot read either; the first's one reader is the crit-chance term against another player and the second has no reader at all [#2160/C/C-only].
The Fitness stat's own refresher is private and cannot be called from Lua, as [character-stats.md#updaters](character-stats.md#updaters) states.
Knockback and combat speed have no Lua-writable modifier, as [perception-speed.md#combat](perception-speed.md#combat) states.

Not covered: the body of `AddXPHaloText`; the wire encoding of a perk id inside the experience object; the global level counter and its `LevelUpLevels` table; `getLevelUpMultiplier` and its effect on the per-level cost; the tails of the door, climb, defence, window-lunge, landing, jam and animal-pickup readers of the two levels.

## Open
<a id="open"></a>

- What is the experience anti-cheat's check interval, and does a server-side burst of grants trip it? — settled by timed server-side bursts either side of the bound, the desk half being read [#2860/C/C-only] [#2865/C/C-only]; -> [X40](../areas/open-questions.md#x40) [#2085/C/open]
- Which side evaluates the Strength experience protein branch for a connected player, and against which side's protein value? — settled by melee hits with the protein store raised on one side at a time; -> [X48](../areas/open-questions.md#x48) [#2087/C/open]
- Decision: which overload a dedicated server reaches for a connected player's combat experience decides where the protein branch and the Fitness gate evaluate — every server-side grant reaches the six-argument body through `GameServer.addXp`, while no client-side overload reaches it at all [#2105/C/C-only] [#2132/C/C-only].
- Decision: how large a single server-side grant the mod issues, given that a flagged check can kick or ban a user connection at the default option [#2147/C/C-only] [#2148/C/C-only] [#2865/C/C-only].
- Decision: whether the mod owns the vanilla protein store, given that the Strength branch reads it directly and fires on vanilla's number otherwise [#2112/C/C-only].
- Decision: whether the mod moves Strength through the level or through the carry setters and the level together, given that every Java reader but carry capacity reads the level alone [#2135/C/C-only] [#2143/C/C-only].

## See also

- [body-and-weight.md#weight-traits](body-and-weight.md#weight-traits) — the Fitness gate's predicate and every weight-band reader.
- [nutrition-core.md#macro-effects](nutrition-core.md#macro-effects) — the protein store's other reader and its clamp.
- [exercise-and-training.md](exercise-and-training.md) — the exercise object, the Java and Lua training grants and their triggers.
- [endurance-fatigue-sleep.md](endurance-fatigue-sleep.md) — the Fitness pacing and recovery ladders and endurance itself.
- [character-stats.md](character-stats.md) — the stat registry and the updaters, the Fitness stat's refresher among them.
- [wire-packets.md](wire-packets.md) — what the experience and perk packets carry.
- [../platform/mp-model.md](../platform/mp-model.md) — who sends the experience push and the trait block, when and to whom.
- [../platform/lua-platform.md#events](../platform/lua-platform.md#events) — the move event's triggers and the event names.
- [other-mods/catalog.md#sweep](other-mods/catalog.md#sweep) — the workshop mod that copies the protein branch.
- [../reference/experiments.md](../reference/experiments.md) — the costed experiments and their riders.
