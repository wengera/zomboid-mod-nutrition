# Jar reading: the health, injury, mood and thermal surfaces a nutrition mod can drive

Read from one jar of build `42.20.4` (`b0bbce05d5`) on 2026-09-27 with `pz-b42/tools/pzdis.py` via `./pz.sh`.
Access flags come from a scratch constant-pool parser rebuilt over `pz-b42/tools/cp.py` for this session.
Exposure is strict membership in the class set of `LuaManager$Exposer.exposeAll()`, dumped whole (3055 instruction lines) and searched.
Every offset and line belongs to this build only; a patch moves all of them.

## Summary for the design

The entire body-damage tick is server-only in multiplayer, and not by a gate at the caller but by an early return inside the tick itself: `BodyDamage.Update` returns at once on a game client for a live local player, and `BodyPart.DamageUpdate` does the same, so health regeneration, the severe-moodle health loss, poison decay, wound healing, infection progress and the thermoregulator all run on the server and nowhere else.
`IsoPlayer.calculateStats` returns on a game client before calling its super, so every registered stat — hunger, thirst, stress, panic, pain, fatigue, endurance, morale, fitness — is also computed server-side only.
That makes the server the only place a nutrition mod can express a consequence, and the client purely a display.
There are exactly 24 registered stats and they are a far richer surface than the five nutrition floats: `PAIN`, `PANIC`, `STRESS`, `UNHAPPINESS`, `BOREDOM`, `SICKNESS`, `FOOD_SICKNESS`, `POISON`, `TEMPERATURE`, `WETNESS`, `SANITY`, `MORALE`, `ANGER`, `DISCOMFORT`, `IDLENESS`, `INTOXICATION`, `ZOMBIE_FEVER` among them, each with its own min, max and default, each clamped on write, and all 24 pushed to the client every second inside the player-stats packet.
Writing a stat is a one-line `getStats():set(CharacterStat.PANIC, x)` and it is a real gameplay effect because the vanilla moodles read those same stats.
Overall health is the one quantity that does **not** work that way: `setOverallBodyHealth` is a raw field write with no clamp, and `calculateOverallHealth` recomputes the field from the 17 body parts at the end of every server tick, so a direct write is erased within a frame.
The supported route is `ReduceGeneralHealth(f)` and `AddGeneralHealth(f)`, which spread the amount over the parts — that is what the engine's own severe-moodle drain and its lethal infection use, the latter with the literal `ReduceGeneralHealth(110.0)`.
A slow drain is therefore a per-tick `ReduceGeneralHealth(rate * GameTime:getMultiplier())` on the server, and a healing-rate change is either `setStandardHealthAddition`/`setReducedHealthAddition`/`setSeverlyReducedHealthAddition` (the three awake regeneration tiers, public setters, defaults 0.002/0.0013/0.0008) or `setHealthReductionFromSevereBadMoodles` (default 0.0165), which is the single constant behind every severe-moodle health loss the engine has.
The regeneration tier itself is chosen from moodle levels and is now settled rather than inferred: the `tableswitch` runs `low=0 high=3` with its default at the asleep block, so tier 0 is the standard addition, tier 1 the reduced, tier 2 the severely reduced, tier 3 adds literally zero, and asleep (tier −1) falls to the default and takes the sleeping addition instead.
For per-part effects the mod has a wide door: every wound timer, the four poultice factors, the splint factor, stiffness, `woundInfectionLevel`, `infectedWound`, `fractureTime` and per-part `health` all have public setters on the exposed `BodyPart`, and `LuaManager$GlobalObject.syncBodyPart(part, mask)` is a server-only Lua global that pushes any subset of 41 per-part fields to the owning client over `BodyPartSyncPacket` — bit value 1 is the part's health.
Two engine hooks make the whole thing cheaper than polling: `LuaEventManager.triggerEvent("OnPlayerGetDamage", chr, tag, amount)` fires once per nonzero health-loss term with the tags `POISON`, `HUNGRY`, `SICK`, `BLEEDING`, `THIRST`, `HEAVYLOAD` and `INFECTION`, and `LuaHookManager.TriggerHook("CalculateStats", chr)` lets a mod cancel the entire vanilla stat update by returning true.
Cold and heat tolerance is a near-wall: `Thermoregulator` has only two public setters (`setSimulationMultiplier`, static, and `setMetabolicTarget`) and `Thermoregulator$ThermalNode` has none at all, so insulation, wind resistance and node temperature are read-only — but `CharacterStat.TEMPERATURE` is a two-way door, because `Thermoregulator.updateHeatDeltas` lerps the core node halfway toward whatever the stat holds before writing the core back into it.
Death needs no new API: `IsoGameCharacter.isDead` is true when `health <= 0` or `getBodyDamage().getHealth() <= 0`, and `IsoGameCharacter.updateInternal` then calls `die()` on the server only — so `ReduceGeneralHealth(110)` or `setHealth(0)` is a kill, and `die()` itself is public final on an exposed class.
There is no fainting or unconscious state anywhere in the jar (`Unconscious`, `Fainted`, `setUnconscious` are all jar-wide absent); `setAsleep`, `forceAwake` and `setKnockedDown` are all bare field writes, and the honest read is that a mod can set the flags but nothing in the jar says an animation or a state machine follows.
Several names the design brief assumed do not exist on this build: `FoodSicknessLevel`, `getInfectionLevel`, `FakeInfectionLevel`, `getWoundHealingRate`, `setHealthAdditionModifier`, `setDamageScaler`, `setHealingRate`, `setNausea` and `CharacterStat.FEAR` are each absent from every class entry in the jar, and drunkenness is `CharacterStat.INTOXICATION`, not `DRUNKENNESS`.
The last practical warning is that the player-stats packet carries the 24 stats and `BodyDamage.saveMainFields` — eleven fields that do **not** include overall health or any per-part field — so a mod that changes health on the server must either let the engine's own body-damage sync carry it or push it with `syncBodyPart`, and a mod that writes any stat on a client is overwritten within a second.

## A — `BodyDamage`: health, regeneration, sickness, pain, temperature

`BodyDamage` is `public final synchronized` and is in the exposer class set (`exposeAll` @577), so every public member below is reachable from Lua.

### A.1 The side gate that governs all of it

`BodyDamage.Update @21-@62 L2159-2165` reads `GameClient.client`; when it is set it casts the parent to `IsoPlayer`, and for a non-null, alive, **local** player it returns at `@62` having done nothing, while for a non-local player it calls `RestoreToFullHealth` first.
Only a null cast or a dead player falls through to the body simulation on a client.
So on a multiplayer client the entire method is dead for the player you are playing.

`BodyDamage.Update @261-@270 L2212-2213` then returns early when `getOverallBodyHealth()` is **exactly** `0.0f` (`fcmpl` + `ifne`), skipping regeneration, the moodle drain, poison, pain, infection, the per-part update and `calculateOverallHealth`. A negative health does not trigger it.

`IsoGameCharacter.updateInternal @1524-@1555 L9222-9230` gates both `getBodyDamage().Update()` and `calculateStats()` on `SystemDisabler.doCharacterStats`.

| member | signature | flags | exposed? | side | synced-by | cite |
|---|---|---|---|---|---|---|
| `Update` | `()V` | public | yes | server only in MP (client returns for the live local player) | — | `BodyDamage.Update @21-@62 L2159-2165` |
| `Update` (zero-health stop) | — | — | — | server | — | `BodyDamage.Update @261-@270 L2212-2213` |
| `RestoreToFullHealth` | `()V` | public | yes | called on a client for **remote** players | — | `BodyDamage.Update @58 L2163` |
| `getBodyDamage` | `()Lzombie/characters/BodyDamage/BodyDamage;` | public | yes | both | — | `fl_igc` (flags read) |
| `getBodyDamageRemote` | `()Lzombie/characters/BodyDamage/BodyDamage;` | public | yes | unread | — | flags only, body not dumped |

### A.2 Overall health

`calculateOverallHealth @0-@72 L2527-2538` computes `overall = 100 - min(100, Σ_i (100 - part_i.getHealth()) * BodyPartType.getDamageModifyer(i) + getDamageFromPills())` and calls `setOverallBodyHealth` with it. It runs at `@2163 L2479` at the end of every `Update`.

`ReduceGeneralHealth @0-@73 L1122-1133`: if `getOverallBodyHealth() <= 10.0` it first calls `parentChar.forceAwake()`; it returns when the argument is `<= 0`; otherwise it divides the amount by `BodyPartType.ToIndex(MAX)` and calls `BodyPart.ReduceHealth(share / BodyPartType.getDamageModifyer(i))` on every part.

`AddGeneralHealth @0-@109 L1101-1119`: counts the parts with `getHealth() < 100`, divides the amount by that count, and calls `BodyPart.AddHealth(share)` on each such part. No damage modifier.

| member | signature | flags | exposed? | side | synced-by | cite |
|---|---|---|---|---|---|---|
| `getOverallBodyHealth` | `()F` | public | yes | server authoritative | not in `PlayerStatsPacket` | `BodyDamage.getHealth @0-@4 L1724` delegates to it |
| `setOverallBodyHealth` | `(F)V` | public | yes | server | — | `BodyDamage.setOverallBodyHealth @0-@5 L2735-2736` — raw `putfield`, no clamp, erased by the next `calculateOverallHealth` |
| `getHealth` | `()F` | public | yes | server | — | `BodyDamage.getHealth @0-@4 L1724` → `getOverallBodyHealth` |
| `ReduceGeneralHealth` | `(F)V` | public | yes | server | via per-part `health` | `BodyDamage.ReduceGeneralHealth @25-@73 L1129-1133` |
| `AddGeneralHealth` | `(F)V` | public | yes | server | via per-part `health` | `BodyDamage.AddGeneralHealth @43-@109 L1111-1119` |
| `calculateOverallHealth` | `()V` | public | yes | server | — | `BodyDamage.calculateOverallHealth @26-@69 L2530-2537` |
| `overallBodyHealth` (field) | `F` | private | n/a | — | — | flags read |

### A.3 The health-regeneration path

`Update @549-@588 L2267-2271` starts the addition accumulator at `0.0f`; if `getHealthFromFoodTimer() > 0` it adds `getHealthFromFood() * GameTime.instance.getMultiplier()` and then decrements the timer by `1 * multiplier`.

`Update @591-@752 L2274-2297` builds the tier index: `1` when `HUNGRY`, `SICK` or `THIRST` is exactly level 2; `2` when any of the three is exactly level 3; `3` when `HUNGRY` or `THIRST` is exactly level 4 (`SICK` is absent from this arm); `-1` when `parentChar.isAsleep()`. Each test is `if_icmpeq` and they run in ascending order, so the highest match wins.

`Update @754 L2301` is a `tableswitch` with `default -> 839`, `low=0`, `high=3`, cases `0 -> 784`, `1 -> 801`, `2 -> 818`, `3 -> 835`. Case 0 adds `getStandardHealthAddition() * multiplier`; case 1 `getReducedHealthAddition() * multiplier`; case 2 `getSeverlyReducedHealthAddition() * multiplier`; case 3 adds `fconst_0`. Tier `-1` falls to the default at `839`, so an asleep character takes none of the four.

`Update @839-@924 L2316-2323`: when asleep, a game client adds `15.0 * GameTime.getGameWorldSecondsSinceLastUpdate() / 3600` and a non-client adds `getSleepingHealthAddition() * multiplier`; then a `HUNGRY` or `THIRST` level of exactly 4 zeroes the whole accumulator.
`Update @925-@927 L2328` passes the accumulator to `AddGeneralHealth`.

