# Endurance, fatigue, sleep and recovery — a jar reading

Read from one jar of build `42.20.4` (`b0bbce05d5`) on 2026-09-27, with `pz.sh grep|methods|dump` plus a session-scoped scratch parser (rebuilt from the toolchain's own `cp.py`/`dis.py`) for access flags, per-method reference scans and `tableswitch` tables. Every fact below carries a `Class.method @off L<n>` cite or a named jar-wide grep. Nothing here was measured on a live session.

## Summary for the design

`CharacterStat` is not a Java enum — it is a registry of 24 stats built in a static initialiser, each carrying an id, a minimum, a maximum and a default, and `CharacterStat.register` is `public static` on a class the exposer holds, so a mod can mint its own stat; but `ORDERED_STATS` is a fixed 24-entry array built in that same initialiser, and every save, every packet write and `SyncPlayerStatsPacket.getBitMaskForStat` walk that array, so a mod-registered stat is neither synced nor overwritten by the 1 Hz snapshot. Endurance and fatigue are both in `ORDERED_STATS` (indices 3 and 4), so both ride the once-a-second full snapshot and a client write to either is erased; the range `[0,1]` is fixed on the `CharacterStat` instance and there is no setter for the minimum or the maximum. The single most consequential finding is the `CalculateStats` Lua hook: `IsoGameCharacter.calculateStats` fires `LuaHookManager.TriggerHook('CalculateStats', this)` and returns early when it comes back true, `CalculateStats` is one of the eight hooks registered into the Lua `Hook` table, and `Event.trigger` returns true whenever the callback list is non-empty regardless of what the callback returns — so registering any `Hook.CalculateStats.Add(fn)` handler replaces the whole vanilla stat update (endurance, thirst, wake-state hunger and fatigue, stress, morale, fitness) for every character, which is both exactly the door the design wants and a footgun that also stops hunger and thirst. The one thing that hook cannot stop is the fatigue reset, which sits two instructions earlier: on a server, when sleep is not both allowed and needed, `calculateStats` calls `Stats.reset(FATIGUE)` every tick, so on a default dedicated server fatigue is pinned at 0 and any mod-side fatigue write is wiped within a tick. `IsoPlayer.calculateStats` returns immediately on a game client, so for a player the whole stat update including that reset is server-only. Endurance has two separate updaters that are not overrides of each other — both are private, `IsoGameCharacter.updateEndurance` (reached from `calculateStats`, and doing nothing but stamping `lastEndurance` and honouring the unlimited-endurance cheat) and `IsoPlayer.updateEndurance` (reached from `updateInternal2`, and holding the whole drain and regen model) — and the player one returns early on a client and for animals. The drain is `ZomboidGlobals` rates (running 5.2e-5, sprinting and dragging 4.55e-4, immobile regen 3.1e-5, all three loaded from `media/lua/shared/defines.lua`) times a weight-trait and Athletic multiplier, times a 2.3 or 3.0 constant, times `getPacingMod` (a Fitness ladder 0.8 down to 0.43), times `getHyperthermiaMod`, times an Asthmatic term, times `GameTime.getMultiplier()` and a heavy-load ladder — and unlike hunger, thirst and fatigue it carries no `deltaMinutesPerDay` factor, so endurance rates do not scale with day length. Regen is `imobileEnduranceReduce × SandboxOptions.getEnduranceRegenMultiplier() × getRecoveryMod() × (1 − 0.85·fatigue)` standing still, a quarter of that walking, five times it sitting or in a vehicle, and twice it asleep (times `deltaMinutesPerDay` when every player is asleep) — so fatigue already gates endurance recovery, and `getRecoveryMod` is the single multiplier the design should aim at because it already multiplies every regen arm. `getRecoveryMod` already has protein and lipid branches, times 0.5 below −1000 and times 0.2 below −1500, and they are unreachable only because the setters clamp both stores at −500 — a nutrition mod that wants protein to gate recovery is re-implementing a hook the engine already designed and then clamped out of existence. Fatigue accumulates awake as `fatigueIncrease (3.45e-5) × StatsDecrease × max(0.3, 1 − endurance) × multiplier × deltaMinutesPerDay × sleepTrait × Thermoregulator.getFatigueMultiplier() ÷ restMod`, so endurance already drives fatigue, heat already raises it, and sitting divides it by 1.5; sleep removes fatigue over a nominal 5 hours down to 0.3 and 7 hours below that, scaled by bed type, Insomniac, Night Owl and the sleep traits, and `ZomboidGlobals.sleepFatigueReduction` is loaded and then read by nothing in the jar. Everything endurance and fatigue do to movement and combat goes through moodle levels, not through the stats: the `ENDURANCE` moodle costs 0.15 of base speed and 0.07 of combat speed per level, the `TIRED` moodle (thresholds 0.6/0.7/0.8/0.9 on fatigue) costs a firearm to-hit penalty of 2.5 per level and multiplies stomp power by 0.5/0.2/0.1/0.05, and each side recomputes its own moodles from its own stats copy — so a server-side stat write reaches the client's speed and combat numbers for free once the snapshot lands, with no packet work. There is no `setEnduranceRegenMod`, `setFatigueMod`, `setRecoveryMod`, `setWalkSpeedModifier`, `setNimbleMod`, `setPacingMod` or `setAttackDelay` anywhere in the jar; the writable speed levers on the character are `setSpeedMod`, `setStaggerTimeMod`, `setSneakLimpSpeedScale`, `setPathSpeed`, `setLevelUpMultiplier`, `IsoPlayer.setMoveSpeed` and `IsoPlayer.setCombatSpeed`, and `updateSpeedModifiers` overwrites `runSpeedModifier`, `walkSpeedModifier` and `combatSpeedModifier` from worn items every time the server syncs damage, so those three fields are not a place to park a value. The one server-to-client carrier for movement speed is `PlayerInjuriesPacket`, which writes `IdleSpeed`, `StrafeSpeed`, `WalkInjury` and `NetworkPlayerAI.walkSpeed`/`runSpeed` — the server computes walk and run speed and copies them into `NetworkPlayerAI`, and the client reads them straight back out instead of computing its own, so a server-side speed change does cross the wire. The Thermoregulator is in the exposer's class set, it already reads `Nutrition.getWeight()` as a fatness term on `[-1, +1]` that is zero at about 93.8 kg and moves every node's heat delta by up to ±20 per cent in both directions, and it already reads hunger, fatigue and thirst through `getEnergy` and `getBodyFluids` — so body fat already insulates in vanilla, and the only writable knobs on it are `setMetabolicTarget` and a static `setSimulationMultiplier`, with no insulation setter of any kind. Finally, food and fluids already carry `EnduranceChange` and `FatigueChange`: `IsoGameCharacter.Eat` writes both into `Stats` and then sends a `SyncPlayerStatsPacket` whose mask includes endurance and fatigue, and no vanilla item script sets `EnduranceChange` at all, so that field is free space for the item pass.

## A — the stat enum and the `Stats` API

`CharacterStat` is a plain class with a `HashMap` registry, not a Java enum: `CharacterStat.<clinit> @0 L11` creates `REGISTRY`, then twenty-four `register(id, min, max, default)` calls fill the static fields, and `@290 L36` builds `ORDERED_STATS` as a 24-element array in the order below, stored at `@457`.

| Stat field | id string | min | max | default | `ORDERED_STATS` index | in the 1 Hz packet? | cite |
|---|---|---|---|---|---|---|---|
| `ANGER` | `Anger` | 0 | 1 | 0 | 0 | yes | `CharacterStat.<clinit> @10 L12` |
| `BOREDOM` | `Boredom` | 0 | 100 | 0 | 1 | yes | `CharacterStat.<clinit> @21 L13` |
| `DISCOMFORT` | `Discomfort` | 0 | 100 | 0 | 2 | yes | `CharacterStat.<clinit> @33 L14` |
| `ENDURANCE` | `Endurance` | 0 | 1 | **1** | 3 | yes | `CharacterStat.<clinit> @45 L15` |
| `FATIGUE` | `Fatigue` | 0 | 1 | 0 | 4 | yes | `CharacterStat.<clinit> @56 L16` |
| `FITNESS` | `Fitness` | **−1** | 1 | 0 | 5 | yes | `CharacterStat.<clinit> @67 L17` |
| `FOOD_SICKNESS` | `FoodSickness` | 0 | 100 | 0 | 6 | yes | `CharacterStat.<clinit> @79 L18` |
| `HUNGER` | `Hunger` | 0 | 1 | 0 | 7 | yes | `CharacterStat.<clinit> @91 L19` |
| `IDLENESS` | `Idleness` | 0 | 1 | 0 | 8 | yes | `CharacterStat.<clinit> @102 L20` |
| `INTOXICATION` | `Intoxication` | 0 | 100 | 0 | 9 | yes | `CharacterStat.<clinit> @113 L21` |
| `MORALE` | `Morale` | 0 | 1 | 1 | 10 | yes | `CharacterStat.<clinit> @125 L22` |
| `NICOTINE_WITHDRAWAL` | `NicotineWithdrawal` | 0 | **0.51** | 0 | 11 | yes | `CharacterStat.<clinit> @136 L23` |
| `PAIN` | `Pain` | 0 | 100 | 0 | 12 | yes | `CharacterStat.<clinit> @148 L24` |
| `PANIC` | `Panic` | 0 | 100 | 0 | 13 | yes | `CharacterStat.<clinit> @160 L25` |
| `POISON` | `Poison` | 0 | 100 | 0 | 14 | yes | `CharacterStat.<clinit> @172 L26` |
| `SANITY` | `Sanity` | 0 | 1 | 1 | 15 | yes | `CharacterStat.<clinit> @184 L27` |
| `SICKNESS` | `Sickness` | 0 | 1 | 0 | 16 | yes | `CharacterStat.<clinit> @195 L28` |
| `STRESS` | `Stress` | 0 | 1 | 0 | 17 | yes | `CharacterStat.<clinit> @206 L29` |
| `TEMPERATURE` | `Temperature` | **20** | **40** | **37** | 18 | yes | `CharacterStat.<clinit> @217 L30` |
| `THIRST` | `Thirst` | 0 | 1 | 0 | 19 | yes | `CharacterStat.<clinit> @231 L31` |
| `UNHAPPINESS` | `Unhappiness` | 0 | 100 | 0 | 20 | yes | `CharacterStat.<clinit> @242 L32` |
| `WETNESS` | `Wetness` | 0 | 100 | 0 | 21 | yes | `CharacterStat.<clinit> @254 L33` |
| `ZOMBIE_FEVER` | `ZombieFever` | 0 | 100 | 0 | 22 | yes | `CharacterStat.<clinit> @266 L34` |
| `ZOMBIE_INFECTION` | `ZombieInfection` | 0 | 100 | 0 | 23 | yes | `CharacterStat.<clinit> @278 L35` |

All twenty-four are in the packet and none is out of it, because `Stats.save(ByteBuffer) @0 L55` iterates `ORDERED_STATS` and writes one float per entry with no bitmask, and `PlayerStatsPacket.write @5 L33` calls exactly that (the packet's field order is already established at [`facts/wire-packets.md#player-stats-packet`](../../facts/wire-packets.md#player-stats-packet) [#0564]). A stat that is *not* in `ORDERED_STATS` — which is the only shape a mod-registered stat can have, since the array is built in the class initialiser — is invisible to every save and every sync: `Stats.write(bb, index) @0 L69` indexes `ORDERED_STATS` and warns `'Wrong field %d provided for Stats::write method'` at `@29 L72` otherwise, and `SyncPlayerStatsPacket.getBitMaskForStat @0 L29` returns `1 << index` for a member and `0` at `@29 L34` for a non-member.

| Member | Signature | Flags | Exposed? | Side | Cite |
|---|---|---|---|---|---|
| `CharacterStat.register` | `(String,F,F,F)CharacterStat` | `public static` | class in exposer set | either | `CharacterStat.register @0 L50` — `REGISTRY.computeIfAbsent`, so re-registering an existing id returns the existing stat and never rewrites its bounds |
| `CharacterStat.getById` | `(String)CharacterStat` | `public static` | yes | either | `CharacterStat.getById @0 L54` |
| `CharacterStat.<init>` | `(String,F,F,F)V` | `private` | — | — | `CharacterStat.<init> @0 L42` |
| `CharacterStat.getMinimumValue` / `getMaximumValue` / `getDefaultValue` | `()F` | `public` | yes | either | member list (13 methods, exhaustive) — **no setter for any of the three exists** |
| `CharacterStat.clamp` | `(F)F` | `public` | yes | either | `CharacterStat.clamp @0 L70` → `PZMath.clamp(v, min, max)` |
| `CharacterStat.isAtMinimum` | `(F)Z` | `public` | yes | either | `CharacterStat.isAtMinimum @0 L78` — `v <= min` |
| `Stats.<init>` | `()V` | `public` | yes | either | `Stats.<init> @4 L18` map, `@15 L21` `enduranceRecharging=false`, `@20 L22` `lastEndurance=1` |
| `Stats.get` | `(CharacterStat)F` | `public` | yes | either | `Stats.get @0 L77` — `stats.getOrDefault(stat, stat.getDefaultValue())`; the map is sparse and **no per-stat registration on `Stats` is needed or possible** |
| `Stats.set` | `(CharacterStat,F)Z` | `public` | yes | either | `Stats.set @0 L81` reads old, `@6 L82` `stat.clamp(v)`, `@13 L83` puts, `@29 L84` returns whether the value changed |
| `Stats.add` | `(CharacterStat,F)Z` | `public` | yes | either | `Stats.add @0 L88` → `set(get + v)` |
| `Stats.remove` | `(CharacterStat,F)Z` | `public` | yes | either | `Stats.remove @0 L92` → `add(−v)` |
| `Stats.reset` | `(CharacterStat)Z` | `public` | yes | either | `Stats.reset @0 L96` → `set(default)` |
| `Stats.resetStats` | `()V` | `public` | yes | either | `Stats.resetStats @0 L112` — iterates `REGISTRY`, so it **would** also reset a mod-registered stat |
| `Stats.isAtMinimum` / `isAtMaximum` / `isAboveMinimum` | `(CharacterStat)Z` | `public` | yes | either | `Stats.isAtMinimum @0 L100` |
| `Stats.save` / `load` / `write` / `parse` | ByteBuffer + DataStream forms | `public` | yes | either | `Stats.save @0 L55`, `Stats.write @0 L69` |
| `Stats.getEnduranceWarning` | `()F` | `public` | yes | either | `Stats.getEnduranceWarning @0 L165` — hard `0.5` |
| `Stats.getEnduranceDangerWarning` | `()F` | `public` | yes | either | `Stats.getEnduranceDangerWarning @0 L161` — hard `0.25` |
| `Stats.isEnduranceRecharging` | `()Z` | `public` | yes | either | `Stats.isEnduranceRecharging @0 L169` — hard `false`, the field is written nowhere but the constructor |
| `Stats.getLastEndurance` / `setLastEndurance` | `()F` / `(F)V` | `public` | yes | either | `IsoGameCharacter.updateEndurance @0 L10360` is the only writer found |

The whole `Stats` member list is 34 methods and every one of them is `public`; `zombie/characters/Stats` sits in the exposer's class set at `LuaManager$Exposer.exposeAll @685`, and `zombie/characters/CharacterStat` at `@691`, both read out of a dump of that method taken end to end.

## B — `updateEndurance` in full

Two distinct methods, not an override pair: both are `private`, and the caller scan shows `IsoGameCharacter.calculateStats @61` reaching the base one while `IsoPlayer.updateInternal2 @938 L2408` and `@2139 L2661` reach the player one (and `IsoPlayer.updateWhileInVehicle @277` / `updateInternal2 @931 L2406` reach the vehicle variant instead). A jar-wide grep for `updateEndurance` hits only `IsoGameCharacter.class` and `IsoPlayer.class`.

`IsoGameCharacter.updateEndurance` is three instructions of housekeeping: `@0 L10360` `stats.setLastEndurance(stats.get(ENDURANCE))`, `@17 L10361` if `isUnlimitedEndurance()` then `@24 L10362` `stats.reset(ENDURANCE)` (to the default 1.0), `@35 L10364` return.

`IsoPlayer.updateEndurance` is the model. Gate first: `@0 L3427` `if (isAnimal() || GameClient.client) return;` — the raw bytes at offsets 0–13 are `42 182 1 197 / 154 0 9 / 178 2 102 / 153 0 4 / 177`, so `ifne` from `isAnimal` targets the `return` at `@13 L3428` and `ifeq` on the `GameClient.client` boolean skips it. **This reads the opposite way round from the library's [#0561]** ("returning immediately on a game client unless the character is an animal"): animals return too. Then `@14 L3432` if sitting on the ground, sitting on furniture or resting, delegate to `updateEnduranceWhileSitting` at `@35 L3433` and return at `@39 L3434`.

```java
float sneak = 1.0f;                                   // @40  L3437
if (isSneaking()) sneak = 1.5f;                       // @49  L3439

// ---- drain, running / sprinting / dragging ----
if (currentSpeed > 0 && (isRunning() || isSprinting() || isDraggingCorpse())) {   // @53  L3441
    double rate = ZomboidGlobals.runningEnduranceReduce;                          // @83  L3442
    if (isSprinting())       rate = ZomboidGlobals.sprintingEnduranceReduce;      // @94  L3444
    if (isDraggingCorpse())  rate = ZomboidGlobals.sprintingEnduranceReduce;      // @105 L3447
    float m = 1.4f;                                                              // @109 L3450
    if (traits.get(OVERWEIGHT)) m = 2.9f;                                         // @127 L3452
    if (traits.get(ATHLETIC))   m = 0.8f;                                         // @145 L3455  (overrides Overweight)
    m *= 2.3f;                                                                    // @150 L3458
    m *= getPacingMod();                                                          // @158 L3459
    m *= getHyperthermiaMod();                                                    // @167 L3460
    float asthma = 0.7f;                                                          // @176 L3461
    if (traits.get(ASTHMATIC)) asthma = 1.0f;                                      // @194 L3464
    if (moodles.getMoodleLevel(HEAVY_LOAD) == 0)                                   // @197 L3467
        stats.remove(ENDURANCE, rate*m*0.5*asthma*GameTime.getMultiplier()*sneak); // @210 L3468
    else {
        float load;                     // tableswitch @259: 1 -> 1.5, 2 -> 1.9, 3 -> 2.3, default -> 2.8
        // @284 L3471 / @290 L3472 / @296 L3473 / @302 L3474
        stats.remove(ENDURANCE, rate*m*0.5*asthma*GameTime.getMultiplier()*load*sneak); // @307 L3476
    }
}
// ---- drain, walking under heavy load ----
else if (currentSpeed > 0 && moodles.getMoodleLevel(HEAVY_LOAD) > 2) {             // @350 L3480
    float asthma = 0.7f; if (traits.get(ASTHMATIC)) asthma = 1.0f;                 // @373 L3481 / @390 L3483
    float m = 1.4f;                                                                // @392 L3486
    if (traits.get(OVERWEIGHT)) m = 2.9f;                                          // @409 L3488
    if (traits.get(ATHLETIC))   m = 0.8f;                                          // @426 L3492
    m *= 3.0f;                                                                     // @430 L3495
    m *= getPacingMod();                                                           // @436 L3496
    m *= getHyperthermiaMod();                                                     // @443 L3497
    float load = 2.8f;                  // tableswitch @465: 2 -> 1.5, 3 -> 1.9, 4 -> 2.3
    // @492 L3501 / @500 L3504 / @508 L3507 ; only 3 and 4 are reachable past the >2 gate
    stats.remove(ENDURANCE,
        runningEnduranceReduce*m*0.5*asthma*sneak*GameTime.getMultiplier()*load / 2.0);  // @513 L3510
}
// ---- regen, standing still ----
if (!isPlayerMoving()) {                                                           // @557 L3514
    float r = 1.0f;                                                                // @564 L3516
    r *= (1.0f - stats.get(FATIGUE) * 0.85f);                                       // @566 L3518
    r *= GameTime.getMultiplier();                                                  // @585 L3519
    if (moodles.getMoodleLevel(HEAVY_LOAD) <= 1)                                    // @594 L3521
        stats.add(ENDURANCE, imobileEnduranceReduce
            * SandboxOptions.instance.getEnduranceRegenMultiplier()
            * getRecoveryMod() * r);                                                // @608 L3522
}
// ---- regen or drain, walking ----
if (!isSprinting() && !isRunning() && currentSpeed > 0) {                           // @639 L3527
    float r = 1.0f;
    r *= (1.0f - stats.get(FATIGUE));                                               // @664 L3530  (no 0.85 here)
    r *= GameTime.getMultiplier();                                                  // @679 L3531
    if (getMoodles().getMoodleLevel(ENDURANCE) < 2) {                                // @688 L3532
        if (moodles.getMoodleLevel(HEAVY_LOAD) <= 1)                                 // @702 L3533
            stats.add(ENDURANCE, imobileEnduranceReduce / 4.0
                * getEnduranceRegenMultiplier() * getRecoveryMod() * r);              // @716 L3534
    } else
        stats.remove(ENDURANCE, runningEnduranceReduce / 7.0 * sneak);                // @754 L3537
}
return;                                                                              // @776 L3540
```

Two things fall out of the shape. Sneaking *raises* the drain (×1.5) and *raises* the walking drain-on-tired term, because `sneak` multiplies the removals and never a regen. And no arm of this method carries `GameTime.getDeltaMinutesPerDay()`, unlike fatigue, hunger and thirst — so endurance rates are per-tick times `getMultiplier()` only and do not scale with day length.

| Constant | Value | Where it comes from | Cite |
|---|---|---|---|
| `runningEnduranceReduce` | 5.20e-5 | Lua `ZomboidGlobals.RunningEnduranceReduce` | `ZomboidGlobals.Load @31 L70`; `media/lua/shared/defines.lua:5` |
| `sprintingEnduranceReduce` | 4.550e-4 | Lua `ZomboidGlobals.SprintingEnduranceReduce` | `ZomboidGlobals.Load @15 L69`; `defines.lua:6` |
| `imobileEnduranceReduce` | 9.30e-5/3 = 3.10e-5 | Lua `ZomboidGlobals.ImobileEnduranceIncrease` | `ZomboidGlobals.Load @48 L71`; `defines.lua:7` |
| `sittingEnduranceMultiplier` | 5.0 | hard-coded, not from Lua | `ZomboidGlobals.<clinit> @0 L11` |
| `fatigueIncrease` | 3.45e-5 | Lua `ZomboidGlobals.FatigueIncrease` | `ZomboidGlobals.Load @202 L84`; `defines.lua:19` |
| `sleepFatigueReduction` | 3.0e-6 | Lua `ZomboidGlobals.SleepFatigueReduction` | `ZomboidGlobals.Load @372 L100`; **read by nothing** — jar-wide grep `sleepFatigueReduction` hits `zombie/ZomboidGlobals.class` only |

The other endurance-writing paths, all in the same model:

| Member | Signature | Flags | Exposed? | Side | Cite |
|---|---|---|---|---|---|
| `IsoPlayer.updateEnduranceWhileSitting` | `()V` | `public` | yes | server (its caller is gated) | `@0 L3407` `m = 5.0`; `@5 L3408` `× (1 − FATIGUE·0.8)`; `@24 L3409` `× multiplier`; `@33 L3410` `ENDURANCE += imobile × regenMult × recoveryMod × m` |
| `IsoPlayer.updateEnduranceWhileInVehicle` | `()V` | `public` | yes | server | `@0 L3414` same animal/client gate; `@14 L3417` skipped while asleep; `@21 L3418`–`@54 L3422` identical to the sitting formula |
| `IsoPlayer.updateStats_Sleeping` | `()V` | `protected` | yes | server | `@0 L3290` `m = 2.0`; `@2 L3291` if `allPlayersAsleep()` then `@8 L3292` `m ×= deltaMinutesPerDay`; `@17 L3295` `ENDURANCE += imobile × regenMult × recoveryMod × multiplier × m` |
| `IsoGameCharacter.exert` | `(F)V` | **`public`** | yes | wherever called from | `@0 L10504` Jogger `×0.9`; `@19 L10507` `ENDURANCE -= amount` — the cleanest Lua-callable endurance drain in the jar |
| `IsoGameCharacter.Eat` | `(InventoryItem,F,Z)Z` | `public` | yes | server (per [`mp-model#ownership`](../../platform/mp-model.md#ownership)) | `@181 L5770` `ENDURANCE += Food.getEnduranceChange() × f`; `@217 L5772` `FATIGUE += Food.getFatigueChange() × f`; `@675`–`@720 L…` the follow-up `SyncPlayerStatsPacket` mask is THIRST+HUNGER+ENDURANCE+STRESS+FATIGUE+PAIN |
| `CombatManager.processWeaponEndurance` | `(IsoGameCharacter,HandWeapon)V` | `public` | `CombatManager` in exposer set | called from `attackCollisionCheck @352` | see below |
| `IsoGameCharacter.updateInternal` | `()V` | `private` | — | both | `@2063 L9316` if `isGodMod()` then `@2070 L9317` reset FATIGUE, `@2081 L9318` reset ENDURANCE, `@2092 L9319` reset TEMPERATURE |

The per-swing drain, `CombatManager.processWeaponEndurance`:

```java
if (!weapon.isUseEndurance()) return;                              // @0  L1190
float w = weapon.getEffectiveWeight();                             // @8  L1194
float extra = 0;                                                   // @13 L1195
if (weapon.isTwoHandWeapon() && !heldInBothHands) extra = w/1.5f/10f;  // @16 L1196, @39 L1197
float d = ( w * 0.18f
          * weapon.getFatigueMod(chr)                              // @54 L1200 — 0.8 at Blunt/Axe/Spear perk >= 8, else 1.0 (HandWeapon.getFatigueMod @0 L515, default @95 L535)
          * chr.getFatigueMod()                                    // @60 L1200 — the Fitness ladder below
          * weapon.getEnduranceMod()                               // @65 L1200 — the item script's EnduranceMod
          * 0.3f + extra ) * 0.04f;                                // @70..@80 L1200
float t = chr.getCharacterTraits().getTraitEnduranceLossModifier(); // @83 L1201 — Asthmatic 1.2, else 1.0 (CharacterTraits.getTraitEnduranceLossModifier @0 L146)
chr.getStats().remove(ENDURANCE, d * t);                           // @92 L1202
```

The three Fitness-perk ladders that enter the model, all `public` on the exposed `IsoGameCharacter`:

| Fitness level | `getRecoveryMod` (`@0 L4614`) | `getPacingMod` (`@0 L4498`) | `getFatigueMod` (`@0 L4428`) |
|---|---|---|---|
| 0 | 0.70 (`@14 L4617`) | 0.90 (default, `@103 L4529`) | 1.00 (default, `@103 L4459`) |
| 1 | 0.80 (`@23 L4620`) | 0.80 (`@13 L4500`) | 0.95 (`@13 L4430`) |
| 2 | 0.90 (`@32 L4623`) | 0.75 (`@22 L4503`) | 0.92 (`@22 L4433`) |
| 3 | 1.00 (`@41 L4626`) | 0.70 (`@31 L4506`) | 0.89 (`@31 L4436`) |
| 4 | 1.10 (`@48 L4629`) | 0.65 (`@40 L4509`) | 0.87 (`@40 L4439`) |
| 5 | 1.20 (`@57 L4632`) | 0.60 (`@49 L4512`) | 0.85 (`@49 L4442`) |
| 6 | 1.30 (`@67 L4635`) | 0.57 (`@59 L4515`) | 0.83 (`@59 L4445`) |
| 7 | 1.40 (`@77 L4638`) | 0.53 (`@69 L4518`) | 0.81 (`@69 L4448`) |
| 8 | 1.50 (`@87 L4641`) | 0.49 (`@79 L4521`) | 0.79 (`@79 L4451`) |
| 9 | 1.55 (`@97 L4644`) | 0.46 (`@89 L4524`) | 0.77 (`@89 L4454`) |
| 10 | 1.60 (`@107 L4647`) | 0.43 (`@99 L4527`) | 0.75 (`@99 L4457`) |

`getRecoveryMod` then applies, in order, Obese `×0.4` (`@124 L4650`), Overweight `×0.7` (`@143 L4653`), Very Underweight `×0.7` (`@162 L4656`), Emaciated `×0.3` (`@181 L4659`) — these four are cumulative in code, not exclusive branches — and then, for an `IsoPlayer` only, lipids below −1500 `×0.2` (`@211 L4665`) else below −1000 `×0.5` (`@236 L4667`), and proteins below −1500 `×0.2` (`@259 L4671`) else below −1000 `×0.5` (`@284 L4673`), returning at `@290 L4676`. Both macro pairs are dead because the setters clamp those stores at −500 ([`facts/nutrition-core.md#macro-effects`](../../facts/nutrition-core.md#macro-effects) [#0181/M/n=2]).

`getHyperthermiaMod @0 L4533` returns 1.0 except at `HYPERTHERMIA` moodle level exactly 4, where it returns 2.0 (`@30 L4537`) — levels 2 and 3 give nothing, which reads as a bug in the gate at `@12`.

`SandboxOptions.getEnduranceRegenMultiplier @0 L535` switches on the `endRegen` enum option: case 1 → 1.8 (`@40 L536`), case 2 → 1.3 (`@46 L537`), case 3 → 1.0 (the default arm, `@64 L540`), case 4 → 0.7 (`@52 L538`), case 5 → 0.4 (`@58 L539`), table read from the `tableswitch` at `@7`.

Where endurance is *read*: `IsoGameCharacter.isEnduranceSufficientForAction @0 L6503` is `!moodles.isMaxMoodleLevel(ENDURANCE)`; `calculateBaseSpeed @13 L9773` subtracts `0.15 ×` the ENDURANCE moodle level from a base of 0.8; `calculateCombatSpeed @95 L9874` subtracts `0.07 ×` it; `calculateIdleSpeed @0 L9764` adds `2.5/10 ×` it to 0.01; `CombatManager.getMoodlesPenalty @94 L2522` adds `level × ENDURANCE_TO_HIT_BASE_PENALTY`; `attackCollisionCheck` multiplies stomp power by the ladder below. The moodle thresholds are `MoodleStat.<clinit> @10 L10`: `ENDURANCE` registers `(0.75, 0.5, 0.25, 0.10, 0.0)` — inverted, so level 1 fires *below* 0.5 — matching [#0510/C/C-only].

## C — fatigue, sleep and the multiplayer reset

The reset the library found, verbatim from the dump:

```java
// IsoGameCharacter.calculateStats
if (isAnimal()) return;                                                   // @0  L10196
if (GameServer.server != null
    && !(ServerOptions.instance.sleepAllowed.getValue()
         && ServerOptions.instance.sleepNeeded.getValue()))               // @8  L10200
    stats.reset(FATIGUE);                                                 // @38 L10201
if (LuaHookManager.TriggerHook("CalculateStats", this)) return;           // @49 L10204, @59 L10205
updateEndurance();          // @60 L10208
updateTripping();           // @64 L10210
updateThirst();             // @68 L10212
updateStress();             // @72 L10214
updateStats_WakeState();    // @76 L10216
updateMorale();             // @80 L10218
updateFitness();            // @84 L10221
```

So yes: **a server with sleep disabled pins fatigue at its default of 0, every tick, unconditionally**, and the pin is applied before the Lua hook, so a mod cannot get in front of it. The gate needs *both* `SleepAllowed` and `SleepNeeded` true to stop resetting. `IsoPlayer.calculateStats @0 L3280` returns immediately when `GameClient.client` is set and otherwise calls `super` at `@7 L3281`, so on a dedicated server the whole block above, reset included, runs on the server only.

`updateStats_WakeState @0 L10224` returns for animals, `@8 L10227` runs only when `GameServer.server` is set, or `GameClient.client` is not set and this character is `IsoPlayer.getInstance()`, then dispatches on the `asleep` field: `@35 L10229` `updateStats_Sleeping()`, else `@41 L10231` `updateStats_Awake()`. `updateStats_Sleeping` is `protected`, so that dispatch *is* virtual and reaches `IsoPlayer`'s override; the base `IsoGameCharacter.updateStats_Sleeping @0 L10239` is an empty body (a bare `return`), so a non-player character does nothing at all while asleep.

Awake accumulation, `IsoGameCharacter.updateStats_Awake`:

```java
float endDef = 1.0f - stats.get(ENDURANCE);                     // @31 L10244
if (endDef < 0.3f) endDef = 0.3f;                               // @44 L10245, @52 L10246
float sleepTrait = 1.0f;                                        // @56 L10249
if (traits.get(NEEDS_LESS_SLEEP)) sleepTrait = 0.7f;            // @71 L10251
if (traits.get(NEEDS_MORE_SLEEP)) sleepTrait = 1.3f;            // @88 L10254
float rest = 1.0f;                                              // @92 L10258
if (isSitOnGround() || isSittingOnFurniture() || isResting())
    rest = 1.5f;                                                // @115 L10260
stats.add(FATIGUE, ZomboidGlobals.fatigueIncrease
    * SandboxOptions.instance.getStatsDecreaseMultiplier()
    * endDef
    * GameTime.getMultiplier()
    * GameTime.getDeltaMinutesPerDay()
    * sleepTrait
    * getFatiqueMultiplier()          // note the engine's spelling
    / rest);                                                    // @119 L10262
```

`getFatiqueMultiplier @0 L14959` returns `BodyDamage.getThermoregulator().getFatigueMultiplier()` when both are non-null and `1.0` otherwise (`@28 L14962`). Sitting *divides*, so resting slows fatigue rather than speeding it. Endurance already drives fatigue through `endDef`, floored at 0.3.

Sleep restoration, `IsoPlayer.updateStats_Sleeping` (the endurance arm is in section B):

```java
if (stats.isAboveMinimum(FATIGUE)) {                            // @56 L3297
    float f = 1.0f;                                             // @69 L3299
    if (traits.get(INSOMNIAC)) f *= 0.5f;                        // @84 L3301
    if (traits.get(NIGHT_OWL)) f *= 1.4f;                        // @103 L3304
    float bed = 1.0f;                                           // @109 L3307
    // getBedType() ladder, @111 L3308 onwards:
    //   averageBedPillow 1.05 (@124 L3309)  goodBed 1.10 (@141 L3312)
    //   goodBedPillow    1.15 (@161 L3314)  badBed  0.90 (@181 L3316)
    //   badBedPillow     0.95 (@201 L3318)  floor   0.60 (@221 L3320)
    //   floorPillow      0.75 (@241 L3322)  anything else 1.00
    float dt = 1.0f / GameTime.getMinutesPerDay() / 60.0f
                    * GameTime.getMultiplier() / 2.0f;           // @245 L3325
    timeOfSleep += dt;                                           // @268 L3327
    if (timeOfSleep > delayToActuallySleep) {                     // @279 L3328
        float t = 1.0f;                                           // @291 L3329
        if (traits.get(NEEDS_LESS_SLEEP))      t *= 0.75f;         // @307 L3331
        else if (traits.get(NEEDS_MORE_SLEEP)) t *= 1.18f;         // @331 L3333
        if (stats.get(FATIGUE) <= 0.3f) {                          // @339 L3338
            float hours = 7.0f * t;                                // @356 L3339
            stats.remove(FATIGUE, dt/hours * 0.3f * f * bed);      // @364 L3340
        } else {
            float hours = 5.0f * t;                                // @391 L3344
            stats.remove(FATIGUE, dt/hours * 0.7f * f * bed);      // @399 L3345
        }
    }
}
```

Read as design: the top 0.7 of fatigue is meant to come off over a nominal 5 hours and the last 0.3 over a nominal 7, both scaled by bed type, Insomniac, Night Owl and the two sleep traits, and `ZomboidGlobals.sleepFatigueReduction` — the constant that looks like it should own this — is loaded and never read.

Two other fatigue writers: `IsoGameCharacter.updateInternal @171 L9034` reads fatigue, and at `@195 L9037` adds `1.0e-4 × GameTime.getThirtyFPSMultiplier()` while fatigue is below 1 on a toxic-exposure branch gated by `isProtectedFromToxic(true)` at `@163`; and the god-mode reset at `@2070 L9317`.

The `TIRED` moodle and what it does:

| Member | Signature | Flags | Exposed? | Side | Cite |
|---|---|---|---|---|---|
| `MoodleStat.TIRED` thresholds | `(0.0, 0.6, 0.7, 0.8, 0.9)` | field | `MoodleStat` **not** in exposer set | both (moodles recompute per side) | `MoodleStat.<clinit> @46 L12` |
| `Moodle.Update` TIRED block | — | — | — | both | `@359 L144` selects the type; `@369 L145` skipped when `getBodyDamage().getHealth() == 0`; `@384 L146` reads `FATIGUE`; strict `>` against the four thresholds at `@398 L147`, `@416 L150`, `@434 L153`, `@452 L156`, last match wins |
| `CombatManager.getMoodlesPenalty` | `(IsoGameCharacter,F)F` | `public` | yes | firearm aim | `@71 L2522` `+= TIRED level × TIRED_TO_HIT_BASE_PENALTY`; `@94` `+= ENDURANCE level × ENDURANCE_TO_HIT_BASE_PENALTY`; `@153` whole sum `× SandboxOptions.firearmMoodleMultiplier` |
| `CombatConfigKey.TIRED_TO_HIT_BASE_PENALTY` | default 2.5, range 0–10, category FIREARM | field | `CombatConfig.set` is `public` | — | `CombatConfigKey.<clinit> @693 L38` |
| `CombatConfigKey.ENDURANCE_TO_HIT_BASE_PENALTY` | default 2.5, range 0–10, FIREARM | field | — | — | `CombatConfigKey.<clinit> @717 L39` |
| `CombatManager.attackCollisionCheck` stomp | — | `public` | yes | attack | stomp power = `Rand.Next(0.7,1) + Strength×0.2` (`@2600 L972`), `×0.5` barefoot (`@2639 L975`) or `× Clothing.getStompPower()` (`@2650 L977`); then `tableswitch @2677` on the ENDURANCE moodle `×0.5/0.2/0.1/0.05` for levels 1–4 (`L986`/`L990`/`L994`/`L998`) and `tableswitch @2802` on the TIRED moodle with the identical ladder (`L1007`/`L1011`/`L1015`/`L1019`) |
| `IsoGameCharacter.testDefense` | `(IsoZombie)Z` | `public` | yes | both | `@124 L14503` subtracts `3 ×` the TIRED level from the defence roll (HEAVY_LOAD and PANIC subtract `2 ×`) |
| `IsoGameCharacter.updateInternal` | `()V` | `private` | — | both | `@1160 L9172` reads the TIRED level; at exactly 4, `@1176 L9174` `SANITY -= 2.0e-6` |
| `IsoGameCharacter.getDetectionRange` | `()F` | `public` | yes | both | `@82 L16400` subtracts the raw `FATIGUE` value |
| `IsoGameCharacter.getEffectiveFatigue` | `()F` | `public` | yes | both | `@0 L16391` `max(0, FATIGUE − 0.6) × 2.5` |
| `Fitness.incFutureStiffness` | `()V` | `public` | `Fitness` in exposer set | exercise | `@170` reads `MoodleType.TIRED` inside the stiffness accumulation |
| `IsoPlayer.onIdlePerformFidgets`, `IsoPlayer.checkCanSeeClient` | — | `private` / `public` | — | client-ish | `@189` and `@485` read the TIRED level (animation and visibility) |

Fatigue does **not** enter `calculateWalkSpeed`, `calculateBaseSpeed` or `calculateCombatSpeed` directly — its movement and combat reach is the TIRED moodle in `attackCollisionCheck` and `testDefense`, the firearm penalty, and the endurance-regen terms in section B. `Moodles` has no setter for a level at all: its member list is twelve methods — `getMoodleLevel`, `isMaxMoodleLevel`, `getGoodBadNeutral`, `GoodBadNeutral`, the four display-string getters, `UI_RefreshNeeded`, `setMoodlesStateChanged`, `Update` and the constructor — so a mod that wants a moodle level must move the stat under it.

The sleep surface a mod can reach, from the shipped Lua rather than the jar:

| Call | Where | Side | Note |
|---|---|---|---|
| `player:setAsleep(true)` | `ISSleepDialog.lua:75`, `ISWorldObjectContextMenu.lua:1108` | client-initiated | `IsoGameCharacter.setAsleep @0 L2989` is a bare `public` field write; `isAsleep` likewise |
| `player:setAsleepTime(0.0)` | `ISSleepDialog.lua:74`, `ISWorldObjectContextMenu.lua:1107` | client | `IsoPlayer.setAsleepTime` `public` |
| `player:setForceWakeUpTime(h)` | `ISSleepDialog.lua:73`, `ISWorldObjectContextMenu.lua:1106` | client | |
| `getSleepingEvent():setPlayerFallAsleep(player, hours)` | `ISSleepDialog.lua:76`, `ISWorldObjectContextMenu.lua:1123` | single-player / host arm | skipped on a client when `SleepAllowed` is true |
| `sendClientCommand(player, "player", "onVehicleSleep", {id=…, isAsleep=true})` → `Commands.player.onVehicleSleep` | `ISWorldObjectContextMenu.lua:1120`, `ClientCommands.lua:606-609` | client → server | the one traced route by which a client's sleep decision reaches the server's `setAsleep` |
| `getServerOptions():getBoolean("SleepAllowed")` / `"SleepNeeded"` | `ISWorldObjectContextMenu.lua:1114`, `ISVehicleMenu.lua:190-192`, `MainCreationMethods.lua:105`, `CharacterCreationProfession.lua:890` | either | `zombie/network/ServerOptions` is in the exposer set at `exposeAll @3614`; these two options are what the fatigue reset reads |

**Blocking or forcing sleep** therefore has no dedicated Java door: the only levers are `setAsleep`, `setAsleepTime`, `setForceWakeUpTime`, `setDelayToSleep`, `setTimeOfSleep`, `SleepingTablet(F)` and `setSleepingPillsTaken`, plus wrapping the Lua that calls them. A jar-wide grep for `forceSleep` was not run; what was established is that the shipped Lua uses only the setters above.

## D — every `Mod` / `Modifier` / `Multiplier` / `Speed` setter on the character

Exhaustive over the two classes' member lists (`IsoGameCharacter` 1450 methods, `IsoPlayer` 574), filtered on `set*` whose name contains `Mod`, `Modifier`, `Multiplier` or `Speed` and excluding `Model`/`ModData`/`Module`.

| Member | Signature | Flags | Exposed? | Side that reads it | Survives the 1 Hz stats push? | Carried by a packet? | Cite |
|---|---|---|---|---|---|---|---|
| `IsoGameCharacter.setSpeedMod` | `(F)V` | `public` | yes | not read by any method scanned here; `getSpeedMod` is the only reader found | yes — not a `Stats` entry, so `PlayerStatsPacket` does not touch it | no — grep of the packet classes turned up no `speedMod` field write | `setSpeedMod @0 L3718`, `getSpeedMod @0 L3714` |
| `IsoGameCharacter.setStaggerTimeMod` | `(F)V` | `public` | yes | stagger timing (not dumped) | yes | not traced | `setStaggerTimeMod @0 L3726` |
| `IsoGameCharacter.setLevelUpMultiplier` | `(F)V` | `public` | yes | XP award | yes | not traced | `setLevelUpMultiplier @0 L2644` |
| `IsoGameCharacter.setPathSpeed` | `(F)V` | `public` | yes | pathfinding | yes | not traced | member list + flags parse |
| `IsoGameCharacter.setSneakLimpSpeedScale` | `(F)V` | `public` | yes | both — written by `calculateWalkSpeed` on **both** sides (`IsoPlayer.calculateWalkSpeed @83 L4059` on the client arm, `IsoGameCharacter.calculateWalkSpeed @143 L10053` on the server arm) | yes, but **overwritten every `calculateWalkSpeed`** | indirectly, via the `WalkInjury` float in `PlayerInjuriesPacket` | `setSneakLimpSpeedScale`, `calculateWalkSpeed @143 L10053` |
| `IsoGameCharacter.setLastFallSpeed` | `(F)V` | `public` | yes | fall damage | yes | not traced | member list |
| `IsoGameCharacter.setUnlimitedEndurance` | `(Z)V` | `public` | yes (`PlayerCheats` is **not** exposed, but this setter is on an exposed class) | server — read by `IsoGameCharacter.updateEndurance @17 L10361`, which resets ENDURANCE to 1.0 | the flag itself yes; the reset it causes is applied to a synced stat | no `CheatType` field traced in any packet | `setUnlimitedEndurance @0 L15473` — gated on `Role.hasCapability(Capability.ToggleUnlimitedEndurance)`: **without the capability it forces the cheat to `false`**, with it, it writes the argument |
| `IsoPlayer.setMoveSpeed` | `(F)V` | `public` | yes | movement integration | yes | not traced | `setMoveSpeed @0 L1822` |
| `IsoPlayer.setCombatSpeed` | `(F)V` | `public` | yes | swing timing | yes | not traced | `setCombatSpeed @0 L9359`, `getCombatSpeed @0 L9363` |
| `IsoPlayer.setFitnessSpeed` | `()V` | `public` | yes | client animation variable | yes | it writes the animation variables `FitnessSpeed` and `FitnessStruggle`, not a field | `setFitnessSpeed @0 L9137` — `v = perk/5/1.1 − ENDURANCE moodle/20`, capped at 1.5, and below 0.85 it snaps to 1.0 and sets `FitnessStruggle` |

Absent from the whole jar (each a `pz.sh grep <name>` that answered `no class contains that literal`): `setEnduranceRegenMod`, `setFatigueMod`, `setRecoveryMod`, `setPacingMod`, `setWalkSpeedModifier`, `setAttackDelay`, `setNimbleMod`, `setFatigueMultiplier`, `setEnduranceMultiplier`. Two names the brief guessed do exist, but on items rather than the character: `setRunSpeedModifier` on `zombie/inventory/types/Clothing` and `zombie/scripting/objects/Item`, and `setEnduranceMod` on `zombie/inventory/types/HandWeapon` and `Item` — both are script-item properties, and the weapon one feeds `processWeaponEndurance`.

The three character-level speed modifier *fields* are not writable from Lua and are rewritten from worn items on a cadence: `IsoGameCharacter.updateSpeedModifiers @0 L10094` sets `runSpeedModifier = 1`, `@5 L10095` `walkSpeedModifier = 1`, `@10 L10096` `combatSpeedModifier = 1` and then sums `(modifier − 1)` over worn clothing and bags; `NetworkPlayerAI.syncDamage @32 L698` calls it on the server immediately before sending the injuries packet. `getRunSpeedModifier @0 L14920` is a `public` getter with no setter.

What *does* cross to the client is the computed speed, and this is the route the design should know about:

```java
// IsoPlayer.calculateWalkSpeed
if (GameClient.client) {                                        // @0  L4051
    boolean running = isRunning() || isSprinting();
    NetworkPlayerAI ai = getNetworkCharacterAI();               // @26 L4053
    setVariable("WalkSpeed", running ? ai.runSpeed : ai.walkSpeed);  // @31 L4054
    ...
    return;                                                     // @88 L4060
}
...
super.calculateWalkSpeed();                                     // @141 L4076
if (GameServer.server) {                                        // @145 L4078
    NetworkPlayerAI ai = getNetworkCharacterAI();
    ai.walkSpeed = this.walkSpeed;                              // @156 L4080
    ai.runSpeed  = this.runSpeed;                               // @164 L4081
}
```

and `PlayerInjuriesPacket.write` carries exactly five floats: `IdleSpeed` (`@10 L29`), `StrafeSpeed` (`@22 L30`), `WalkInjury` (`@33 L31`), `NetworkPlayerAI.walkSpeed` (`@49 L33`) and `NetworkPlayerAI.runSpeed` (`@57 L34`). `NetworkPlayerAI.syncDamage @0 L695` is server-gated and sends `PacketType.PlayerInjuries` at `@46 L700` and `PacketType.PlayerDamage` at `@67 L701`; a jar-wide grep for `walkSpeed` hits only `IsoGameCharacter`, `IsoPlayer`, `NetworkPlayerAI`, `FakeClientManager`, `FakeClientManager$Movement` and `PlayerInjuriesPacket`, so that packet is the only carrier.

The server-side inputs to `IsoGameCharacter.calculateWalkSpeed` that a mod could move: `getFootInjurySpeedModifier` (`@0 L10020`), `calculateBaseSpeed` (`@34 L10025`, which is where the ENDURANCE moodle enters), the `fullSpeedMod` field (`@50 L10029`), the Sprinting perk (`@59 L10030`), `walkSpeedModifier` (`@136 L10050`), `getSlowFactor` (`@149 L10055`), `Thermoregulator.getMovementModifier` (`@203 L10064`), the Nimble perk for strafe (`@234 L10070`) and tree slow factors (`@337 L10082`); the outputs are the `WalkSpeed` and `RunSpeed` animation variables at `@369 L10089` and `@387 L10090`.

And the one door that dwarfs all of them, established in section C: `Hook.CalculateStats`. `LuaHookManager.AddEvents @15 L130` registers `'CalculateStats'` as one of eight hooks (`AutoDrink`, `UseItem`, `Attack`, `CalculateStats`, `ContextualAction`, `WeaponHitCharacter`, `WeaponSwing`, `WeaponSwingHitPoint`, `L127`–`L134`); `LuaHookManager.AddEvent @43 L118` installs each into the Lua `Hook` table created by `LuaHookManager.register @7 L163`; `Event.register @7 L122` / `@19 L123` gives each hook an `Add` and a `Remove` function. The catch is `Event.trigger`: `@0 L26` returns `false` when the callback list is empty, `@82 L36` and `@269 L55` invoke each callback with `LuaCaller.protectedCallVoid` (the callback's return value is discarded), and `@222 L49` / `@350 L64` return `true` unconditionally afterwards. So `Hook.CalculateStats.Add(fn)` suppresses `updateEndurance`, `updateTripping`, `updateThirst`, `updateStress`, `updateStats_WakeState`, `updateMorale` and `updateFitness` for every character on that host, whatever `fn` does or returns — it cannot be used selectively, and it takes hunger and thirst down with endurance and fatigue.

## E — the Thermoregulator, and whether body fat can insulate

`zombie/characters/BodyDamage/Thermoregulator` **is** in the exposer's class set (`LuaManager$Exposer.exposeAll @583`), along with `Thermoregulator$ThermalNode` (`@589`), `Metabolics` (`@595`), `Fitness` (`@601`), `BodyDamage` (`@577`) and `Nutrition` (`@5413`).

| Member | Signature | Flags | Exposed? | Side | Cite |
|---|---|---|---|---|---|
| `setSimulationMultiplier` | `(F)V` | `public static` | yes | whichever host calls it | member list + flags parse — a global tuning knob, not per character |
| `setMetabolicTarget` | `(Metabolics)V` | `public` | yes | wherever called | member list + flags; `Metabolics.<clinit>` MET values: Sleeping 0.8 (`@4 L7`), SeatedResting 1.0 (`@19 L8`), StandingAtRest 1.1 (`@33 L9`), SedentaryActivity 1.2 (`@48 L10`), Default 1.5 (`@63 L11`), DrivingCar 1.4 (`@78 L12`), LightDomestic 1.6 (`@93 L13`), HeavyDomestic 2.0 (`@109 L14`) |
| `setMetabolicTarget` | `(F)V` | `public` | yes | — | member list |
| `reset` | `()V` | `public` | yes | — | member list |

Those four are the **entire** writable surface: a scan of the class's declared members for `set*` returns only `setSimulationMultiplier`, the two `setMetabolicTarget` overloads and `reset` (`getSetPoint` and `updateSetPoint` matched the substring but are a getter and a private updater). There is **no insulation setter at all** — insulation is computed per node by `ThermalNode.calculateInsulation`, called from `updateNodesHeatDelta @162 L888`, and consumed at `@267 L905` as `delta /= (1 + node.insulation)`.

Body fat and nutrition already enter, and this is the finding that matters:

```java
// Thermoregulator.updateNodesHeatDelta
float fat = PZMath.clamp_01((player.getNutrition().getWeight() / 75.0 - 0.5) * 0.666);  // @0  L856
fat = (fat - 0.5f) * 2.0f;                        // @27 L859  -> [-1, +1], zero at ~93.8 kg
float fit = stats.get(CharacterStat.FITNESS);      // @34 L861
...
for each node {
    node.calculateInsulation();                                             // @162 L888
    ... delta = (airTemp - node.skinCelcius), wetness-scaled, ×0.3,
        then / (1 + node.insulation);                                       // @259 L904, @267 L905
    node.heatDelta = delta * node.skinSurface;                              // @279 L907
    if (node.primaryDelta > 0) {                          // cooling / hot   @292 L910
        float k = 0.2f + 0.8f * getBodyFluids();                            // @302 L913
        float q = Metabolics.Default.getMet() * node.primaryDelta * node.skinSurface
                  / (1 + node.insulation);                                  // @316 L915
        q *= k * (0.1f + 0.9f * windOrHumidityTerm);                        // @344 L916
        q *= humidityTerm;                                                  // @361 L917
        q *= (1.0f - 0.2f * fat);                                           // @368 L918  <-- fat suppresses heat loss
        q *= (1.0f + 0.2f * fit);                                           // @380 L919
        node.heatDelta -= q;                                                // @392 L920
    } else {                                              // heating / cold  @407 L924
        float k = 0.2f + 0.8f * getEnergy();                                // @407 L924  <-- hunger + fatigue
        float q = Metabolics.Default.getMet() * abs(node.primaryDelta) * node.skinSurface;  // @421 L926
        q *= k;                                                             // @444 L927
        q *= (1.0f + 0.2f * fat);                                           // @451 L928  <-- fat raises heat generation
        q *= (1.0f + 0.2f * fit);                                           // @463 L929
        ...
    }
}
```

`getEnergy @0 L1178` is `0.6 × (1 − (0.4h + 0.6h²)) + 0.4 × (1 − (0.4f + 0.6f²))` with `h = Stats.get(HUNGER)` and `f = Stats.get(FATIGUE)` (`@0 L1178`, `@43 L1179`, `@86 L1180`); `getBodyFluids @0 L1184` is `1 − Stats.get(THIRST)`. A jar-wide reference scan of the class shows `Nutrition` reached in exactly two places — the constructor at `@124` and `updateNodesHeatDelta @4`/`@7` (`Nutrition.getWeight`) — and no reference anywhere in the class to a lipid or fat term beyond the weight-derived `fat` above.

The primary and secondary totals, and what they buy:

```java
// Thermoregulator.updateBodyMultipliers
energyMultiplier = fluidsMultiplier = fatigueMultiplier = 1.0;      // @0 L1095, @5 L1096, @10 L1097
float p = PZMath.abs(primTotal); p *= p;                            // @15 L1099, @23 L1100
if (primTotal < 0) { energyMultiplier += 0.05*p;  fatigueMultiplier += 0.25*p; }  // @36 L1102, @51 L1103
else if (primTotal > 0) { fluidsMultiplier += 0.25*p; fatigueMultiplier += 0.25*p; }  // @77 L1105, @91 L1106
float s = PZMath.abs(secTotal); s *= s;                             // @105 L1109, @113 L1110
if (secTotal < 0) { energyMultiplier += 0.10*s;  fatigueMultiplier += 0.75*s; }   // @126 L1112, @141 L1113
else if (secTotal > 0) { fluidsMultiplier += 3.75*s; fatigueMultiplier += 1.75*s; }  // @168 L1115, @183 L1116
```

so cold (negative totals) raises the calorie-burn multiplier and fatigue accumulation, and heat (positive) raises thirst and fatigue; `fatigueMultiplier` is raised by *both* signs, which is why `updateStats_Awake`'s `getFatiqueMultiplier()` term is never below 1. `primTotal` and `secTotal` are written in `updateNodes @595` (the assembly there was not dumped) and read back through `getDbg_primTotal @0 L629` and `getDbg_secTotal @0 L633`. `getMovementModifier @0 L342` and `getCombatModifier @0 L367` are hypothermia/hyperthermia ladders only — `0.66` at level 2, `0.33` at level 3, and `0.0` (movement) or `0.10` (combat) at level 4 — with no nutrition term.

Verdict for the design: body fat already insulates, through `Nutrition.getWeight()`, with a fixed ±20 per cent band and a fixed 75 kg / 0.666 mapping, and the only way a mod changes the band or the mapping is by changing the weight the thermoregulator reads. There is no per-node insulation setter, so a mod cannot add a fat-driven insulation term of its own inside the thermal model.

## F — absences, each proved by a named jar-wide grep

| Identifier searched | Result | What it settles |
|---|---|---|
| `setEnduranceRegenMod` | `no class contains that literal` | no endurance-regen setter on any class |
| `setFatigueMod` | `no class contains that literal` | `getFatigueMod` is read-only — the Fitness ladder cannot be overridden |
| `setRecoveryMod` | `no class contains that literal` | `getRecoveryMod` cannot be overridden; it must be moved through the Fitness perk, the weight-band traits, or the clamped macro stores |
| `setPacingMod` | `no class contains that literal` | ditto for pacing |
| `setWalkSpeedModifier` | `no class contains that literal` | the field is engine-owned; `updateSpeedModifiers` is the only writer |
| `setAttackDelay` | `no class contains that literal` | no such setter anywhere |
| `setNimbleMod` | `no class contains that literal` | `getNimbleMod` is read-only |
| `setFatigueMultiplier` | `no class contains that literal` | the Thermoregulator's fatigue multiplier is computed only |
| `setEnduranceMultiplier` | `no class contains that literal` | ditto |
| `sleepFatigueReduction` | `zombie/ZomboidGlobals.class` only | the constant is loaded from Lua and read by nothing in the jar — the sleep restoration uses the 5-hour / 7-hour constants instead |
| `updateEndurance` | `IsoGameCharacter.class`, `IsoPlayer.class` only | there is no third endurance updater — no `IsoAnimal` override |
| `walkSpeed` | `IsoGameCharacter`, `IsoPlayer`, `NetworkPlayerAI`, `FakeClientManager`, `FakeClientManager$Movement`, `PlayerInjuriesPacket` | `PlayerInjuriesPacket` is the only packet carrying walk or run speed |
| `MoodleStat` (in the `exposeAll` dump, read end to end, 3055 lines) | absent | the moodle threshold object is unreachable from Lua even though `setLowestThreshold` … `setMaximumThreshold` are all declared — consistent with [#1141/C/C-only] |
| `ZomboidGlobals`, `LuaHookManager`, `PlayerCheats` (same dump) | absent | the endurance and fatigue rate constants cannot be written through the Java class; only the Lua `ZomboidGlobals` table, read once by `ZomboidGlobals.Load`, and only on the side that runs the updater ([#0569/C/C-only]) |
| `EnduranceChange` in `media/scripts/` | 0 files | no vanilla item script sets it, so the field is free for the item pass |
| `CalculateStats` in `media/lua/` | 0 files | the hook is registered by the engine and used by nothing in the shipped Lua, so a mod taking it is the only consumer |

Two absences deliberately *not* claimed: `forceSleep` was never grepped, and no packet-class grep was run for `speedMod`, `staggerTimeMod`, `combatSpeed` or `moveSpeed` individually — the packet statements in section D rest on the `walkSpeed` grep and on the read of `PlayerInjuriesPacket.write`, not on an exhaustive scan of every packet class.

## Claims candidates

Each line is worded as a claim, grade C, bound `C-only`, from this build's jar.

1. `CharacterStat` registers 24 stats in its class initialiser with an id, a minimum, a maximum and a default apiece, and builds a fixed 24-entry `ORDERED_STATS` array from them in the same initialiser — `CharacterStat.<clinit> @10–@287 L12–L35`, `@290 L36`, `@457`. [C/C-only]
2. Endurance registers on `[0,1]` with a default of 1 and fatigue on `[0,1]` with a default of 0, at `ORDERED_STATS` indices 3 and 4 — `CharacterStat.<clinit> @45 L15`, `@56 L16`, `@315`, `@321`. [C/C-only]
3. `Stats` holds a sparse map and falls back to the stat's own default, so no stat needs registering on a `Stats` instance — `Stats.get @0 L77`. [C/C-only]
4. Every `Stats` write passes the stat's own clamp and the setter returns whether the value changed — `Stats.set @0 L81`, `@6 L82`, `@29 L84`; `CharacterStat.clamp @0 L70`. [C/C-only]
5. `CharacterStat` exposes no setter for a stat's minimum, maximum or default, so the `[0,1]` range of endurance and fatigue cannot be widened — `CharacterStat` member list, 13 methods. [C/C-only]
6. `CharacterStat.register` is `public static` and uses `computeIfAbsent`, so registering an id that already exists returns the existing stat and never rewrites its bounds — `CharacterStat.register @0 L50`. [C/C-only]
7. A stat a mod registers is absent from `ORDERED_STATS` and therefore from every save and every sync: `Stats.save` and `Stats.write` walk that array and `SyncPlayerStatsPacket.getBitMaskForStat` returns 0 for a non-member — `Stats.save @0 L55`, `Stats.write @0 L69`, `getBitMaskForStat @29 L34`. [C/C-only]
8. `Stats.resetStats` iterates the whole `REGISTRY` rather than `ORDERED_STATS`, so it also resets a mod-registered stat — `Stats.resetStats @0 L112`. [C/C-only]
9. `Stats.isEnduranceRecharging` is a hard `false` and `getEnduranceWarning` and `getEnduranceDangerWarning` are hard `0.5` and `0.25` — `Stats.isEnduranceRecharging @0 L169`, `getEnduranceWarning @0 L165`, `getEnduranceDangerWarning @0 L161`. [C/C-only]
10. `IsoGameCharacter.updateEndurance` and `IsoPlayer.updateEndurance` are both `private` and are therefore two separate methods rather than an override pair, reached from `calculateStats` and from `updateInternal2` respectively — flags parse; `calculateStats @61 L10208`; `IsoPlayer.updateInternal2 @938 L2408`, `@2139 L2661`. [C/C-only]
11. `IsoGameCharacter.updateEndurance` does nothing but stamp `lastEndurance` and, under the unlimited-endurance cheat, reset endurance to 1.0 — `IsoGameCharacter.updateEndurance @0 L10360`, `@17 L10361`, `@24 L10362`. [C/C-only]
12. `IsoPlayer.updateEndurance` returns immediately both for an animal and on a game client, the animal test jumping to the same return — `IsoPlayer.updateEndurance @0 L3427`, `@13 L3428`. [C/C-only]
13. The running, sprinting and dragging drain is `rate × mult × 0.5 × asthma × GameTime.getMultiplier() × sneak`, with rate 5.2e-5 running and 4.55e-4 sprinting or dragging — `IsoPlayer.updateEndurance @83 L3442`, `@94 L3444`, `@105 L3447`, `@210 L3468`. [C/C-only]
14. That drain's multiplier is 1.4, raised to 2.9 by Overweight and then overridden to 0.8 by Athletic, then times 2.3, then times `getPacingMod` and `getHyperthermiaMod` — `IsoPlayer.updateEndurance @109 L3450`–`@167 L3460`. [C/C-only]
15. Asthmatic raises the endurance drain by replacing a 0.7 factor with 1.0 in both drain branches — `IsoPlayer.updateEndurance @176 L3461`, `@194 L3464`, `@373 L3481`, `@390 L3483`. [C/C-only]
16. Sneaking multiplies the endurance drain by 1.5 and reaches no regen arm — `IsoPlayer.updateEndurance @40 L3437`, `@49 L3439`. [C/C-only]
17. Under a heavy load the running drain is multiplied by 1.5, 1.9, 2.3 or 2.8 at moodle levels 1, 2, 3 and 4 — `IsoPlayer.updateEndurance` `tableswitch @259`, `@284 L3471`, `@290 L3472`, `@296 L3473`, `@302 L3474`. [C/C-only]
18. Walking drains endurance only above heavy-load level 2, at `runningEnduranceReduce × mult × 0.5 × asthma × sneak × multiplier × load ÷ 2`, with the base multiplier times 3.0 rather than 2.3 — `IsoPlayer.updateEndurance @350 L3480`, `@430 L3495`, `@513 L3510`. [C/C-only]
19. Standing still, endurance regenerates at `imobileEnduranceReduce × EnduranceRegenMultiplier × getRecoveryMod() × (1 − 0.85 × fatigue) × multiplier`, and only at heavy-load level 1 or below — `IsoPlayer.updateEndurance @566 L3518`, `@594 L3521`, `@608 L3522`. [C/C-only]
20. Walking, endurance regenerates at a quarter of the immobile rate with a `(1 − fatigue)` term and no 0.85 factor, but only while the endurance moodle is below level 2; at level 2 or above walking instead drains it at `runningEnduranceReduce ÷ 7 × sneak` — `IsoPlayer.updateEndurance @664 L3530`, `@688 L3532`, `@716 L3534`, `@754 L3537`. [C/C-only]
21. Sitting, resting and riding in a vehicle regenerate endurance at five times the immobile rate with a `(1 − 0.8 × fatigue)` term — `IsoPlayer.updateEnduranceWhileSitting @0 L3407`–`@33 L3410`, `updateEnduranceWhileInVehicle @21 L3418`–`@54 L3422`, `ZomboidGlobals.<clinit> @0 L11`. [C/C-only]
22. Asleep, endurance regenerates at twice the immobile rate, times `deltaMinutesPerDay` when every player is asleep, with no fatigue term — `IsoPlayer.updateStats_Sleeping @0 L3290`, `@8 L3292`, `@17 L3295`. [C/C-only]
23. No arm of the endurance model carries `GameTime.getDeltaMinutesPerDay()`, so endurance rates do not scale with day length while hunger, thirst and fatigue do — `IsoPlayer.updateEndurance @210 L3468` against `IsoGameCharacter.updateStats_Awake @119 L10262`. [C/C-only]
24. `getRecoveryMod` multiplies a Fitness ladder from 0.7 at level 0 to 1.6 at level 10 by Obese 0.4, Overweight 0.7, Very Underweight 0.7 and Emaciated 0.3 cumulatively, then by dead lipid and protein branches — `IsoGameCharacter.getRecoveryMod @14 L4617`–`@107 L4647`, `@124 L4650`, `@143 L4653`, `@162 L4656`, `@181 L4659`, `@211 L4665`, `@259 L4671`. [C/C-only]
25. `getPacingMod` runs 0.8 down to 0.43 over Fitness 1 to 10 and returns 0.9 at level 0 — `IsoGameCharacter.getPacingMod @13 L4500`–`@103 L4529`. [C/C-only]
26. `getHyperthermiaMod` returns 2.0 only at hyperthermia moodle level exactly 4 and 1.0 at every other level including 2 and 3 — `IsoGameCharacter.getHyperthermiaMod @0 L4533`, `@30 L4537`. [C/C-only]
27. The `EnduranceRegen` sandbox option maps its five values to 1.8, 1.3, 1.0, 0.7 and 0.4 and multiplies every endurance regen arm — `SandboxOptions.getEnduranceRegenMultiplier @0 L535`, `tableswitch @7`, `@40 L536`–`@64 L540`. [C/C-only]
28. A swing drains endurance by `(effectiveWeight × 0.18 × weapon fatigue mod × character fatigue mod × weapon endurance mod × 0.3 + two-hand term) × 0.04`, times 1.2 for Asthmatic, and only when the weapon's `UseEndurance` is set — `CombatManager.processWeaponEndurance @0 L1190`, `@49 L1200`, `@92 L1202`; `CharacterTraits.getTraitEnduranceLossModifier @0 L146`. [C/C-only]
29. A weapon's own fatigue modifier is 0.8 once the matching Blunt, Axe or Spear perk reaches 8 and 1.0 otherwise — `HandWeapon.getFatigueMod @0 L515`, `@27 L518`, `@95 L535`. [C/C-only]
30. `IsoGameCharacter.exert(float)` is `public` on an exposed class and removes that much endurance, times 0.9 for Jogger — `IsoGameCharacter.exert @0 L10504`, `@19 L10507`. [C/C-only]
31. On a server, `calculateStats` resets fatigue to its default on every call unless both `SleepAllowed` and `SleepNeeded` are true, and the reset runs before the `CalculateStats` Lua hook — `IsoGameCharacter.calculateStats @8 L10200`, `@38 L10201`, `@49 L10204`. [C/C-only]
32. `IsoPlayer.calculateStats` returns immediately when the game-client flag is set, so for a player the whole vanilla stat update including the fatigue reset is server-only — `IsoPlayer.calculateStats @0 L3280`, `@7 L3281`, `@10 L3283`. [C/C-only]
33. `calculateStats` fires the `CalculateStats` Lua hook and returns early when it comes back true, skipping endurance, tripping, thirst, stress, the wake-state updater, morale and fitness — `IsoGameCharacter.calculateStats @49 L10204`, `@59 L10205`, `@60 L10208`–`@84 L10221`. [C/C-only]
34. `CalculateStats` is one of eight hooks the engine registers into the Lua `Hook` table, each with an `Add` and a `Remove` function — `LuaHookManager.AddEvents @15 L130` (L127–L134), `AddEvent @43 L118`, `register @7 L163`, `Event.register @7 L122`, `@19 L123`. [C/C-only]
35. `Event.trigger` discards each Lua callback's return value and returns true whenever the callback list is non-empty, so registering any `Hook.CalculateStats` handler suppresses the whole vanilla stat update regardless of what the handler does — `Event.trigger @0 L26`, `@82 L36`, `@269 L55`, `@222 L49`, `@350 L64`. [C/C-only]
36. `IsoGameCharacter.updateStats_Sleeping` is an empty method, so a non-player character's stats do not move while it sleeps — `IsoGameCharacter.updateStats_Sleeping @0 L10239`. [C/C-only]
37. Awake fatigue accumulates at `fatigueIncrease × StatsDecrease × max(0.3, 1 − endurance) × multiplier × deltaMinutesPerDay × sleepTrait × thermoregulator fatigue multiplier ÷ restMod`, with `fatigueIncrease` 3.45e-5 — `IsoGameCharacter.updateStats_Awake @31 L10244`, `@52 L10246`, `@119 L10262`; `ZomboidGlobals.Load @202 L84`; `defines.lua:19`. [C/C-only]
38. Needs Less Sleep scales awake fatigue by 0.7 and Needs More Sleep by 1.3, and sitting on the ground, on furniture or resting *divides* it by 1.5 — `IsoGameCharacter.updateStats_Awake @71 L10251`, `@88 L10254`, `@115 L10260`. [C/C-only]
39. The thermoregulator's fatigue multiplier is raised by both cold and heat and never falls below 1, so it can only speed fatigue up — `Thermoregulator.updateBodyMultipliers @10 L1097`, `@51 L1103`, `@91 L1106`, `@141 L1113`, `@183 L1116`; `IsoGameCharacter.getFatiqueMultiplier @0 L14959`. [C/C-only]
40. Sleep removes fatigue over a nominal 5 hours above 0.3 and 7 hours below it, scaled by bed type from 0.60 on a floor to 1.15 on a good bed with a pillow, by Insomniac 0.5 and Night Owl 1.4, and by Needs Less Sleep 0.75 or Needs More Sleep 1.18 — `IsoPlayer.updateStats_Sleeping @84 L3301`, `@103 L3304`, `@111 L3308`–`@241 L3322`, `@307 L3331`, `@331 L3333`, `@356 L3339`, `@391 L3344`. [C/C-only]
41. Sleep restoration is gated on `timeOfSleep` exceeding `delayToActuallySleep`, with `timeOfSleep` advancing by `(1 ÷ minutesPerDay ÷ 60) × multiplier ÷ 2` per call — `IsoPlayer.updateStats_Sleeping @245 L3325`, `@268 L3327`, `@279 L3328`. [C/C-only]
42. `ZomboidGlobals.sleepFatigueReduction` is loaded from Lua and read nowhere in the jar — `ZomboidGlobals.Load @372 L100`; jar-wide grep `sleepFatigueReduction` returns `zombie/ZomboidGlobals.class` alone. [C/C-only]
43. A toxic-exposure branch adds 1.0e-4 per thirty-FPS multiplier unit to fatigue while fatigue is below 1 — `IsoGameCharacter.updateInternal @171 L9034`, `@195 L9037`. [C/C-only]
44. God mode resets fatigue, endurance and temperature every update — `IsoGameCharacter.updateInternal @2070 L9317`, `@2081 L9318`, `@2092 L9319`. [C/C-only]
45. The `TIRED` moodle fires above 0.6, 0.7, 0.8 and 0.9 on fatigue, on a strict greater-than, and is skipped when body health is exactly zero — `MoodleStat.<clinit> @46 L12`; `Moodle.Update @369 L145`, `@384 L146`, `@398 L147`, `@416 L150`, `@434 L153`, `@452 L156`. [C/C-only]
46. A `TIRED` level multiplies stomp power by 0.5, 0.2, 0.1 and 0.05, the same ladder the `ENDURANCE` moodle applies immediately before it, so the two compound — `CombatManager.attackCollisionCheck tableswitch @2677` (L986–L998) and `tableswitch @2802` (L1007–L1019). [C/C-only]
47. A `TIRED` or `ENDURANCE` moodle level costs `2.5` of firearm to-hit penalty per level by default, the sum scaled by the firearm moodle sandbox multiplier — `CombatManager.getMoodlesPenalty @71 L2522`, `@94`, `@153`; `CombatConfigKey.<clinit> @693 L38`, `@717 L39`. [C/C-only]
48. A `TIRED` level subtracts three from the defence roll against a zombie, where heavy load and panic subtract two — `IsoGameCharacter.testDefense @124 L14503`. [C/C-only]
49. A `TIRED` level of exactly 4 drains sanity at 2.0e-6 per update — `IsoGameCharacter.updateInternal @1160 L9172`, `@1176 L9174`. [C/C-only]
50. Endurance reaches movement and combat only through its moodle level: 0.15 off base speed and 0.07 off combat speed per level, and 0.25 onto idle speed — `IsoGameCharacter.calculateBaseSpeed @13 L9773`, `calculateCombatSpeed @95 L9874`, `calculateIdleSpeed @0 L9764`. [C/C-only]
51. `Moodles` declares no setter for a moodle level, so a mod must move the underlying stat — `Moodles` member list, 12 methods. [C/C-only]
52. The only `Mod`, `Modifier`, `Multiplier` or `Speed` setters on the character are `setSpeedMod`, `setStaggerTimeMod`, `setLevelUpMultiplier`, `setPathSpeed`, `setSneakLimpSpeedScale`, `setLastFallSpeed`, `IsoPlayer.setMoveSpeed`, `IsoPlayer.setCombatSpeed` and `IsoPlayer.setFitnessSpeed`, and all nine are `public` — member lists of both classes plus the flags parse. [C/C-only]
53. `setEnduranceRegenMod`, `setFatigueMod`, `setRecoveryMod`, `setPacingMod`, `setWalkSpeedModifier`, `setAttackDelay`, `setNimbleMod`, `setFatigueMultiplier` and `setEnduranceMultiplier` are absent from the jar in every form — nine jar-wide greps, each `no class contains that literal`. [C/C-only]
54. `setRunSpeedModifier` and `setEnduranceMod` exist only on script items and weapons, not on the character — jar-wide greps hitting `Clothing`, `Item` and `HandWeapon`. [C/C-only]
55. `updateSpeedModifiers` resets the run, walk and combat speed modifier fields to 1 and rebuilds them from worn items, and the server calls it immediately before every injuries packet, so those three fields cannot hold a mod's value — `IsoGameCharacter.updateSpeedModifiers @0 L10094`–`@10 L10096`; `NetworkPlayerAI.syncDamage @32 L698`. [C/C-only]
56. A server-computed walk and run speed reaches the client: the server copies them into `NetworkPlayerAI` and the client reads them back out of it instead of computing its own — `IsoPlayer.calculateWalkSpeed @0 L4051`, `@31 L4054`, `@145 L4078`, `@156 L4080`, `@164 L4081`. [C/C-only]
57. `PlayerInjuriesPacket` carries five floats — `IdleSpeed`, `StrafeSpeed`, `WalkInjury`, `NetworkPlayerAI.walkSpeed` and `runSpeed` — and is the only packet in the jar naming walk speed — `PlayerInjuriesPacket.write @10 L29`–`@57 L34`; jar-wide grep `walkSpeed`. [C/C-only]
58. `setUnlimitedEndurance` forces the cheat off rather than on when the caller lacks the `ToggleUnlimitedEndurance` capability — `IsoGameCharacter.setUnlimitedEndurance @0 L15473`, `@10 L15474`, `@22 L15477`. [C/C-only]
59. `setFitnessSpeed` computes an animation speed from the Fitness perk and the endurance moodle, caps it at 1.5, and below 0.85 snaps it to 1.0 and raises a `FitnessStruggle` flag — `IsoPlayer.setFitnessSpeed @0 L9137`, `@37 L9139`, `@49 L9142`, `@68 L9146`. [C/C-only]
60. `Thermoregulator`, `Thermoregulator$ThermalNode`, `Metabolics`, `Fitness`, `BodyDamage`, `Stats`, `CharacterStat`, `IsoGameCharacter`, `IsoPlayer`, `Moodles`, `MoodleType`, `CharacterTraits`, `SandboxOptions`, `ServerOptions`, `GameTime` and `Nutrition` are all in the exposer's class set, while `MoodleStat`, `ZomboidGlobals`, `LuaHookManager` and `PlayerCheats` are not — `LuaManager$Exposer.exposeAll` dump, read end to end. [C/C-only]
61. The thermoregulator's whole writable surface is `setSimulationMultiplier` (static), two `setMetabolicTarget` overloads and `reset`, and it declares no insulation setter — `Thermoregulator` member list plus flags parse. [C/C-only]
62. The thermoregulator derives a fatness term on `[-1, +1]` from `Nutrition.getWeight()` as `clamp01((w ÷ 75 − 0.5) × 0.666)` remapped by `(x − 0.5) × 2`, zero at about 93.8 kg — `Thermoregulator.updateNodesHeatDelta @0 L856`, `@27 L859`. [C/C-only]
63. That fatness term suppresses heat loss by up to 20 per cent when hot and raises heat generation by up to 20 per cent when cold, alongside a fitness term of the same size — `Thermoregulator.updateNodesHeatDelta @368 L918`, `@380 L919`, `@451 L928`, `@463 L929`. [C/C-only]
64. The thermoregulator's cold heat-generation term is scaled by `0.2 + 0.8 × getEnergy()`, where `getEnergy` is `0.6 × (1 − (0.4h + 0.6h²)) + 0.4 × (1 − (0.4f + 0.6f²))` over hunger and fatigue, and its hot term by `0.2 + 0.8 × (1 − thirst)` — `Thermoregulator.updateNodesHeatDelta @302 L913`, `@407 L924`; `getEnergy @0 L1178`, `@43 L1179`, `@86 L1180`; `getBodyFluids @0 L1184`. [C/C-only]
65. Node insulation is computed per node and divides the skin heat delta, with no setter anywhere in the class — `Thermoregulator.updateNodesHeatDelta @162 L888`, `@267 L905`. [C/C-only]
66. The thermoregulator reads `Nutrition` in exactly two places, its constructor and `updateNodesHeatDelta`, and never reads a lipid or a separate fat store — per-method reference scan of the class for `Nutrition`, `Weight`, `Fat` and `Lipid`. [C/C-only]
67. Eating writes endurance and fatigue into `Stats` from the item's `EnduranceChange` and `FatigueChange` and then sends a stats packet whose mask includes both — `IsoGameCharacter.Eat @181 L5770`, `@217 L5772`, `@688`, `@702`. [C/C-only]
68. No vanilla item script sets `EnduranceChange` — a grep of `media/scripts/` returns zero files. [C/C-only]
69. `getEffectiveFatigue` is `max(0, fatigue − 0.6) × 2.5`, a zero-below-0.6 rescaling of the stat — `IsoGameCharacter.getEffectiveFatigue @0 L16391`. [C/C-only]
70. Fatigue is subtracted directly from the character's detection range — `IsoGameCharacter.getDetectionRange @82 L16400`. [C/C-only]

## Not read

- **A contradiction with the register.** Row [#0561] says the endurance updater returns "immediately on a game client unless the character is an animal"; the bytecode at `IsoPlayer.updateEndurance @0 L3427` (raw bytes `42 182 1 197 / 154 0 9 / 178 2 102 / 153 0 4 / 177`) reads `if (isAnimal() || GameClient.client) return`, so an animal returns as well. The claim needs re-reading before it is quoted again.
- Whether Kahlua can actually call `CharacterStat.register` as a static on an exposed class, and what a mod-registered stat does across a save and reload, are live-run questions; the exposure test says only that the class is reachable.
- Whether the `Hook` table and the `CalculateStats` hook exist in a dedicated server's Lua environment, and whether `Event.trigger`'s unconditional true is really reached on that host, need a run — the reading is static.
- The `tableswitch` for `SandboxOptions.getEnduranceRegenMultiplier` was read, but which sandbox UI label corresponds to each of the five integers was not; the mapping 1 → 1.8 … 5 → 0.4 is the switch's, not the UI's.
- The unit of the sleep `dt` at `IsoPlayer.updateStats_Sleeping @245 L3325` — `1 ÷ getMinutesPerDay() ÷ 60 × multiplier ÷ 2` — was not reconciled against `getMultiplier`, so the "5 hours" and "7 hours" above are the code's named constants and not a derived wall-clock or game-clock duration.
- `delayToActuallySleep` is read but never located: nothing was dumped that writes it, so how long the gate at `@279 L3328` actually holds is unknown.
- The cadence of `NetworkPlayerAI.syncDamage`, and therefore of `PlayerInjuriesPacket`, was not read: the caller is not a direct method reference inside `NetworkPlayerAI` (the reference scan found none) and is most likely an `UpdateLimit` method handle, which the scan does not resolve.
- `Thermoregulator.updateNodes @595` assembles `primTotal` and `secTotal`; that body was not dumped, so the real range of the two totals — and hence the real size of the cold energy bonus and the heat fatigue penalty — is still unbounded here, exactly as [#0464] leaves it.
- `ThermalNode.calculateInsulation` was not dumped, so what clothing contributes to node insulation, and whether any body term enters it, is unread.
- `IsoPlayer.updateMovementRates`, called next to `updateSpeedModifiers` in `syncDamage`, was not dumped; whether it reads endurance or fatigue is unknown.
- `Fitness.incFutureStiffness` reads the `TIRED` moodle at `@170` but the surrounding arithmetic was not read, so what tiredness does to exercise stiffness is unread.
- No grep was run for `forceSleep`, and no per-packet grep was run for `speedMod`, `staggerTimeMod`, `combatSpeed` or `moveSpeed`, so the "no packet carries it" statements in section D are bounded by the `walkSpeed` grep and the one packet body that was read.
- `CombatConfig.set` is `public` and `CombatConfig` was not tested against the exposer's class set, so whether a mod can retune `TIRED_TO_HIT_BASE_PENALTY` at runtime is unsettled.
- Everything here is a static read of one jar of `42.20.4`; no rate, no cadence and no cross-side behaviour on these paths was measured.