Constructor defaults, `BodyDamage.<init>`: `standardHealthAddition` 0.002 (`@61 L74`), `reducedHealthAddition` 0.0013 (`@67 L75`), `severlyReducedHealthAddition` 0.0008 (`@73 L76`), `sleepingHealthAddition` 0.02 (`@79 L77`), `healthFromFood` 0.015 (`@85 L78`), `healthReductionFromSevereBadMoodles` 0.0165 (`@91 L79`), `standardHealthFromFoodTime` 1600 (`@97 L80`), `infectionGrowthRate` 0.001 (`@37 L68`), `painReductionFromMeds` 30.0 (`@140 L88`), `standardPainReductionWhenWell` 0.01 (`@146 L89`), `coldProgressionRate` 0.0112 (`@182 L102`).

| member | signature | flags | exposed? | side | synced-by | cite |
|---|---|---|---|---|---|---|
| `getStandardHealthAddition` / `set…` | `()F` / `(F)V` | public / public | yes | server | no | `BodyDamage.Update @786 L2303`; default `<init> @61 L74` |
| `getReducedHealthAddition` / `set…` | `()F` / `(F)V` | public / public | yes | server | no | `BodyDamage.Update @803 L2306`; default `<init> @67 L75` |
| `getSeverlyReducedHealthAddition` / `set…` | `()F` / `(F)V` | public / public | yes | server | no | `BodyDamage.Update @820 L2309`; default `<init> @73 L76` |
| `getSleepingHealthAddition` / `set…` | `()F` / `(F)V` | public / public | yes | server | no | `BodyDamage.Update @877 L2320`; default `<init> @79 L77` |
| `getHealthFromFood` / `set…` | `()F` / `(F)V` | public / public | yes | server | no | `BodyDamage.Update @562 L2270`; default `<init> @85 L78` |
| `getHealthFromFoodTimer` / `set…` | `()F` / `(F)V` | public / public | yes | server writes it; **client receives it** | `BodyDamage.saveMainFields @62-@70 L316` | `BodyDamage.Update @552-@588 L2269-2271` |
| `getStandardHealthFromFoodTime` / `set…` | `()I` / `(I)V` | public / public | yes | server | no | default `<init> @97 L80` |
| `getHealthFromFoodTimeByHunger` | `()F` | **private** | n/a — wall | server | — | flags read; not callable from Lua |
| `getHealthReductionFromSevereBadMoodles` / `set…` | `()F` / `(F)V` | public / public | yes | server | no | `BodyDamage.Update @1152 L2357`, `@1215 L2363`, `@1268 L2368`, `@1303 L2374`, `@1338 L2378`, `@1465 L2390`; default `<init> @91 L79` |

### A.4 The severe-moodle health loss, and the Lua event that reports it

All six terms accumulate into one float and are handed to `ReduceGeneralHealth` at `BodyDamage.Update @1514 L2395`, multiplied by `GameTime.instance.getMultiplier()`, with `red = getHealthReductionFromSevereBadMoodles()`:

| trigger | term | cite |
|---|---|---|
| `HUNGRY` level exactly 4 | `red / 50` | `BodyDamage.Update @1151-@1172 L2357-2358` |
| `SICK` level exactly 4 **and** `FOOD_SICKNESS > ZOMBIE_INFECTION` | `red` | `BodyDamage.Update @1190-@1231 L2362-2364` |
| `SICK` level exactly 4, else-arm: `SandboxOptions.woundInfectionFactor > 0` **and** `getGeneralWoundInfectionLevel() > ZOMBIE_INFECTION` | `red` | `BodyDamage.Update @1235-@1284 L2367-2369` |
| `BLEEDING` level exactly 4 | `red` | `BodyDamage.Update @1285-@1319 L2373-2375` |
| `THIRST` level exactly 4 | `red / 10` | `BodyDamage.Update @1320-@1358 L2377-2379` |
| `HEAVY_LOAD > 2`, not in a vehicle, not asleep, not sitting, metabolic target ≠ `Metabolics.SeatedResting`, not (server and fastForward), `getHealth() > 75`, and `Rand.PerThirtiethOfASecond(10)` | `red / ((5 - heavyLoadLevel) / 10)`, plus `parentChar.addBackMuscleStrain(term / 2)` | `BodyDamage.Update @1359-@1511 L2381-2392` |

Each nonzero term then fires a Lua event: `LuaEventManager.triggerEvent("OnPlayerGetDamage", parentChar, tag, Float.valueOf(term))` with the tags `POISON` (`@1526-@1541 L2398`), `HUNGRY` (`@1551-@1566 L2401`), `SICK` (`@1576-@1591 L2404`), `BLEEDING` (`@1601-@1616 L2407`), `THIRST` (`@1626-@1641 L2410`), `HEAVYLOAD` (`@1651-@1666 L2413`). The infection arms fire the same event with the tag `INFECTION` (`@1909-@1924 L2449`, `@2037-@2052 L2461`, `@2112-@2127 L2469`).

### A.5 Sickness, poison and infection

There is no `FoodSicknessLevel`, `setPoisonLevel` or `getInfectionLevel` on a character on this build (see § F). Sickness and poison are registered stats.

`BodyDamage.Update @962-@1024 L2343-2346`: with `POISON > 0`, if `POISON > 10` **and** the `SICK` moodle is at level ≥ 1, the health-loss accumulator gains `0.0035 * min(POISON / 10, 3) * multiplier` — so the poison drain caps at `0.0105` per multiplier unit.
`@1028-@1062 L2349-2350`: a `FOOD_EATEN` level above 0 adds an extra decay term `1.5e-4 * level`.
`@1064-@1090 L2353`: `POISON` is then reduced by `foodEatenTerm + ZomboidGlobals.poisonLevelDecrease * multiplier`.
`@1091-@1133 L2354`: `FOOD_SICKNESS` gains `getInfectionGrowthRate() * (2 + Math.round(POISON / 10)) * multiplier`.

`BodyDamage.Update @1877-@2130 L2445-2469` is the zombie-infection path, switching on `SandboxOptions.lore.mortality`: value 1 calls `ReduceGeneralHealth(110.0)` immediately and pins `ZOMBIE_INFECTION` to its maximum; value 7 does nothing; otherwise it advances `infectionTime`, sets `ZOMBIE_INFECTION` to `min(elapsed / infectionMortalityDuration, 1) * 100`, and at exactly 1 calls `ReduceGeneralHealth(110.0)`, else reduces health toward `100 * (1 - f^4)`.

`BodyDamage.Update @2233-@2362 L2497-2507`: `isReduceFakeInfection()` and `parentChar.getReduceInfectionPower()` each drain `ZOMBIE_FEVER`, the latter by `getInfectionGrowthRate() * multiplier` while decrementing itself — that is the infection-resistance dial, and `IsoGameCharacter.setReduceInfectionPower(F)` is public.

| member | signature | flags | exposed? | side | synced-by | cite |
|---|---|---|---|---|---|---|
| `CharacterStat.FOOD_SICKNESS` | static field, `Stats.get/set` | public static final; `Stats.set` public | yes (`Stats` @685, `CharacterStat` @691) | server | `PlayerStatsPacket` (`Stats.save`, index 6) | `BodyDamage.Update @1095-@1133 L2354` |
| `CharacterStat.POISON` | as above | as above | yes | server | packet, index 14 | `BodyDamage.Update @954-@1090 L2342-2353` |
| `CharacterStat.SICKNESS` | as above | as above | yes | server | packet, index 16 | registered `CharacterStat.<clinit> @195-@203 L28` (0…1, default 0) |
| `CharacterStat.ZOMBIE_INFECTION` | as above | as above | yes | server | packet, index 23 | `BodyDamage.Update @2007-@2022 L2458` |
| `CharacterStat.ZOMBIE_FEVER` | as above | as above | yes | server | packet, index 22 | `BodyDamage.Update @2249-@2272 L2498` |
| `getInfectionGrowthRate` / `set…` | `()F` / `(F)V` | public / public | yes | server | no | `BodyDamage.Update @1099 L2354`; default `<init> @37 L68` |
| `isInfected` / `setInfected` | `()Z` / `(Z)V` | public / public | yes | server | no | `BodyDamage.Update @1878 L2445` |
| `getInfectionTime` / `set…` | `()F` / `(F)V` | public / public | yes | server writes; client receives | `saveMainFields @89-@97 L319` | `BodyDamage.Update @1976-@1986 L2456` |
| `getInfectionMortalityDuration` / `set…` | `()F` / `(F)V` | public / public | yes | server writes; client receives | `saveMainFields @98-@106 L320` | `BodyDamage.Update @1959-@1973 L2453-2454` |
| `getCurrentTimeForInfection` | `()F` | **private** | n/a — wall | — | — | flags read |
| `isIsFakeInfected` / `setIsFakeInfected` | `()Z` / `(Z)V` | public / public | yes | server | no | `BodyDamage.Update @2410-@2414 L2515` |
| `isReduceFakeInfection` / `set…` | `()Z` / `(Z)V` | public / public | yes | server writes; client receives | `saveMainFields @45-@61 L315` | `BodyDamage.Update @2234 L2497` |
| `getGeneralWoundInfectionLevel` | `()F` | public | yes | server | — | `BodyDamage.Update @1250 L2367`; body not dumped |
| `getApparentInfectionLevel` | `()F` | public | yes | unread | — | flags only |
| `IsoGameCharacter.getReduceInfectionPower` / `set…` | `()F` / `(F)V` | public / public | yes | server | not traced | `BodyDamage.Update @2277-@2339 L2502-2504` |

### A.6 Wetness, cold and temperature

`BodyDamage.Update @225-@258 L2202-2210` calls, in order, `UpdateDraggingCorpse`, `UpdateWetness`, `UpdateCold`, `UpdateBoredom`, `UpdateStrength`, `UpdatePanicState`, `UpdateTemperatureState`, `UpdateDiscomfort`, `UpdateIllness`; the `Thermoregulator.update()` call is just above at `@222 L2199`. All of them therefore inherit the server-only gate. Their bodies were not dumped this session except where noted.

There is no `BodyDamage.getTemperature`/`setTemperature`; body temperature is `CharacterStat.TEMPERATURE`, registered with min 20, max 40, default 37 at `CharacterStat.<clinit> @217-@228 L30`. `Wetness` is likewise `CharacterStat.WETNESS`, min 0 max 100 default 0 (`<clinit> @254-@263 L33`).

| member | signature | flags | exposed? | side | synced-by | cite |
|---|---|---|---|---|---|---|
| `UpdateWetness` | `()V` | public | yes | server | — | `BodyDamage.Update @230 L2203` |
| `increaseBodyWetness` / `decreaseBodyWetness` | `(F)V` | public | yes | server | per-part `wetness` not in the sync field list | flags read |
| `CharacterStat.WETNESS` | via `Stats` | public static final | yes | server | packet, index 21 | `CharacterStat.<clinit> @254-@263 L33` |
| `CharacterStat.TEMPERATURE` | via `Stats` | public static final | yes | server | packet, index 18 | `CharacterStat.<clinit> @217-@228 L30` |
| `UpdateCold` | `()V` | public | yes | server | — | `BodyDamage.Update @234 L2204` |
| `getCatchACold` / `setCatchACold` | `()F` / `(F)V` | public / public | yes | server writes; client receives | `saveMainFields @0-@8 L311` | flags read |
| `isHasACold` / `setHasACold` | `()Z` / `(Z)V` | public / public | yes | server writes; client receives | `saveMainFields @9-@25 L312` | flags read |
| `getColdStrength` / `setColdStrength` | `()F` / `(F)V` | public / public | yes | server writes; client receives | `saveMainFields @26-@34 L313` | flags read |
| `getColdProgressionRate` / `set…` | `()F` / `(F)V` | public / public | yes | server | no | default `<init> @182 L102` = 0.0112 |
| `getColdReduction` / `set…` | `()F` / `(F)V` | public / public | yes | server writes; client receives | `saveMainFields @80-@88 L318` | flags read |
| `getColdDamageStage` / `set…` | `()F` / `(F)V` | public / public | yes | server writes; client receives | `saveMainFields @107-@115 L321` | flags read |
| `getTimeToSneezeOrCough` / `set…` | `()F` / `(F)V` | public / public | yes | server writes; client receives (narrowed to int) | `saveMainFields @35-@44 L314` | flags read |
| `UpdateTemperatureState` | `()V` | **private** | n/a — wall | server | — | flags read |

### A.7 Pain

`BodyDamage.Update @1669-@1843 L2419-2435`. When `parentChar.getPainEffect() > 0` the stat `PAIN` is reduced by `0.023333333 * GameTime.getThirtyFPSMultiplier()` and `painEffect` is decremented; otherwise `setPainDelta(0)` and the target is computed as `Σ_i part_i.getPain() * BodyPartType.getPainModifyer(i)` (`@1736-@1777 L2426-2428`) minus `getPainReduction()` (`@1780-@1786 L2431`). If the target exceeds the current `PAIN`, `PAIN` gains `(target - current) / 500` (`@1802-@1825 L2433`); otherwise `PAIN` is set to the target outright (`@1832-@1843 L2435`).
`@1844-@1876 L2439-2441`: `setPainReduction(getPainReduction() - 0.005 * GameTime.getMultiplier())`, floored at 0.
`@2431-@2466 L2521-2522`: if `PAIN` is unchanged over the whole tick, it decays by `0.25 * getThirtyFPSMultiplier()`.

| member | signature | flags | exposed? | side | synced-by | cite |
|---|---|---|---|---|---|---|
| `getPainReduction` / `setPainReduction` | `()F` / `(F)V` | public / public | yes | server writes; client receives | `saveMainFields @71-@79 L317` | `BodyDamage.Update @1782-@1786 L2431`, `@1846-@1860 L2439` |
| `getPainReductionFromMeds` / `set…` | `()F` / `(F)V` | public / public | yes | server | no | default `<init> @140 L88` = 30.0 |
| `getStandardPainReductionWhenWell` / `set…` | `()F` / `(F)V` | public / public | yes | server | no | default `<init> @146 L89` = 0.01 |
| `getInitialThumpPain` / `Scratch` / `Bite` / `Wound`, `getContinualPainIncrease`, all with setters | `()F` / `(F)V` | public / public | yes | server | no | flags read; bodies not dumped |
| `getRemotePainLevel` / `set…` | `()I` / `(I)V` | public / public | yes | server writes for the remote view | `BodyDamageSync$Updater` | `BodyDamageSync$Updater.update @106-@114 L96` |
| `CharacterStat.PAIN` | via `Stats` | public static final | yes | server | packet, index 12; also `SyncPlayerStats` mask | `CharacterStat.<clinit> @148-@157 L24` (0…100, default 0) |
| `IsoGameCharacter.getPainEffect` / `setPainEffect` | `()F` / `(F)V` | public / public | yes | server | not traced | `BodyDamage.Update @1673 L2419`, `@1720 L2421` |
| `IsoGameCharacter.PainMeds` | `(F)V` | public | yes | unread | — | flags only |

### A.8 What the player-stats packet actually carries

`BodyDamage.saveMainFields @0-@116 L311-322` writes exactly eleven values, in this order: `getCatchACold()` float, `isHasACold()` byte, `getColdStrength()` float, `getTimeToSneezeOrCough()` narrowed to int, `isReduceFakeInfection()` byte, `healthFromFoodTimer` float, `painReduction` float, `coldReduction` float, `infectionTime` float, `infectionMortalityDuration` float, `coldDamageStage` float.
Neither `overallBodyHealth` nor any per-part field is in it.

`Stats.save(ByteBuffer) @0-@39 L55-58` iterates `CharacterStat.ORDERED_STATS` and writes one float per entry with no mask, so all 24 stats ride together.
`ORDERED_STATS` order, from `CharacterStat.<clinit> @290-@457 L36`: 0 `ANGER`, 1 `BOREDOM`, 2 `DISCOMFORT`, 3 `ENDURANCE`, 4 `FATIGUE`, 5 `FITNESS`, 6 `FOOD_SICKNESS`, 7 `HUNGER`, 8 `IDLENESS`, 9 `INTOXICATION`, 10 `MORALE`, 11 `NICOTINE_WITHDRAWAL`, 12 `PAIN`, 13 `PANIC`, 14 `POISON`, 15 `SANITY`, 16 `SICKNESS`, 17 `STRESS`, 18 `TEMPERATURE`, 19 `THIRST`, 20 `UNHAPPINESS`, 21 `WETNESS`, 22 `ZOMBIE_FEVER`, 23 `ZOMBIE_INFECTION`.

`SyncPlayerStatsPacket.write @0-@91 L66-78`: writes the player id, then `syncParams` as an int; when `syncParams == -1` it writes the whole `Nutrition` object via `Nutrition.save` and nothing else, otherwise it walks `ORDERED_STATS` and calls `Stats.write(bb, i)` for each set bit.
`SyncPlayerStatsPacket.getBitMaskForStat @0-@30 L29-34` returns `1 << index` for a stat's `ORDERED_STATS` index, and 0 for a stat that is not in the array.
`Stats.write(ByteBuffer, byte) @0-@48 L69-74` writes a single stat by index and warns `'Wrong field %d provided for Stats::write method'` for an out-of-range index.

`GameServer.sendSyncPlayerFields(IsoPlayer, byte) @0-@35 L2459-2463` returns when the player is null or `onlineId == -1`, else sends `PacketType.SyncPlayerFields` with `{player, mask}`.
`LuaManager$GlobalObject.sendSyncPlayerFields(IsoPlayer, byte) @0-@11 L3910-3913` is the Lua global; it forwards only when `GameServer.server` is set.
`SyncPlayerFieldsPacket.write @0-@51 L139-148` walks bits 0..5 of a byte mask and calls `writeParam(1 << i, writer)`.
`SyncPlayerFieldsPacket.writeParam @1 L52` is a `lookupswitch` with `default -> 267` and six pairs: `1 -> 60` known recipes, `2 -> 127` `CharacterTraits.write`, `4 -> 146` already-read books, `8 -> 209` `BodyDamage.saveMainFields`, `16 -> 229` `isReading`, `32 -> 247` `Fitness.save`.
`SyncPlayerFieldsPacket.parseParam` mirrors it; case 2 calls `CharacterTraits.read` on the receiving player (`@127-@143 L104-107`).

So mask 8 pushes the body-damage main fields on demand, and **mask 2 does carry the character trait list to a client and apply it there** — worth re-checking against the register rows that say no packet was traced carrying traits.

| carrier | payload | cite |
|---|---|---|
| `PlayerStatsPacket` | player id, all 24 stats, `Nutrition.save`, time-since-smoke, `BodyDamage.saveMainFields` | `BodyDamage.saveMainFields @0-@116 L311-322`; `Stats.save @0-@39 L55-58` |
| `SyncPlayerStatsPacket` | player id, int mask; `-1` means the whole `Nutrition` object | `SyncPlayerStatsPacket.write @16-@91 L69-78` |
| `SyncPlayerFieldsPacket` | byte mask over six blocks, bit 8 = `saveMainFields`, bit 2 = traits | `SyncPlayerFieldsPacket.writeParam @1 L52` (switch decoded) |
| `BodyPartSyncPacket` | player id, part index byte, 64-bit field mask, then the selected per-part fields | `BodyPartSyncPacket.write @0-@65 L98-107` |

## B — `BodyPart`: bleeding, bandages, wound healing, fracture, infection, stiffness

`BodyPart` is in the exposer class set (`exposeAll` @571), as is `BodyPartType` (@565).

### B.1 The side gate

`BodyPart.DamageUpdate @0-@30 L154-155` returns immediately when `GameClient.client` is set and the parent is the local `IsoPlayer`. Every wound timer, every poultice countdown and every `CombatManager.applyDamage` call below it is therefore server-only in multiplayer. `BodyDamage.Update @2130-@2159 L2475-2476` is the only caller inside the tick, once per part.

### B.2 Wound damage per tick

`CombatManager.getInstance().applyDamage(part, x)` is called with `x = constant * damageScaler * GameTime.getMultiplier()`:

| wound | constant, unbandaged | constant, bandaged | cite |
|---|---|---|---|
| deep wound (and not stitched) | 3.125 | 1.5625 | `BodyPart.DamageUpdate @47-@89 L159-163` |
| scratch (skipped if bandaged) | 0.9375 | — | `BodyPart.DamageUpdate @108-@126 L167` |
| cut (skipped if bandaged) | 1.875 | — | `BodyPart.DamageUpdate @145-@163 L171` |
| bite (skipped if bandaged) | 2.1875 | — | `BodyPart.DamageUpdate @182-@200 L175` |
| bleeding (skipped if bandaged) | 0.2857143 × `bleedingTime / 10` | — | `BodyPart.DamageUpdate @219-@239 L181` |

`damageScaler` is `private` with no setter: `setDamageScaler` is absent from every class entry in the jar, and the field is written only in `BodyPart.<init>` (@19, @92, @98) and read in `DamageUpdate` (@50, @72, @115, @152, @189, @222, @310, @332, @375, @412), `getDamageScaler` (@1) and `getBandageNeededDamageLevel` (@181). It is a per-part constant and a wall.

### B.3 Wound healing — the timers and the factors

Healing in this model is the wound timer counting down; when it reaches 0 the wound stops doing damage. Every timer and every factor has a public setter, which is where a mod can change a healing rate.

`BodyPart.DamageUpdate @1424-@1601 L373-…`: a bandaged scratch loses `1.5e-4 * multiplier` per tick from `scratchTime` and `8e-5 * multiplier` from `bandageLife`; with `getPlantainFactor() > 0` it loses a further `1e-4 * multiplier` and the plantain factor itself decays by `8e-4 * multiplier`.
`@2169-@2311 L479-495`: with `getSplintFactor() > 0`, `fractureTime` loses `5e-5 * multiplier * splintFactor`, otherwise `5e-6 * multiplier`; `getComfreyFactor() > 0` adds another `5e-6 * multiplier` while the comfrey factor decays by `5e-4 * multiplier`; when `fractureTime` goes negative it is clamped to 0, `setGetSplintXp(true)` fires and `resetPoulticeFactors()` runs.
`@2151-@2168 L473-474`: `stitchTime` is capped at 50.
`@2321-@2337 L501`: `additionalPain` decays by `0.005 * multiplier`.
Equivalent blocks exist for `cutTime` (@1818-@1888 L…), `deepWoundTime` (@1909-@1995), `bleedingTime` (@1594, @1765), `burnTime` (@542, @587), `biteTime` (@460, @505), `woundInfectionLevel` (@1069, @1116, @1191, @1242, @1271, @1293, @1309, @1400, @2534) and `stiffness` (@2417, @2431); `getGarlicFactor` scales the wound-infection arms (@1167, @1196).

| member | signature | flags | exposed? | side | synced-by (bit value) | cite |
|---|---|---|---|---|---|---|
| `getHealth` / `SetHealth` / `AddHealth` / `ReduceHealth` | `()F` / `(F)V` ×3 | all public | yes | server | `syncWrite` case 1 → mask **1** | `BodyDamage.ReduceGeneralHealth @64 L1131`; `BodyPart.syncWrite @432 L1586` |
| `bleeding` / `setBleeding` | `()Z` / `(Z)V` | public / public | yes | server | case 4 → mask **8** | `BodyPart.syncWrite @271 L1572` |
| `getBleedingTime` / `set…` | `()F` / `(F)V` | public / public | yes | server | case 18 → mask **131072** | `BodyPart.DamageUpdate @219-@239 L181`; `syncWrite @283 L1573` |
| `IsBleedingStemmed` / `SetBleedingStemmed` | `()Z` / `(Z)V` | public / public | yes | server | case 5 → mask **16** | `BodyPart.syncWrite @455 L1588` |
| `generateBleeding` | `()V` | public | yes | server | — | flags read; body not dumped |
| `bandaged` / `setBandaged(ZF)` / `setBandaged(ZFZString)` | `()Z` / `(ZF)V` / `(ZFZLjava/lang/String;)V` | all public | yes | server | case 2 → mask **2** | `BodyPart.syncWrite @214 L1567` |
| `getBandageLife` / `set…` | `()F` / `(F)V` | public / public | yes | server | case 12 → mask **2048** | `BodyPart.DamageUpdate @1461-@1479 L376`; `syncWrite @226 L1568` |
| `getBandageType` / `set…` | `()Ljava/lang/String;` / `(…)V` | public / public | yes | server | case 24 → mask **8388608** | `BodyPart.syncWrite @237 L1569` |
| `isBandageDirty` | `()Z` | public | yes | unread | — | flags only |
| `getScratchTime` / `set…` | `()F` / `(F)V` | public / public | yes | server | case 13 → mask **4096** | `BodyPart.DamageUpdate @1440-@1458 L375`; `syncWrite @561 L1597` |
| `getCutTime` / `set…` | `()F` / `(F)V` | public / public | yes | server | case 40 → mask **2^39** | `BodyPart.DamageUpdate @1635`, `@1686`, `@1731`, `@1745` (the cut block, lines not transcribed); `syncWrite @339 L1578` |
| `getDeepWoundTime` / `set…` | `()F` / `(F)V` | public / public | yes | server | case 19 → mask **262144** | `BodyPart.DamageUpdate @31-@37 L158`; `syncWrite @328 L1577` |
| `getBurnTime` / `set…`, `setBurned`, `isBurnt`, `isNeedBurnWash` / `set…`, `getLastTimeBurnWash` / `set…` | see flags | all public | yes | server | cases 32, 33, 34 → masks **2^31**, **2^32**, **2^33** | `BodyPart.syncWrite @294 L1574`, `@514 L1593`, `@503 L1592` |
| `getBiteTime` / `set…`, `bitten` / `SetBitten` | `()F` / `(F)V`, `()Z` / `(Z)V` | all public | yes | server | cases 14, 3 → masks **8192**, **4** | `BodyPart.DamageUpdate @166-@200 L174-175`; `syncWrite @248 L1570`, `@259 L1571` |
| `getStitchTime` / `set…`, `stitched` / `setStitched` | `()F` / `(F)V`, `()Z` / `(Z)V` | all public | yes | server | cases 21, 8 → masks **2^20**, **128** | `BodyPart.DamageUpdate @2151-@2166 L473-474`; `syncWrite @618 L1602`, `@606 L1601` |
| `getFractureTime` / `setFractureTime` | `()F` / `(F)V` | public / public | yes | server | case 28 → mask **2^27** | `BodyPart.DamageUpdate @2169-@2235 L479-484`; `syncWrite @350 L1579` |
| `generateFracture(F)` / `generateFractureNew(F)` | `(F)V` | public / public | yes | server | — | flags read; bodies not dumped |
| `isSplint` / `setSplint(ZF)`, `getSplintFactor` / `set…`, `getSplintItem` / `set…`, `isGetSplintXp` / `set…` | see flags | all public | yes | server | cases 29, 30, 35, 27 → masks **2^28**, **2^29**, **2^34**, **2^26** | `BodyPart.DamageUpdate @2178-@2211 L481-482`; `syncWrite @572 L1598`, `@584 L1599`, `@595 L1600`, `@384 L1582` |
| `fractureDamage` (field) | `F` | **private final** | n/a — wall | — | not in the sync list | flags read |
| `isDeepWounded` / `setDeepWounded`, `deepWounded`, `generateDeepWound`, `generateDeepShardWound` | see flags | all public | yes | server | case 9 → mask **256** | `BodyPart.syncWrite @316 L1576` |
| `IsInfected` / `SetInfected` | `()Z` / `(Z)V` | public / public | yes | server | case 10 → mask **512** | `BodyPart.syncWrite @491 L1591` |
| `isInfectedWound` / `setInfectedWound` | `()Z` / `(Z)V` | public / public | yes | server | case 17 → mask **65536** | `BodyPart.DamageUpdate @1010 L…`, `@2070`, `@2132`; `syncWrite @443 L1587` |
| `getWoundInfectionLevel` / `set…` | `()F` / `(F)V` | public / public | yes | server | case 16 → mask **32768** | `BodyPart.DamageUpdate @1069-@1400 L…`; `syncWrite @629 L1603` |
| `IsFakeInfected` / `SetFakeInfected`, `DisableFakeInfection` | see flags | all public | yes | server | case 11 → mask **1024** | `BodyPart.syncWrite @479 L1590`; `BodyDamage.Update @2389-@2401 L2513` |
| `generateZombieInfection(I)` | `(I)V` | public | yes | server | — | flags read; body not dumped |
| `getStiffness` / `setStiffness`, `addStiffness(F)` | `()F` / `(F)V` / `(F)V` | all public | yes | server | case 41 → mask **2^40** | `BodyPart.DamageUpdate @2417 L…`, `@2431`; `syncWrite @640 L1604` |
| `BodyDamage.addStiffness(BodyPart,F)` / `(BodyPartType,F)`, `IsoGameCharacter.addStiffness(BodyPartType,F)` | `(…;F)V` | all public | yes | server | via the part's `stiffness` bit | flags read |
| `getPlantainFactor` / `set…`, `getComfreyFactor` / `set…`, `getGarlicFactor` / `set…`, `getAlcoholLevel` / `set…`, `resetPoulticeFactors` | see flags | all public | yes | server | cases 36, 37, 38, 22 → masks **2^35**, **2^36**, **2^37**, **2^21** | `BodyPart.DamageUpdate @1483-@1529 L378-380`, `@2238-@2286 L487-489`; `syncWrite @526 L1594`, `@305 L1575`, `@361 L1580`, `@203 L1566` |
| `getAdditionalPain` / `setAdditionalPain` / `getAdditionalPain(Z)` | `()F` / `(F)V` / `(Z)F` | all public | yes | server | case 23 → mask **2^22** | `BodyPart.DamageUpdate @2313-@2337 L500-501`; `syncWrite @180 L1564` |
| `getPain` | `()F` | public | yes | server | not in the sync list | `BodyDamage.Update @1763 L2428` |
| `getScratchSpeedModifier` / `set…`, `getCutSpeedModifier` / `set…`, `getBurnSpeedModifier` / `set…`, `getDeepWoundSpeedModifier` / `set…` | `()F` / `(F)V` ×4 | all public | yes | read on the side that moves the character | **not** in the sync list | set only in `BodyPart.<init>` (@132…@309) and by their own setters; read **only** by `IsoGameCharacter.calculateInjurySpeed @1,@6,@12,@18 L9946-9949` |
| `getInnerTemperature`, `getSkinTemperature`, `getDistToCore`, `getSkinSurface`, `getThermalNode` | getters | public | yes | server | no | flags read |
| `getWetness` / `setWetness` | `()F` / `(F)V` | public / public | yes | server | **not** in the sync list | flags read |
| `getIndex`, `getType` | `()I`, `()…BodyPartType;` | public | yes | both | part index is in the packet header | `BodyPartSyncPacket.write @13 L99` |

**Note on the four `*SpeedModifier` fields**: they are *not* healing rates. Their only reader in the jar is `IsoGameCharacter.calculateInjurySpeed`, which is a movement/combat speed term. A mod that wants a nutrition deficiency to make an injury more crippling can set them; a mod that wants slower healing must slow a timer or a poultice factor instead.

### B.4 How a client learns of a per-part change

Two mechanisms exist and they are different.

`BodyPartSyncPacket.write @0-@65 L98-107`: player id, the part index as a byte, `syncParams` as a **long**, then a loop `for i in 0..41` that calls `BodyPart.syncWrite(writer, i+1)` for each set bit.
`BodyPartSyncPacket.parse @0-@89 L82-94` resolves the part by index out of `getBodyDamage().getBodyParts()` on the addressed player and calls `BodyPart.sync(reader, (byte)(i+1))` per set bit.
`BodyPart.syncWrite @1 L1563` is a `tableswitch` `low=1 high=41 default=648` — 41 fields over 42 bit positions, one position with no case. The case-to-field map is the "synced-by" column above; the bit value for case *n* is `2^(n-1)`, so **case 1 (`health`) is mask `1`**.
`LuaManager$GlobalObject.syncBodyPart(BodyPart, long) @0-@50 L9802-9805` is the Lua-facing sender: it runs only when `GameServer.server` is set, resolves the part's parent to an `IsoPlayer` and sends `PacketType.BodyPartSync` with `{part, mask}`. This is the route a mod uses to make a server-side per-part write visible on a client.

The engine's own remote-player path is separate. `BodyPart.sync(BodyPart, BodyDamageSync$Updater) @0-@… L1373-…` diffs each field against a "last sent" copy and calls `BodyDamageSync$Updater.updateField(index, value)` with the same index numbering (1 `health`, 2 `bandaged`, 3 `bitten`, 4 `bleeding`, 5 `isBleedingStemmed`, …), writing the new value into the sent copy.
`BodyDamageSync.update @0-@42 L254-262` returns unless `GameServer.server` is set and then ticks every registered `Updater`.
`BodyDamageSync.startSendingUpdates(SS) @0-@6 L187-188` has the same server gate; it is keyed on a `(localId, remoteId)` pair and calls `RestoreToFullHealth` plus `setBodyPartsLastState` on the sent copy when the pair already exists.
`BodyDamageSync$Updater.update @0-@17 L85-87` rate-limits itself to one send per 500 ms, and compares overall health (truncated to an int), the `PAIN` moodle level against `getRemotePainLevel`, `ZOMBIE_INFECTION` and `isFakeInfected` before sending.
`BodyDamageUpdatePacket.write @0-@51 L68-75` carries a type enum, a current-player id, a remote-player id and, for `Type.UPDATE`, a raw `ByteBuffer`.

The honest reading is that `BodyDamageSync` is the *one player looking at another player's injuries* channel, throttled to 2 Hz, and `syncBodyPart` is the general-purpose one. Who calls `BodyDamageSync.update()` (the grep names `IngameState` and `IsoWorld`) and what triggers `startSendingUpdates` were not read.

## C — `Stats`: the mood surface

`Stats` (`exposeAll` @685) and `CharacterStat` (@691) are both exposed. `Stats` is `public synchronized`; every method a mod needs is public.

`Stats.<init> @0-@25 L14-22` creates an empty `HashMap`; `Stats.get @0-@23 L77` returns `stats.getOrDefault(stat, stat.getDefaultValue())`, so an unset stat reads its default rather than 0.
`Stats.set @0-@41 L81-84` clamps through `CharacterStat.clamp` before storing and returns whether the value changed.
`CharacterStat.register(String,F,F,F,F)` is `public static`, so a mod *can* register a new stat — but `ORDERED_STATS` is a `public static final` array built once in `<clinit> @290-@457 L36`, and `Stats.save` iterates it, so a stat registered later is usable through `get`/`set` and is neither saved nor synced.

### C.1 The 24 registered stats

All from `CharacterStat.<clinit>`, `register(id, minimum, maximum, default)`:

| stat | id string | min | max | default | `ORDERED_STATS` index | cite |
|---|---|---|---|---|---|---|
| `ANGER` | `Anger` | 0 | 1 | 0 | 0 | `<clinit> @10-@18 L12` |
| `BOREDOM` | `Boredom` | 0 | 100 | 0 | 1 | `<clinit> @21-@30 L13` |
| `DISCOMFORT` | `Discomfort` | 0 | 100 | 0 | 2 | `<clinit> @33-@42 L14` |
| `ENDURANCE` | `Endurance` | 0 | 1 | 1 | 3 | `<clinit> @45-@53 L15` |
| `FATIGUE` | `Fatigue` | 0 | 1 | 0 | 4 | `<clinit> @56-@64 L16` |
| `FITNESS` | `Fitness` | −1 | 1 | 0 | 5 | `<clinit> @67-@76 L17` |
| `FOOD_SICKNESS` | `FoodSickness` | 0 | 100 | 0 | 6 | `<clinit> @79-@88 L18` |
| `HUNGER` | `Hunger` | 0 | 1 | 0 | 7 | `<clinit> @91-@99 L19` |
| `IDLENESS` | `Idleness` | 0 | 1 | 0 | 8 | `<clinit> @102-@110 L20` |
| `INTOXICATION` | `Intoxication` | 0 | 100 | 0 | 9 | `<clinit> @113-@122 L21` |
| `MORALE` | `Morale` | 0 | 1 | 1 | 10 | `<clinit> @125-@133 L22` |
| `NICOTINE_WITHDRAWAL` | `NicotineWithdrawal` | 0 | 0.51 | 0 | 11 | `<clinit> @136-@145 L23` |
| `PAIN` | `Pain` | 0 | 100 | 0 | 12 | `<clinit> @148-@157 L24` |
| `PANIC` | `Panic` | 0 | 100 | 0 | 13 | `<clinit> @160-@169 L25` |
| `POISON` | `Poison` | 0 | 100 | 0 | 14 | `<clinit> @172-@181 L26` |
| `SANITY` | `Sanity` | 0 | 1 | 1 | 15 | `<clinit> @184-@192 L27` |
| `SICKNESS` | `Sickness` | 0 | 1 | 0 | 16 | `<clinit> @195-@203 L28` |
| `STRESS` | `Stress` | 0 | 1 | 0 | 17 | `<clinit> @206-@214 L29` |
| `TEMPERATURE` | `Temperature` | 20 | 40 | 37 | 18 | `<clinit> @217-@228 L30` |
| `THIRST` | `Thirst` | 0 | 1 | 0 | 19 | `<clinit> @231-@239 L31` |
| `UNHAPPINESS` | `Unhappiness` | 0 | 100 | 0 | 20 | `<clinit> @242-@251 L32` |
| `WETNESS` | `Wetness` | 0 | 100 | 0 | 21 | `<clinit> @254-@263 L33` |
| `ZOMBIE_FEVER` | `ZombieFever` | 0 | 100 | 0 | 22 | `<clinit> @266-@275 L34` |
| `ZOMBIE_INFECTION` | `ZombieInfection` | 0 | 100 | 0 | 23 | `<clinit> @278-@287 L35` |

There is no `DRUNKENNESS` and no `FEAR` (§ F); drunkenness is `INTOXICATION` and fear is `PANIC`.

### C.2 The moodle thresholds behind those stats

`MoodleStat.<clinit>` registers 20 moodle stats as `register(type, minimumThreshold, lowestThreshold, moderateThreshold, highestThreshold, maximumThreshold)`; the last four are moodle levels 1 through 4.

| moodle | min | L1 | L2 | L3 | L4 | cite |
|---|---|---|---|---|---|---|
| `ENDURANCE` | 0.75 | 0.5 | 0.25 | 0.10 | 0.0 | `MoodleStat.<clinit> @10-@25 L10` |
| `ANGRY` | 0 | 0.10 | 0.25 | 0.5 | 0.75 | `@28-@43 L11` |
| `TIRED` | 0 | 0.60 | 0.70 | 0.80 | 0.90 | `@46-@61 L12` |
| `HUNGRY` | 0 | 0.15 | 0.25 | 0.45 | 0.70 | `@64-@79 L13` |
| `PANIC` | 0 | 6.0 | 30.0 | 65.0 | 80.0 | `@82-@97 L14` |
| `SICK` | 0 | 0.25 | 0.50 | 0.75 | 0.90 | `@100-@115 L15` |
| `BORED` | 0 | 25.0 | 50.0 | 75.0 | 90.0 | `@118-@133 L16` |
| `UNHAPPY` | 0 | 20.0 | 45.0 | 60.0 | 80.0 | `@136-@151 L17` |
| `STRESS` | 0 | 0.25 | 0.50 | 0.75 | 0.90 | `@154-@169 L18` |
| `THIRST` | 0 | 0.12 | 0.25 | 0.70 | 0.84 | `@172-@187 L19` |
| `PAIN` | 0 | 10.0 | 20.0 | 50.0 | 75.0 | `@190-@205 L20` |
| `WET` | 0 | 15.0 | 40.0 | 70.0 | 90.0 | `@208-@223 L21` |
| `HAS_A_COLD` | 0 | 20.0 | 40.0 | 60.0 | 75.0 | `@226-@241 L22` |
| `INJURED` | 0 | 20.0 | 40.0 | 60.0 | 75.0 | `@244-@259 L23` |
| `DRUNK` | 0 | 10.0 | 30.0 | 50.0 | 70.0 | `@262-@277 L24` |
| `UNCOMFORTABLE` | 0 | 20.0 | 40.0 | 60.0 | 80.0 | `@280-@295 L25` |
| `NOXIOUS_SMELL` | 0 | 0.001 | 0.001 | 0.002 | 0.002 | `@298-@313 L26` |
| `HYPOTHERMIA` | 0 | 30.0 | 70.0 | 9.0 | 100.0 | `@316-@331 L27` |
| `WINDCHILL` | 0 | 5.0 | 10.0 | 15.0 | 20.0 | `@334-@349 L28` |
| `HEAVY_LOAD` | 0 | 1.0 | 1.25 | 1.5 | 1.75 | `@352-@366 L29` |

The `HYPOTHERMIA` row is quoted as read: level 3 is `9.0`, below both level 2 and level 1, which looks like an authoring mistake in the engine. It was not investigated further.

`MoodleStat` carries public threshold setters (`setMinimumThreshold`, `setLowestThreshold`, `setModerateThreshold`, `setHighestThreshold`, `setMaximumThreshold`), but `MoodleStat` **does not appear anywhere** in the 3055-line `LuaManager$Exposer.exposeAll()` dump (grep count 0 over the whole dump), so it is unreachable from Lua and the thresholds are a wall. This matches the existing register row.

`Moodles.Update @0-@49 L60-65` iterates the moodle map and calls `Moodle.Update` on each, with no side gate — so both sides recompute their own moodles from their own stats.

### C.3 Who owns the mood stats

`IsoPlayer.calculateStats @0-@10 L3280-3283`: when `GameClient.client` is set the method returns **without** calling `IsoLivingCharacter.calculateStats`. That is the single gate that makes every mood stat server-owned for players in multiplayer.

`IsoGameCharacter.calculateStats @0-@88 L10196-10221`: returns for an animal; on a server, resets `FATIGUE` unless both `ServerOptions.sleepAllowed` and `sleepNeeded` are set; then calls `LuaHookManager.TriggerHook("CalculateStats", this)` and **returns if the hook returns true**; then calls, in order, `updateEndurance`, `updateTripping`, `updateThirst`, `updateStress`, `updateStats_WakeState`, `updateMorale`, `updateFitness`.

`IsoGameCharacter.updateStats_WakeState @0-@45 L10224-10234`: returns for an animal; proceeds when `GameServer.server` is set, or when `GameClient.client` is clear **and** `this == IsoPlayer.getInstance()`; then branches on `asleep` into `updateStats_Sleeping` or `updateStats_Awake`.

`IsoGameCharacter.updateStress @0-@… L10333-…`: no side gate of its own — it relies on `IsoPlayer.calculateStats`. It adds `WorldSoundManager.getStressFromSounds(...) * ZomboidGlobals.stressFromSoundsMultiplier` unless the character has the `DEAF` trait (`@8-@61 L10337-10338`), then `ZomboidGlobals.stressFromBiteOrScratch * multiplier * deltaMinutesPerDay` per bitten part (`@62-@102 L10341-10342`) and again per scratched part (`@103-@144 L10345-10346`).

`IsoGameCharacter.updateStats_Awake @0-@30 L10242`: removes `ZomboidGlobals.stressReduction * multiplier * deltaMinutesPerDay` from `STRESS` as its first act.

| member | signature | flags | exposed? | side | synced-by | cite |
|---|---|---|---|---|---|---|
| `Stats.get(CharacterStat)` | `(…)F` | public | yes | both read | — | `Stats.get @0-@23 L77` |
| `Stats.set(CharacterStat,F)` | `(…F)Z` | public | yes | server writes stick; client writes are overwritten | all 24 in `PlayerStatsPacket` | `Stats.set @0-@41 L81-84` |
| `Stats.add` / `remove` / `reset` / `isAtMinimum` / `isAtMaximum` / `isAboveMinimum` / `resetStats` | see flags | all public | yes | server | — | flags read |
| `Stats.save(ByteBuffer)` / `load` / `write(bb,byte)` / `parse(bb,byte)` | see flags | all public | yes | server sends | — | `Stats.save @0-@39 L55-58`; `Stats.write @0-@48 L69-74` |
| `Stats.getNicotineStress` | `()F` | public | yes | unread | — | flags only |
| `CharacterStat.register` | `(Ljava/lang/String;FFF)…` | **public static** | yes | either | a new stat is **not** in `ORDERED_STATS`, so never saved or synced | `CharacterStat.<clinit> @290-@457 L36` builds the array once |
| `CharacterStat.clamp` / `getMinimumValue` / `getMaximumValue` / `getDefaultValue` / `getById` | see flags | all public | yes | — | — | flags read |
| `IsoPlayer.calculateStats` | `()V` | public | yes | **server only** | — | `IsoPlayer.calculateStats @0-@10 L3280-3283` |
| `IsoGameCharacter.calculateStats` | `()V` | (called via super) | yes | server | — | `IsoGameCharacter.calculateStats @49-@59 L10204-10205` (the `CalculateStats` hook) |
| `IsoGameCharacter.updateStats_Awake` | `()V` | protected | reachable only via the chain | server | — | `updateStats_Awake @0-@30 L10242` |
| `IsoGameCharacter.updateStress` | `()V` | **private** | n/a — wall | server | — | `updateStress @0-@144 L10333-10346` |
| `IsoGameCharacter.updateThirst` | `()V` | **private** | n/a — wall | server | — | flags read |
| `BodyDamage.UpdateBoredom` / `UpdatePanicState` / `UpdateDiscomfort` / `UpdateIllness` / `UpdateStrength` | `()V` | all public | yes | server (via `BodyDamage.Update`) | — | `BodyDamage.Update @238 L2205`, `@246 L2207`, `@254 L2209`, `@258 L2210`, `@242 L2206`; bodies **not dumped** |
| `BodyDamage.IncreasePanic(I)` / `IncreasePanicFloat(F)` / `ReducePanic()` | see flags | all public | yes | server | `PANIC` rides the stats block | flags read; bodies not dumped |
| `BodyDamage.getPanicIncreaseValue` / `set…`, `getPanicReductionValue` / `set…`, `getDrunkIncreaseValue` / `set…`, `getDrunkReductionValue` / `set…` | `()F` / `(F)V` | all public | yes | server | no | flags read |
| `BodyDamage.getBoredomDecreaseFromReading` / `set…` | `()F` / `(F)V` | public / public | yes | server | no | flags read |
| `LuaHookManager.TriggerHook("CalculateStats", chr)` | Lua script hook | — | yes | wherever `calculateStats` runs (server in MP) | — | `IsoGameCharacter.calculateStats @49-@59 L10204-10205` |

## D — `Thermoregulator`: what a mod can write

`Thermoregulator` (`exposeAll` @583) and `Thermoregulator$ThermalNode` (@589) and `Metabolics` (@595) are all exposed. The formulas belong to the other agent; this is the writability audit only.

`Thermoregulator` declares exactly three non-private mutators: `setSimulationMultiplier(F)` which is `public static` (a global simulation-speed knob, not per-character), and the two overloads `setMetabolicTarget(Metabolics)` and `setMetabolicTarget(F)`, both `public`. `updateThermalDamage(F)` is `private`, and so are `updateSetPoint`, `updateMetabolicRate`, `updateNodesHeatDelta`, `updateHeatDeltas`, `updateNodes`, `updateBodyMultipliers`, `updateClothing`, `updateCoreRateOfChange` and the `getSimulationMultiplier(Multiplier)` overload. Everything else on the class is a getter.

`Thermoregulator$ThermalNode` is `public` and has **no setters at all** — 19 fields, 7 of them `private final`, and 28 methods every one of which is a getter or a predicate. `insulation`, `windresist`, `celcius`, `skinCelcius`, `clothingWetness`, `bodyWetness` are all `private` with no writer. `calculateInsulation()` is `private`.

`setInsulation` exists in the jar only on `zombie/inventory/types/Clothing` and `zombie/scripting/objects/Item` — the clothing script side, not the character side. `setColdResistance`, `setHeatResistance`, `setInsulationFactor` and `getInsulationFactor` are absent from every class entry.

The one writable thermal door is the stat. `Thermoregulator.updateHeatDeltas @130-@216 L980-985`: the core node's `celcius` is clamped to `[20, 42]`; then the method reads `CharacterStat.TEMPERATURE`, and if `abs(stat - core.celcius) > 0.001` it sets `core.celcius = PZMath.lerp(core.celcius, stat, 0.5)`; then it writes `core.celcius` back into the stat. So a server-side `getStats():set(CharacterStat.TEMPERATURE, x)` moves the core node halfway to `x` on the next tick, and the stat is then re-driven from the core.

`Thermoregulator.update()` is public but is called from `BodyDamage.Update @218-@222 L2198-2199`, which is server-only in multiplayer.

| member | signature | flags | exposed? | side | synced-by | cite |
|---|---|---|---|---|---|---|
| `Thermoregulator.setSimulationMultiplier` | `(F)V` | **public static** | yes | process-global, not per character | — | flags read |
| `Thermoregulator.setMetabolicTarget` | `(Lzombie/…/Metabolics;)V` and `(F)V` | public / public | yes | server | — | flags read; read back at `BodyDamage.Update @1420 L2386` |
| `Thermoregulator.updateThermalDamage` | `(F)V` | **private** | n/a — wall | — | — | flags read |
| `Thermoregulator.getThermalDamage` / `getCoreTemperature` / `getCoreCelcius` / `getSetPoint` / `getHeatGeneration` / `getMetabolicRate` / `getCatchAColdDelta` / `getMovementModifier` / `getCombatModifier` / `getTimedActionTimeModifier` / `getFluidsMultiplier` / `getEnergyMultiplier` / `getFatigueMultiplier` … | getters | public | yes | server-computed, client reads its own | — | flags read |
| `Thermoregulator.update` | `()V` | public | yes | server only in MP | — | `BodyDamage.Update @218-@222 L2198-2199` |
| `Thermoregulator$ThermalNode.*` | 28 getters, 0 setters | public class, all fields private or private final | yes | read-only | — | full flag listing read; `calculateInsulation` private |
| `CharacterStat.TEMPERATURE` | via `Stats.set` | public static final | yes | server writes; both sides receive it in the stats block | `PlayerStatsPacket`, index 18 | `Thermoregulator.updateHeatDeltas @149-@216 L981-985` |
| `BodyDamage.getThermoregulator` | `()Lzombie/…/Thermoregulator;` | public | yes | both | — | flags read |
| character-level insulation setter | — | — | — | — | — | **absent**: jar-wide grep `setInsulation` hits only `Clothing` and `Item`; `setInsulationFactor`, `setColdResistance`, `setHeatResistance` hit nothing |

## E — Death and knock-out

`IsoGameCharacter.isDead @0-@33 L4946`: returns true when `health <= 0` **or** (`getBodyDamage() != null` and `getBodyDamage().getHealth() <= 0`). `BodyDamage.getHealth @0-@4 L1724` is `getOverallBodyHealth()`.

`IsoGameCharacter.updateInternal @96-@134 L9023-9027`: when `isDead()` and the character is not in its square's moving-object list, it calls `die()` — but only when `GameServer.server` is set (`@124-@131 L9024-9025`), then returns.

The engine's own fatal move is `ReduceGeneralHealth(110.0f)` — the constant appears twice on the zombie-infection path, at `BodyDamage.Update @1902-@1906 L2448` (mortality option 1) and `@2030-@2034 L2460` (the mortality clock reaching 1). A deficiency effect that wants to kill should use the same call rather than `setOverallBodyHealth(0)`, which is a raw field write that `calculateOverallHealth` overwrites in the same tick.

Note also `BodyDamage.ReduceGeneralHealth @0-@18 L1122-1123`: any reduction taken while overall health is at or below 10 calls `parentChar.forceAwake()` first. So a drain that crosses 10 wakes a sleeping player for free.

`BodyDamage.Update @261-@270 L2212-2213` returns early at *exactly* zero health, so a body parked at 0.0 stops simulating; `ReduceGeneralHealth(110)` overshoots into the negative and does not hit that stop.

There is no fainting or unconscious state on this build: `Unconscious`, `setUnconscious`, `Fainted` and `setFainted` are each absent from every class entry in the jar. What exists is three flags, all bare field writes:

| member | signature | flags | exposed? | side | synced-by | cite |
|---|---|---|---|---|---|---|
| `IsoGameCharacter.die` | `()V` | **public final** | yes (`exposeAll` @716) | server (the engine calls it under a `GameServer.server` gate) | — | `IsoGameCharacter.updateInternal @124-@131 L9024-9025` |
| `IsoGameCharacter.Kill(…)` ×4 | see flags | all public final | yes | unread | — | flags read; bodies not dumped |
| `IsoGameCharacter.dieNetwork(…)` | `(…)Lzombie/iso/objects/IsoDeadBody;` | public final | yes | unread | — | flags read |
| `IsoGameCharacter.addOnDiedListener` | `(Lzombie/characters/CharacterDiedListener;Z)V` | public | yes | unread | — | flags read |
| `IsoGameCharacter.isDead` | `()Z` | public | yes | both | — | `isDead @0-@33 L4946` |
| `IsoGameCharacter.getHealth` / `setHealth` | `()F` / `(F)V` | public / public | yes | unsettled — the `health` field is in neither `PlayerStatsPacket` nor `saveMainFields` | **not read** | `getHealth @0-@4 L3123`; `setHealth @0-@19 L3128-3132` — refuses only the exact value 0 when `isInvulnerable()`, otherwise a raw unclamped `putfield` |
| `BodyDamage.ReduceGeneralHealth(110.0f)` | `(F)V` | public | yes | server | via per-part `health` | `BodyDamage.Update @1902-@1906 L2448`, `@2030-@2034 L2460` |
| `IsoGameCharacter.setAsleep` | `(Z)V` | public | yes | server (the sleep updaters are server-gated) | not read | `setAsleep @0-@5 L2989-2990` — bare `putfield` |
| `IsoGameCharacter.isAsleep` | `()Z` | public | yes | both read | — | `BodyDamage.Update @743 L2296`, `@843 L2316` |
| `IsoGameCharacter.forceAwake` | `()V` | public | yes | server | not read | `forceAwake @0-@12 L3032-3035` — sets `forceWakeUp = true` only when already asleep |
| `IsoGameCharacter.setForceWakeUp` | — | present in `IsoGameCharacter`, `ILuaGameCharacter`, `SleepingEvent`, `ModalDialog` | in the `ILuaGameCharacter` interface | unread | — | jar-wide grep only; body **not dumped** |
| `IsoGameCharacter.setKnockedDown` / `isKnockedDown` | `(Z)V` / `()Z` | public / public | yes | not read | not read | `setKnockedDown @0-@5 L15746-15747` — bare `putfield`, no animation or state change |
| `IsoGameCharacter.setBumpDone` / `isBumpDone`, `setBumpFall`, `setBumpStaggered`, `setBumpType`, `setBumpFallType`, `setBumpedChr`, `setLastBump` | see flags | all public | yes | not read | not read | flags read; bodies not dumped |
| `IsoGameCharacter.OnAnimEvent_SetKnockedDown` | `(Lzombie/characters/IsoGameCharacter;Z)V` | **private** | n/a — wall | — | — | flags read |
| `IsoGameCharacter.isGodMod` | `()Z` | public | yes | both | — | `BodyDamage.Update @67-@88 L2169-2172` — god mode calls `RestoreToFullHealth` and returns |

The honest limit on knock-down: `setKnockedDown` writes a flag and the only animation-side writer in the class is `private`, so whether setting the flag from Lua produces a visible knock-down was not established from the bytecode and is a run question.

## F — Absences, each proved by a jar-wide grep

The grep is a byte scan over every one of the jar's class entries, so "no class contains that literal" is the absence of the identifier in any form — declaration, call, descriptor or string constant. Every search below returned that answer, and the default `--max 60` cap was never approached (a zero-hit search cannot be truncated).

| searched string | result | what it means for the design |
|---|---|---|
| `FoodSicknessLevel` | no class contains that literal | food sickness is `CharacterStat.FOOD_SICKNESS`, 0…100, index 6 |
| `getInfectionLevel` | no class contains that literal | use `Stats.get(CharacterStat.ZOMBIE_INFECTION)` or `BodyDamage.getApparentInfectionLevel()` |
| `FakeInfectionLevel` | no class contains that literal | the fake infection is the boolean pair `isIsFakeInfected` / `BodyPart.IsFakeInfected` plus `CharacterStat.ZOMBIE_FEVER` |
| `setWoundHealingRate` | no class contains that literal | no per-part healing-rate setter; slow a timer or a poultice factor instead |
| `getWoundHealingRate` | no class contains that literal | as above |
| `setHealthAdditionModifier` | no class contains that literal | the regeneration dials are the four `*HealthAddition` setters on `BodyDamage` |
| `setDamageScaler` | no class contains that literal | `BodyPart.damageScaler` is a constructor-set constant, read-only from Lua |
| `setHealingRate` | no class contains that literal | — |
| `setRegenRate` | no class contains that literal | — |
| `setHealthRegen` | no class contains that literal | — |
| `setBleedingRate` | no class contains that literal | bleeding damage is a fixed constant × `damageScaler`; only `bleedingTime` is writable |
| `setInfectionResistance` | no class contains that literal | the dial is `IsoGameCharacter.setReduceInfectionPower(F)` |
| `getNausea` / `setNausea` | no class contains that literal | nausea is `CharacterStat.SICKNESS` (0…1) and `FOOD_SICKNESS` (0…100) |
| `setSicknessLevel` | no class contains that literal | as above |
| `setFoodSicknessLevel` | no class contains that literal | as above |
| `DRUNKENNESS` | no class contains that literal | the stat is `CharacterStat.INTOXICATION`, 0…100, index 9; the moodle is `DRUNK` |
| `DrunkennessLevel` | no class contains that literal | as above |
| `CharacterStat.FEAR` | no class contains that literal | there is no fear stat; `FEAR` as a bare string hits only `zombie/scripting/objects/Book` and unrelated JNA classes |
| `Unconscious` / `setUnconscious` | no class contains that literal | no unconscious state exists |
| `Fainted` / `setFainted` | no class contains that literal | no fainting state exists |
| `setColdResistance` / `setHeatResistance` | no class contains that literal | no character-level thermal-resistance setter |
| `setInsulationFactor` / `getInsulationFactor` | no class contains that literal | insulation is computed from clothing inside a private method |
| `setTemperature` | only `zombie/inventory/types/Clothing`, `zombie/iso/IsoHeatSource`, `zombie/scripting/objects/Item` | no character temperature setter; use `CharacterStat.TEMPERATURE` |
| `setPoisonLevel` | only `zombie/inventory/types/Food`, `zombie/scripting/objects/Item` | that is item poison, not character poison; use `CharacterStat.POISON` |
| `setInsulation` | only `zombie/inventory/types/Clothing`, `zombie/scripting/objects/Item` | script-side clothing insulation only |
| `MoodleStat` in the exposer dump | 0 occurrences in 3055 lines | moodle thresholds are unreachable from Lua, confirming the existing register row |
| `BodyPartSyncPacket` | `LuaManager$Exposer`, `LuaManager$GlobalObject`, `PacketTypes$PacketType`, the packet itself | the only sender in the jar is the Lua global `syncBodyPart` |

## Claims candidates

Each line is worded as it would go on a page; grade C, bound "C-only" unless stated. Ids are for the controller to assign.

1. `BodyDamage.Update` returns without doing anything on a game client for a live local player, and calls `RestoreToFullHealth` first for a live remote one, so the whole body-damage tick is server-only in multiplayer — `jar:BodyDamage.Update @21-@62 L2159-2165` · C · C-only.
2. `BodyPart.DamageUpdate` carries the same client gate, so every wound timer, poultice countdown and per-part damage call is server-only in multiplayer — `jar:BodyPart.DamageUpdate @0-@30 L154-155` · C · C-only.
3. `IsoPlayer.calculateStats` returns on a game client before calling its super, so all 24 registered stats are computed server-side only for players — `jar:IsoPlayer.calculateStats @0-@10 L3280-3283` · C · C-only.
4. `BodyDamage.Update` returns early when overall body health is exactly zero, skipping regeneration, the moodle drain, poison, pain, infection and the per-part update — `jar:BodyDamage.Update @261-@270 L2212-2213` · C · C-only.
5. The health-regeneration tier maps to its constant through a `tableswitch` with `low=0 high=3` and its default at the asleep block, so tier 0 takes the standard addition, tier 1 the reduced, tier 2 the severely reduced, tier 3 adds zero and asleep takes the sleeping addition instead — `jar:BodyDamage.Update @754 L2301` (switch decoded) · C · C-only; **settles the inference bound on the existing tier row**.
6. The four regeneration constants are the constructor defaults 0.002, 0.0013, 0.0008 and 0.02, and each has a public setter, so a mod can retune the whole regeneration ladder — `jar:BodyDamage.<init> @61-@79 L74-77` · C · C-only.
7. `setHealthReductionFromSevereBadMoodles` is public and its default is 0.0165, and it is the single constant behind all six severe-moodle health-loss terms — `jar:BodyDamage.<init> @91 L79`, `jar:BodyDamage.Update @1152 L2357` · C · C-only.
8. The severe-moodle health loss has six terms, not two: hunger at level 4 costs `red/50`, thirst at level 4 `red/10`, sickness at level 4 and bleeding at level 4 the full `red`, and a heavy load above level 2 `red/((5-level)/10)` under seven further conditions — `jar:BodyDamage.Update @1151-@1511 L2357-2392` · C · C-only.
9. `BodyDamage.Update` fires `LuaEventManager.triggerEvent("OnPlayerGetDamage", chr, tag, amount)` once per nonzero health-loss term, with the tags `POISON`, `HUNGRY`, `SICK`, `BLEEDING`, `THIRST`, `HEAVYLOAD` and `INFECTION` — `jar:BodyDamage.Update @1526-@1666 L2398-2413`, `@1909 L2449` · C · C-only.
10. `IsoGameCharacter.calculateStats` calls `LuaHookManager.TriggerHook("CalculateStats", chr)` and returns when the hook returns true, so a mod can cancel the entire vanilla stat update — `jar:IsoGameCharacter.calculateStats @49-@59 L10204-10205` · C · C-only.
11. `setOverallBodyHealth` is an unclamped raw field write and `calculateOverallHealth` recomputes the field from the body parts at the end of every tick, so a direct write to overall health is erased within a frame — `jar:BodyDamage.setOverallBodyHealth @0-@5 L2735-2736`, `jar:BodyDamage.calculateOverallHealth @26-@69 L2530-2537` · C · C-only.
12. Overall health is `100 - min(100, Σ (100 - partHealth) × getDamageModifyer(i) + getDamageFromPills())` — `jar:BodyDamage.calculateOverallHealth @26-@69 L2530-2537` · C · C-only.
13. `ReduceGeneralHealth` divides its argument by the part count and by each part's damage modifier, and calls `forceAwake` on the parent first whenever overall health is at or below 10 — `jar:BodyDamage.ReduceGeneralHealth @0-@73 L1122-1133` · C · C-only.
14. `AddGeneralHealth` divides its argument only among the parts below 100 health and applies no damage modifier — `jar:BodyDamage.AddGeneralHealth @0-@109 L1101-1119` · C · C-only.
15. The engine's own fatal move is `ReduceGeneralHealth(110.0f)`, used on both lethal arms of the zombie-infection path — `jar:BodyDamage.Update @1902-@1906 L2448`, `@2030-@2034 L2460` · C · C-only.
16. A character is dead when its `health` field or its overall body health is at or below zero, and `updateInternal` then calls `die()` only when `GameServer.server` is set — `jar:IsoGameCharacter.isDead @0-@33 L4946`, `jar:IsoGameCharacter.updateInternal @124-@131 L9024-9025` · C · C-only.
17. `IsoGameCharacter.setHealth` refuses only the exact value zero and only while invulnerable, and is otherwise an unclamped field write — `jar:IsoGameCharacter.setHealth @0-@19 L3128-3132` · C · C-only.
18. There is no unconscious or fainting state in the engine: `Unconscious`, `setUnconscious`, `Fainted` and `setFainted` are each absent from every class entry in the jar — `jar:jar-wide grep Unconscious`, `grep Fainted`, `grep setUnconscious`, `grep setFainted` · C · C-only.
19. `setAsleep`, `forceAwake` and `setKnockedDown` are all bare field writes, `forceAwake` acting only on an already-asleep character and `setKnockedDown` carrying no animation or state change — `jar:IsoGameCharacter.setAsleep @0-@5 L2989-2990`, `jar:IsoGameCharacter.forceAwake @0-@12 L3032-3035`, `jar:IsoGameCharacter.setKnockedDown @0-@5 L15746-15747` · C · C-only.
20. The poison health drain needs both `POISON` above 10 and the `SICK` moodle at level 1 or more, and is `0.0035 × min(POISON/10, 3)` per multiplier unit, so it caps at 0.0105 — `jar:BodyDamage.Update @962-@1024 L2343-2346` · C · C-only.
21. `FOOD_SICKNESS` grows at `getInfectionGrowthRate() × (2 + round(POISON/10))` per multiplier unit whenever `POISON` is above zero — `jar:BodyDamage.Update @1091-@1133 L2354` · C · C-only.
22. The pain stat tracks `Σ partPain × getPainModifyer(i) − getPainReduction()`, rising at one five-hundredth of the gap per tick and snapping down to the target when the target is lower, while `painReduction` itself decays by 0.005 per multiplier unit and is floored at zero — `jar:BodyDamage.Update @1736-@1876 L2426-2441` · C · C-only.
23. There are exactly 24 registered character stats, each with its own minimum, maximum and default, and `Stats.set` clamps every write through `CharacterStat.clamp` — `jar:CharacterStat.<clinit> @10-@287 L12-35`, `jar:Stats.set @0-@41 L81-84` · C · C-only.
24. `Stats.get` returns the stat's registered default rather than zero for a stat never written, because the backing map is consulted with `getOrDefault` — `jar:Stats.get @0-@23 L77` · C · C-only.
25. `CharacterStat.register` is public and static, but `ORDERED_STATS` is built once in the static initialiser and `Stats.save` iterates it, so a stat a mod registers later is usable through `get` and `set` and is never saved or synced — `jar:CharacterStat.<clinit> @290-@457 L36`, `jar:Stats.save @0-@39 L55-58` · C · C-only.
26. `ORDERED_STATS` is alphabetical by constant name with `TEMPERATURE` at index 18 and `ZOMBIE_INFECTION` at index 23, and that index is both the `Stats.write` selector and the `SyncPlayerStatsPacket` bit position — `jar:CharacterStat.<clinit> @290-@457 L36`, `jar:SyncPlayerStatsPacket.getBitMaskForStat @0-@30 L29-34` · C · C-only.
27. Body temperature is a registered stat with minimum 20, maximum 40 and default 37, not a `BodyDamage` field — `jar:CharacterStat.<clinit> @217-@228 L30`; `jar:jar-wide grep setTemperature` finds it only on `Clothing`, `IsoHeatSource` and `Item` · C · C-only.
28. `Thermoregulator.updateHeatDeltas` clamps the core node to 20–42 °C, lerps it halfway toward whatever `CharacterStat.TEMPERATURE` holds when the two differ by more than 0.001, and then writes the core back into the stat — so a write to the stat is the one way into the thermal core from Lua — `jar:Thermoregulator.updateHeatDeltas @130-@216 L980-985` · C · C-only.
29. `Thermoregulator` exposes only two non-private mutators, the static `setSimulationMultiplier` and the two `setMetabolicTarget` overloads, every other `update*` method being private — `jar:Thermoregulator` flag listing · C · C-only.
30. `Thermoregulator$ThermalNode` has no setters at all, so insulation, wind resistance, node temperature and node wetness are read-only from Lua — `jar:Thermoregulator$ThermalNode` flag listing (19 fields, 28 methods, all getters); `jar:jar-wide grep setInsulation` finds it only on `Clothing` and `Item` · C · C-only.
31. `MoodleStat` registers 20 moodle stats as a minimum plus four level thresholds, and the mood moodles are `PANIC` 6/30/65/80, `STRESS` 0.25/0.50/0.75/0.90, `UNHAPPY` 20/45/60/80, `BORED` 25/50/75/90, `PAIN` 10/20/50/75, `SICK` 0.25/0.50/0.75/0.90 and `DRUNK` 10/30/50/70 — `jar:MoodleStat.<clinit> @82-@277 L14-24` · C · C-only.
32. The `HYPOTHERMIA` moodle's third threshold is 9.0, below both its first and second, which makes its level ladder non-monotonic as shipped — `jar:MoodleStat.<clinit> @316-@331 L27` · C · C-only.
33. `BodyPart.damageScaler` is written only in the constructor and has no setter anywhere in the jar, so the per-part wound-damage scale is fixed — `jar:BodyPart.<init> @19,@92,@98`; `jar:jar-wide grep setDamageScaler` · C · C-only.
34. Unbandaged wound damage per tick is `damageScaler × multiplier` times 3.125 for a deep wound, 1.875 for a cut, 2.1875 for a bite, 0.9375 for a scratch and 0.2857143 × bleedingTime/10 for bleeding, and a bandage halves the deep-wound term and suppresses the other four — `jar:BodyPart.DamageUpdate @47-@239 L159-181` · C · C-only.
35. Wound healing is the wound timer counting down, and every timer plus the plantain, comfrey, garlic and splint factors has a public setter, so those are the only healing-rate handles a mod has — `jar:BodyPart.DamageUpdate @1424-@2311 L373-495`, `jar:BodyPart` flag listing · C · C-only.
36. A splinted fracture heals ten times faster: `fractureTime` loses `5e-5 × multiplier × splintFactor` with a splint and `5e-6 × multiplier` without, with comfrey adding a further `5e-6 × multiplier` — `jar:BodyPart.DamageUpdate @2178-@2286 L481-489` · C · C-only.
37. The four `BodyPart.*SpeedModifier` setters are movement and combat speed terms, not healing rates: their only reader in the jar is `IsoGameCharacter.calculateInjurySpeed` — `jar:IsoGameCharacter.calculateInjurySpeed @1-@21 L9946-9949`; `jar:jar-wide grep ScratchSpeedModifier` names only `IsoGameCharacter` and `BodyPart` · C · C-only.
38. `BodyPartSyncPacket` carries one body part as a 64-bit field mask over 41 selectable fields, and `BodyPart.syncWrite`'s case table makes the part's own health mask value 1 — `jar:BodyPartSyncPacket.write @0-@65 L98-107`, `jar:BodyPart.syncWrite @1 L1563` (switch decoded, `low=1 high=41`) · C · C-only.
39. `syncBodyPart(part, mask)` is a Lua global that runs only on a server and sends `BodyPartSync` to the part's owning player, and it is the packet's only sender in the jar — `jar:LuaManager$GlobalObject.syncBodyPart @0-@50 L9802-9805`; `jar:jar-wide grep BodyPartSyncPacket` · C · C-only.
40. `BodyDamageSync` is the server-side remote-player injury channel: its `update` and `startSendingUpdates` both return unless `GameServer.server` is set, each updater rate-limits itself to one send per 500 ms, and it diffs overall health truncated to an int, the pain moodle level, zombie infection and the fake-infection flag — `jar:BodyDamageSync.update @0-@42 L254-262`, `jar:BodyDamageSync.startSendingUpdates @0-@6 L187-188`, `jar:BodyDamageSync$Updater.update @0-@128 L85-96` · C · C-only.
41. `BodyDamage.saveMainFields` writes exactly eleven fields — cold catch, has-a-cold, cold strength, sneeze timer as an int, reduce-fake-infection, health-from-food timer, pain reduction, cold reduction, infection time, infection mortality duration and cold damage stage — and neither overall health nor any per-part field is among them — `jar:BodyDamage.saveMainFields @0-@116 L311-322` · C · C-only.
42. `SyncPlayerFieldsPacket` has six blocks selected by a byte mask, and bit 2 writes and reads the whole `CharacterTraits` list while bit 8 writes `BodyDamage.saveMainFields` — `jar:SyncPlayerFieldsPacket.writeParam @1 L52` and `parseParam @127-@143 L104-107` (both switches decoded) · C · C-only. **This appears to contradict the register rows saying no packet was traced carrying the character trait list to a client; the controller should reconcile it.**
43. `sendSyncPlayerFields` is a Lua global that forwards to `GameServer.sendSyncPlayerFields` only when the process is a server, and the server call drops a null player or one whose online id is −1 — `jar:LuaManager$GlobalObject.sendSyncPlayerFields @0-@11 L3910-3913`, `jar:GameServer.sendSyncPlayerFields @0-@35 L2459-2463` · C · C-only.
44. `SyncPlayerStatsPacket` carries the whole `Nutrition` object when its mask is −1 and otherwise one float per set bit of the 24-stat mask — `jar:SyncPlayerStatsPacket.write @16-@91 L69-78` · C · C-only.
45. `Stats.save` writes all 24 stats with no per-field mask, and `Stats.write` writes one stat by `ORDERED_STATS` index and warns on an out-of-range index — `jar:Stats.save @0-@39 L55-58`, `jar:Stats.write @0-@48 L69-74` · C · C-only.
46. `updateStats_WakeState` runs when the process is a server, or when it is not a client and the character is the local player instance, so the awake and sleeping stat paths never run on a multiplayer client — `jar:IsoGameCharacter.updateStats_WakeState @0-@45 L10224-10234` · C · C-only.
47. `updateStress` carries no side gate of its own and relies on `IsoPlayer.calculateStats`; it adds sound stress unless the character is deaf, plus a per-bitten-part and a per-scratched-part term — `jar:IsoGameCharacter.updateStress @0-@144 L10333-10346` · C · C-only.
48. `Moodles.Update` carries no side gate, so each side recomputes its own moodles from its own stats — `jar:Moodles.Update @0-@49 L60-65` · C · C-only.
49. `MoodleStat` does not appear anywhere in the exposer's class set, so the moodle thresholds are unreachable from Lua even though every threshold setter is public — `jar:LuaManager$Exposer.exposeAll() dump` (3055 lines, zero occurrences) · C · C-only.
50. Both `BodyDamage.Update` and `calculateStats` are gated on `SystemDisabler.doCharacterStats`, so a debug switch can disable the whole body and stat simulation — `jar:IsoGameCharacter.updateInternal @1524-@1555 L9222-9230` · C · C-only.
51. `BodyDamage.Update` drives nine sub-updaters in a fixed order — the thermoregulator, then dragging-corpse, wetness, cold, boredom, strength, panic state, temperature state, discomfort and illness — all of them inheriting its server-only gate — `jar:BodyDamage.Update @218-@258 L2198-2210` · C · C-only.
52. Infection resistance is `IsoGameCharacter.getReduceInfectionPower`, which drains `ZOMBIE_FEVER` by the infection growth rate per multiplier unit while decrementing itself, and its setter is public — `jar:BodyDamage.Update @2273-@2362 L2502-2507` · C · C-only.
53. Six identifiers the design assumed do not exist on this build: `FoodSicknessLevel`, `getInfectionLevel`, `FakeInfectionLevel`, `getWoundHealingRate`, `setHealthAdditionModifier` and `CharacterStat.FEAR` are each absent from every class entry in the jar — `jar:jar-wide grep` on each string · C · C-only.
54. Drunkenness is `CharacterStat.INTOXICATION` on a 0–100 scale: `DRUNKENNESS` and `DrunkennessLevel` are absent from every class entry in the jar — `jar:CharacterStat.<clinit> @113-@122 L21`; `jar:jar-wide grep DRUNKENNESS`, `grep DrunkennessLevel` · C · C-only.
55. Character poison is `CharacterStat.POISON`; `setPoisonLevel` exists only on `Food` and `Item`, which is item poison — `jar:jar-wide grep setPoisonLevel`; `jar:BodyDamage.Update @954-@1090 L2342-2353` · C · C-only.

## Not read

- **Cadence, everywhere.** Not one rate on this page was timed. The jar gives the constants and the multiplier they are scaled by; how often `BodyDamage.Update` is reached on a real dedicated server, and therefore what any of these rates costs per game-hour, is a run question.
- **`IsoGameCharacter.health`'s carrier.** The field is read by `isDead` and written by `setHealth`, and it is in neither `PlayerStatsPacket` nor `saveMainFields`. How (or whether) it reaches a multiplayer client was not established.
- **Who drives `BodyDamageSync`.** The jar-wide grep names `IngameState` and `IsoWorld` as holding the literal; neither class was opened, and what triggers `startSendingUpdates` / `stopSendingUpdates` (a UI action, a proximity test, something else) is unread.
- **`BodyPartSyncPacket`'s recipient set.** `syncBodyPart` sends with the owning player as the first argument to `INetworkPacket.send`; whether that reaches only that client, or that client plus others, was not settled from the bytecode.
- **Nine sub-updater bodies.** `BodyDamage.UpdateBoredom`, `UpdatePanicState`, `UpdateDiscomfort`, `UpdateIllness`, `UpdateStrength`, `UpdateWetness`, `UpdateCold`, `UpdateTemperatureState` and `UpdateDraggingCorpse` were located at their call sites only. `UpdatePanicState` and `UpdateBoredom` in particular are where the panic and boredom stats are actually driven, and neither was dumped.
- **`Moodle.Update`.** The thresholds were read out of `MoodleStat.<clinit>` rather than out of `Moodle.Update`, so the comparison operator and the evaluation order for the mood moodles were not re-verified this session (the register already carries them for hunger and thirst).
- **`BodyPartType.getDamageModifyer` and `getPainModifyer`.** Both are load-bearing in the overall-health and pain formulas and neither was dumped, so the per-part weights are unknown.
- **`CombatManager.applyDamage(BodyPart, float)`.** Every wound damage term in `DamageUpdate` goes through it; it was not dumped, so whether it writes part health directly or scales again is unread.
- **`generateFracture`, `generateFractureNew`, `generateDeepWound`, `generateDeepShardWound`, `generateZombieInfection`, `generateBleeding`.** All public and exposed; none dumped, so what each one sets (and whether it is safe to call from Lua on a server) is unknown.
- **`BodyDamage.getGeneralWoundInfectionLevel`** and **`getApparentInfectionLevel`**: both public, neither dumped.
- **`setForceWakeUp`.** Located by grep in `IsoGameCharacter`, `ILuaGameCharacter`, `SleepingEvent` and `ModalDialog`; its body and signature were not read, and the sleep surface belongs to the other agent anyway.
- **`Kill`, `dieNetwork`, `addOnDiedListener`.** Flags read, bodies not dumped; whether a mod can safely kill a player with any of them rather than through health is unsettled.
- **Thermoregulator formulas.** Deliberately out of scope; only the writability audit and the `TEMPERATURE` round trip were read.
- **Whether any of this is safe to call from Lua.** The exposure test says a class is reachable and the flags say a member is public. Neither says a call resolves to the overload you want, behaves the same on both sides, or does not park a `-debug` client in the debugger. Every candidate above needs a harness probe before it becomes a measured claim.
