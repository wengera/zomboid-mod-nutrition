# Health surfaces
Verified against 42.20.4 (b0bbce05d5) · 2026-09-30 · scope: what a mod can drive in the body-damage model — overall and per-part health, regeneration, the severe-moodle drain, poison and infection, pain, wounds and healing, the mood moodles and the thermal door; the stat registry, the updaters, the side gates and the packets are handed off.

## Key facts

- The four regeneration constants default to `0.002`, `0.0013`, `0.0008` and `0.02` (standard, reduced, severely reduced, sleeping), each with a public setter [#2354/C/C-only].
- The regeneration tier reaches its constant through a `tableswitch` decoded as low `0`, high `3`, default at the asleep block, so tier 3 adds nothing and a sleeper takes the sleeping addition [#2353/C/C-only].
- Every severe-moodle health loss is built from one public constant, `healthReductionFromSevereBadMoodles`, defaulting to `0.0165` [#2355/C/C-only].
- The severe-moodle drain has six terms — hunger over `50`, thirst over `10`, two sickness arms, bleeding and heavy load — summed into one `ReduceGeneralHealth` call per tick [#2356/C/C-only].
- Health changes through `ReduceGeneralHealth` and `AddGeneralHealth`; a direct `setOverallBodyHealth` write is recomputed away on the next server tick unless it is exactly zero [#2344/C/C-only] [#2343/C/C-only].
- The engine kills with `ReduceGeneralHealth(110.0f)`, and a character at or below zero health is killed by `die()` on the server only [#2348/C/C-only] [#2349/C/C-only].
- The poison health drain is `0.0035 × min(POISON / 10, 3)` per multiplier unit, so it caps at `0.0105` [#2358/C/C-only].
- A splinted fracture heals at `5e-5 × splintFactor` per multiplier unit against `5e-6` unsplinted, ten times faster per unit of splint factor [#2367/C/C-only].
- A multiplier on a part's `bleedingTime` scales its total bleeding damage by about the multiplier's square, because the term is both the duration and the per-tick rate [#2365/C/arith.].
- Body temperature is `CharacterStat.TEMPERATURE`, `20` to `40` with default `37`, and a write to it pulls the thermal core halfway toward it on the next update [#2372/C/C-only] [#2373/C/C-only].
- The thermoregulator's weight-derived fatness term moves heat loss and heat generation by up to 20 per cent each way [#2379/C/C-only].

## How it works

The tick methods on this page run inside `BodyDamage.Update` or `BodyPart.DamageUpdate`, whose side gates are stated at [../platform/mp-model.md#ownership](../platform/mp-model.md#ownership); the stats they read and write are registered at [character-stats.md#registry](character-stats.md#registry).
A multiplier unit is one `GameTime.getMultiplier()` step; how a step converts to game time is stated at [body-and-weight.md#time-unit](body-and-weight.md#time-unit).

<a id="health-api"></a>
### The health API

Overall body health is not a store of its own: it is recomputed from the parts [#2345/C/C-only].
The formula is `100 − min(100, Σ (100 − part health) × getDamageModifyer(i) + getDamageFromPills())`, and the per-part damage modifiers inside it are not read [#2345/C/C-only].
`calculateOverallHealth` runs at the end of every `BodyDamage.Update` and writes its result through `setOverallBodyHealth`, which is itself a raw, unclamped field write [#2344/C/C-only].
A mod that calls `setOverallBodyHealth` directly therefore sees its value replaced by the part sum on the next server tick [#2344/C/C-only].
The exception is a write of exactly zero: it meets the exact-zero stop before the recompute, so it persists, and `isDead` then kills the character on the server [#2343/C/C-only] [#2344/C/C-only] [#2349/C/C-only].

The two supported routes spread an amount over the parts instead [#2346/C/C-only] [#2347/C/C-only].
`ReduceGeneralHealth(f)` returns at once for an argument at or below zero [#2346/C/C-only].
Otherwise it divides the argument by the part count and each part's share again by that part's damage modifier, then calls `BodyPart.ReduceHealth` on every part [#2346/C/C-only].
Before any of that it calls `forceAwake` on its character whenever overall health is at or below `10`, so a drain that crosses that line wakes a sleeper [#2346/C/C-only].
`AddGeneralHealth(f)` counts only the parts below `100` health, divides the argument among them and applies no damage modifier [#2347/C/C-only].
A heal therefore concentrates on the damaged parts, while a loss lands on every part [#2346/C/C-only] [#2347/C/C-only].

The tick stops when overall body health is exactly zero [#2343/C/C-only].
At that value `BodyDamage.Update` returns before its regeneration, the severe-moodle drain, poison, pain, infection, the per-part update and the overall-health recompute [#2343/C/C-only].
A negative value, which only a raw `setOverallBodyHealth` write can produce, does not trigger the stop [#2343/C/C-only] [#2345/C/C-only].

Death needs no new API [#2349/C/C-only].
A character is dead when its own `health` field or its overall body health is at or below zero [#2349/C/C-only].
`IsoGameCharacter.updateInternal` then calls `die()`, and only when the process is a server [#2349/C/C-only].
The engine's own fatal move is `ReduceGeneralHealth(110.0f)`, used on both lethal arms of the zombie-infection path — at once under the mortality option's first value, and when the mortality clock completes [#2348/C/C-only].
The recompute caps the damage sum at `100`, so after that call overall health reads exactly zero and the next tick stops at once [#2348/C/C-only] [#2345/C/C-only] [#2343/C/C-only].

`IsoGameCharacter.setHealth` writes the character's separate `health` field [#2350/C/C-only].
It refuses only the exact value zero, and only while the character is invulnerable; any other value, negative or above the usual range, is stored unclamped [#2350/C/C-only].

Three state flags look like health levers and are bare field writes [#2351/C/C-only].
`setAsleep` stores its argument and nothing else [#2351/C/C-only].
`forceAwake` sets its wake-up flag only on a character that is already asleep [#2351/C/C-only].
`setKnockedDown` stores its flag and starts no animation or state change of its own; whether another reader turns the flag into a visible knock-down is not read [#2351/C/C-only].

One debug switch sits above the whole model [#2352/C/C-only].
`IsoGameCharacter.updateInternal` gates both `BodyDamage.Update` and `calculateStats` on `SystemDisabler.doCharacterStats`, so with it off neither the body nor the stats simulate [#2352/C/C-only].

<a id="regeneration"></a>
### Regeneration

Regeneration is one accumulator per tick, fed by the health-from-food term, the tier addition and the sleeping addition, and handed to `AddGeneralHealth` once [#2353/C/C-only] [#2385/C/C-only].
A tier index is built from the `HUNGRY`, `SICK` and `THIRST` moodle levels, and a `tableswitch` maps it to one of four constants [#2353/C/C-only].
The switch decodes with low `0`, high `3` and its default at the asleep block; a sleeping character's tier of `-1` falls to that default and takes the sleeping addition instead of any awake constant [#2353/C/C-only].
The decoded switch, with the food term and the tier build above it and the sleeping arm below it, is this [#2353/C/C-only] [#2385/C/C-only]:

```java
// BodyDamage.Update, the regeneration block
float add = 0;                                                   // @549  L2267
if (getHealthFromFoodTimer() > 0) {                              // @551  L2269
  add += getHealthFromFood() * mult;                             // @560  L2270
  setHealthFromFoodTimer(getHealthFromFoodTimer() - 1 * mult);   // @574  L2271
}
int tier = 0;                                                    // @591  L2274
if (HUNGRY == 2 || SICK == 2 || THIRST == 2) tier = 1;           // @645  L2280
if (HUNGRY == 3 || SICK == 3 || THIRST == 3) tier = 2;           // @699  L2287
if (HUNGRY == 4 || THIRST == 4)             tier = 3;            // @736  L2293  (SICK absent)
if (isAsleep())                             tier = -1;           // @749  L2297
switch (tier) {                      // @754 tableswitch low 0 high 3, default -> @839
  case 0: add += getStandardHealthAddition()       * mult; break;  // @784 L2303
  case 1: add += getReducedHealthAddition()        * mult; break;  // @801 L2306
  case 2: add += getSeverlyReducedHealthAddition() * mult; break;  // @818 L2309
  case 3: add += 0;                                                // @835 L2312
}
if (isAsleep()) {                                                // @839  L2316  (ifeq -> @925)
  if (GameClient.client)
    add += 15 * getGameWorldSecondsSinceLastUpdate() / 3600;     // @849  L2317-L2318
  else
    add += getSleepingHealthAddition() * mult;                   // @875  L2320
  if (HUNGRY == 4 || THIRST == 4) add = 0;                       // @889  L2322-L2323
}
AddGeneralHealth(add);                                           // @925  L2328
```

Each test is an equality on a moodle level, run in ascending order, so the highest matching level wins [#2353/C/C-only].
The sleeping addition is zeroed by a level-4 hunger or thirst [#0515/C/C-only].
While `healthFromFoodTimer` is above zero the same accumulator also takes `getHealthFromFood() × mult`, `healthFromFood` defaulting to `0.015`, and the timer falls by one multiplier unit per tick [#2385/C/C-only].
That zero-out sits inside the asleep branch, so a sleeper at level-4 hunger or thirst loses the food term with the rest while an awake character keeps it [#2385/C/C-only].
How the tiers read against the hunger and thirst moodles is stated at [body-and-weight.md#moodles](body-and-weight.md#moodles), which cites this decoded switch.

The four constants live on the character's own `BodyDamage` and are set in its constructor [#2354/C/C-only].
Their defaults are `0.002` standard, `0.0013` reduced, `0.0008` severely reduced and `0.02` sleeping [#2354/C/C-only].
Each has a public getter and setter on an exposed class, so a mod can retune the whole ladder for one character without touching another's [#2354/C/C-only].
`BodyDamage` has no `setHealthAdditionModifier`: the ladder is moved by writing the four constants [#2354/C/C-only] [#2382/C/C-only].

The severe-moodle constant sits beside them [#2355/C/C-only].
`healthReductionFromSevereBadMoodles` defaults to `0.0165` and has a public getter and setter [#2355/C/C-only].
It is the single constant every severe-moodle health-loss term is built from, so one write scales all six terms together [#2355/C/C-only].

<a id="severe-drain"></a>
### The severe-moodle drain

The drain is six terms summed into one total, which `ReduceGeneralHealth` applies once per tick; with `red` the severe-moodle constant and `mult` the multiplier, the terms are these [#2356/C/C-only]:

| trigger | term |
|---|---|
| `HUNGRY` level exactly 4 | `red / 50 × mult` |
| `THIRST` level exactly 4 | `red / 10 × mult` |
| `SICK` level 4 and `FOOD_SICKNESS > ZOMBIE_INFECTION` | `red × mult` |
| `SICK` level 4, otherwise: the wound-infection option above 0 and the general wound-infection level above `ZOMBIE_INFECTION` | `red × mult` |
| `BLEEDING` level exactly 4 | `red × mult` |
| `HEAVY_LOAD` above level 2, not in a vehicle, not asleep, not sitting on the ground or on furniture, metabolic target not `SeatedResting`, not a fast-forwarding server, health above 75, and a one-in-ten roll per thirtieth of a second | `red / ((5 − level) / 10) × mult`, half of it also added as back-muscle strain |

The two sickness arms are exclusive, so at most one of them contributes on a tick [#2356/C/C-only].
The hunger and thirst terms' per-unit sizes and their cost per game-hour are stated at [body-and-weight.md#moodles](body-and-weight.md#moodles) [#0516] [#0518/C/arith.].
The poison drain of [#poison-infection](#poison-infection) joins the same total before the call [#2358/C/C-only].

Each nonzero term reports itself to Lua [#2357/C/C-only].
`BodyDamage.Update` fires `OnPlayerGetDamage` with the character, a tag and the amount once per nonzero term, with the tags `POISON`, `HUNGRY`, `SICK`, `BLEEDING`, `THIRST` and `HEAVYLOAD` [#2357/C/C-only].
The zombie-infection path fires the same event with the tag `INFECTION` on each of its three arms that reduce health [#2357/C/C-only].
A mod that wants to observe the drain can therefore listen rather than poll, on the side the tick runs on [#2357/C/C-only].
The event's registration and the hunger and thirst arms are stated at [../platform/lua-platform.md#events](../platform/lua-platform.md#events).

<a id="poison-infection"></a>
### Poison, food sickness and infection

Character poison is a stat, `CharacterStat.POISON`, which `BodyDamage.Update` reads and decays each tick [#2361/C/C-only].
`setPoisonLevel` exists in the jar only on `Food` and `Item`, where it is item poison and never touches a character [#2361/C/C-only].
What raises the stat at eat time is stated at [food-item-model.md#poison](food-item-model.md#poison).

Poison costs health only in combination with the sickness moodle [#2358/C/C-only].
The drain runs while `POISON` is above `10` and the `SICK` moodle is at level 1 or more [#2358/C/C-only].
Its size is `0.0035 × min(POISON / 10, 3)` per multiplier unit, so it caps at `0.0105` once poison reaches `30` [#2358/C/C-only].
Poison then decays by `ZomboidGlobals.poisonLevelDecrease` per multiplier unit, faster while the food-eaten moodle is up [#0520/C/C-only].

Poison feeds food sickness on every tick it is above zero [#2359/C/C-only].
`FOOD_SICKNESS` grows by `getInfectionGrowthRate() × (2 + round(POISON / 10))` per multiplier unit, the growth rate defaulting to `0.001` [#2359/C/C-only].
The growth rate has a public setter, so it is a lever on both food sickness and the infection terms that share it [#2359/C/C-only] [#2360/C/C-only].

Infection resistance is a character field, not a stat [#2360/C/C-only].
While `IsoGameCharacter.getReduceInfectionPower` is positive and overall health is above zero, it drains `ZOMBIE_FEVER` by the infection growth rate per multiplier unit [#2360/C/C-only].
It decrements itself by the same amount and is floored at zero, so a value written to it is a budget that spends down [#2360/C/C-only].
Its setter is public [#2360/C/C-only].

<a id="pain"></a>
### Pain

The `PAIN` stat is driven toward a target the parts define [#2362/C/C-only].
With no pain effect running, the target is `Σ part pain × getPainModifyer(i) − getPainReduction()`, and the per-part pain modifiers inside it are not read [#2362/C/C-only].
When the target is above the current `PAIN`, the stat rises by one five-hundredth of the gap per tick [#2362/C/C-only].
When the target is lower, `PAIN` snaps down to it at once [#2362/C/C-only].
`painReduction` itself decays by `0.005` per multiplier unit and is floored at zero [#2362/C/C-only].
Pain therefore rises slowly and falls instantly, so a mod that raises a part's pain sees the stat lag, and one that lowers it sees no lag [#2362/C/C-only].

<a id="wounds"></a>
### Wounds and healing

Each part's wound damage per tick is a constant times the part's `damageScaler` and the multiplier [#2364/C/C-only].
Unbandaged, the constants are `3.125` for an unstitched deep wound, `1.875` for a cut, `2.1875` for a bite and `0.9375` for a scratch [#2364/C/C-only].
Bleeding costs `0.2857143 × bleedingTime / 10` on the same scale [#2364/C/C-only].
A bandage halves the deep-wound term to `1.5625` and suppresses the scratch, cut, bite and bleeding terms outright [#2364/C/C-only].
The four wound terms go through `CombatManager.applyDamage`, while the bleeding term goes through `BodyDamage.ReduceGeneralHealth` and then fires `OnPlayerGetDamage` with `BLEEDING` [#2364/C/C-only].

The bleeding term has a trap for any multiplier on it [#2365/C/arith.].
`bleedingTime` is both the duration of the bleed and a factor in its per-tick rate [#2365/C/arith.].
An unbandaged part's `bleedingTime` counts down linearly by `2e-5` per multiplier unit, so the total damage from one bleed grows with the square of its starting `bleedingTime` [#2365/C/arith.].
A multiplier on `bleedingTime` therefore scales total bleeding damage by about its square; the arithmetic is the part a re-reader redoes, and it is exact only for an unbandaged part carrying no glass and left unbandaged throughout [#2365/C/arith.].

`damageScaler` is not a lever [#2363/C/C-only].
It is a private field written only in the `BodyPart` constructor, and no class in the jar contains `setDamageScaler`, so a part's wound-damage scale is fixed for its life [#2363/C/C-only].

Healing in this model is the wound timers counting down [#2366/C/C-only].
A bandaged scratch's `scratchTime`, for one, loses `1.5e-4` per multiplier unit, and a further `1e-4` while plantain is applied [#2366/C/C-only].
When a timer reaches zero its wound stops doing damage [#2364/C/C-only].
Every timer, and the plantain, comfrey, garlic and splint factors, has a public setter on the exposed `BodyPart`, and those setters are a mod's only healing-rate handles [#2366/C/C-only].
A slower heal is written by moving a timer back up, and a faster one by moving it down; no rate setter exists to do it instead [#2366/C/C-only] [#2382/C/C-only].

Fractures heal on their own timer [#2367/C/C-only].
A splinted fracture's `fractureTime` loses `5e-5 × multiplier × splintFactor` per tick, against `5e-6 × multiplier` unsplinted [#2367/C/C-only].
That is ten times faster per unit of splint factor, and comfrey adds a further `5e-6 × multiplier` on top of either [#2367/C/C-only].

Four `BodyPart` setters are easy to mistake for healing rates [#2368/C/C-only].
The `scratch`, `cut`, `burn` and `deepWound` speed modifiers have only one reader in the jar, `IsoGameCharacter.calculateInjurySpeed`, which is a movement and combat speed term [#2368/C/C-only].
A mod that wants an injury to cripple harder can set them; a mod that wants slower healing must move a timer or a factor instead [#2368/C/C-only] [#2366/C/C-only].

A server-side write to any per-part field reaches the owning client only through `syncBodyPart`, whose gate is stated among the sync globals of [../platform/mp-model.md](../platform/mp-model.md#sync-globals) and whose field mask with the body-part packet of [wire-packets.md](wire-packets.md).

<a id="mood-surface"></a>
### The mood surface

The mood stats are registered stats with their own ranges, listed at [character-stats.md#registry](character-stats.md#registry).
Stress and the wake-state updaters run inside `calculateStats`, which a `CalculateStats` hook returning true skips [#0469/C/C-only]; panic, boredom, pain and sickness are driven inside `BodyDamage.Update`, which that hook does not reach [#2352/C/C-only] [#2384/C/C-only].
What a player sees of them is the moodle each stat feeds, and `MoodleStat` fixes where each moodle level begins [#2369/C/C-only].
`MoodleStat` registers each moodle stat as a minimum plus four level thresholds; the mood moodles' thresholds are these [#2369/C/C-only]:

| moodle | stat scale | level 1 | level 2 | level 3 | level 4 |
|---|---|---|---|---|---|
| `PANIC` | 0–100 | 6 | 30 | 65 | 80 |
| `STRESS` | 0–1 | 0.25 | 0.50 | 0.75 | 0.90 |
| `UNHAPPY` | 0–100 | 20 | 45 | 60 | 80 |
| `BORED` | 0–100 | 25 | 50 | 75 | 90 |
| `PAIN` | 0–100 | 10 | 20 | 50 | 75 |
| `SICK` | 0–1 | 0.25 | 0.50 | 0.75 | 0.90 |
| `DRUNK` | 0–100 | 10 | 30 | 50 | 70 |

The hunger, thirst, endurance and heavy-load thresholds are stated at [body-and-weight.md#moodles](body-and-weight.md#moodles) [#0508/M/n=1] [#0509/M/n=1] [#0510/C/C-only].
The comparison operator and evaluation order inside `Moodle.Update` were re-read for hunger and thirst only, so the mood rows above are the registered values and not a measured firing point [#2369/C/C-only].

One ladder is not monotonic [#2370/C/C-only].
The `HYPOTHERMIA` moodle's third threshold is `9.0`, below its first at `30` and its second at `70`, as shipped [#2370/C/C-only].
How `Moodle.Update` resolves a ladder in that shape is not read [#2370/C/C-only].

The thresholds cannot be retuned from Lua [#1141/C/C-only].
`MoodleStat` does not appear anywhere in the `LuaManager$Exposer.exposeAll()` class set, so a mod never reaches its public threshold setters, the wall stated at [../reference/wall-map.md#d2-d3](../reference/wall-map.md#d2-d3) [#1141/C/C-only].
A mod moves a moodle only by moving the stat behind it [#1141/C/C-only].

Drunkenness is not named as such [#2371/C/C-only].
It is `CharacterStat.INTOXICATION` on a `0` to `100` scale, read by the `DRUNK` moodle, and `DRUNKENNESS` and `DrunkennessLevel` are absent from every class entry in the jar [#2371/C/C-only].

<a id="thermal"></a>
### The thermal door

Body temperature is a registered stat, not a `BodyDamage` field [#2372/C/C-only].
`CharacterStat.TEMPERATURE` runs from `20` to `40` with a default of `37`, and `setTemperature` exists in the jar only on `Clothing`, `IsoHeatSource` and `Item` [#2372/C/C-only].

That stat is the one way into the thermal core from Lua [#2373/C/C-only].
`Thermoregulator.updateHeatDeltas` adds the core heat delta to the core node and then clamps it to `20` to `42` degrees [#2373/C/C-only].
It then reads `CharacterStat.TEMPERATURE`, and when the stat and the core differ by more than `0.001` it lerps the core halfway toward the stat [#2373/C/C-only].
Last, it writes the core back into the stat [#2373/C/C-only].
A server-side write to the stat therefore moves the core halfway on the next update, after which the stat is driven from the core again [#2373/C/C-only].
A mod that wants to hold a temperature must re-write the stat on every update, and one that writes it once sees half the step land [#2373/C/C-only].

Everything else in the thermoregulator is closed [#2374/C/C-only] [#2375/C/C-only].
Every step of the thermal update — `updateSetPoint`, `updateMetabolicRate`, `updateNodesHeatDelta`, `updateHeatDeltas`, `updateNodes`, `updateBodyMultipliers`, `updateClothing`, `updateCoreRateOfChange` and `updateThermalDamage` — is private, and only the whole `update()` is public [#2374/C/C-only].
Beside its save-and-load pair, the class's whole public writable surface is the static `setSimulationMultiplier`, the two `setMetabolicTarget` overloads and `reset` [#2375/C/C-only].
`setSimulationMultiplier` is static, so it is a process-wide knob and not a per-character one [#2375/C/C-only].
The class declares no insulation setter [#2375/C/C-only].
`Thermoregulator$ThermalNode` declares `19` fields and `28` methods and not one setter, so insulation, wind resistance, node temperature and node wetness are read-only from Lua [#2376/C/C-only].
`setInsulation` exists in the jar only on `Clothing` and `Item`, the clothing script side [#2376/C/C-only].
Node insulation is computed per node by the private `ThermalNode.calculateInsulation` inside `updateNodesHeatDelta`, and it divides each node's skin heat delta as `delta / (1 + insulation)` [#2377/C/C-only].

Body fat already enters the model through weight [#2378/C/C-only].
The thermoregulator derives a fatness term on `[−1, +1]` from `Nutrition.getWeight()` as `clamp01((w / 75 − 0.5) × 0.666)`, remapped by `(x − 0.5) × 2` [#2378/C/C-only].
The term is zero at about 93.8 kg, positive above it and negative below [#2378/C/C-only].
On the hot side it multiplies a node's heat loss by `1 − 0.2 × fat`, and on the cold side it multiplies heat generation by `1 + 0.2 × fat` [#2379/C/C-only].
Body fat therefore suppresses heat loss by up to 20 per cent in heat and raises heat generation by up to 20 per cent in cold, and a thin character takes the reverse [#2379/C/C-only].
A fitness term of the same form sits beside it [#2379/C/C-only].
The band and the mapping are fixed, so a mod changes the fat effect only by changing the weight the thermoregulator reads [#2378/C/C-only] [#2375/C/C-only].

Hunger, fatigue and thirst scale the two sides as well [#2380/C/C-only].
Cold-side heat generation is scaled by `0.2 + 0.8 × getEnergy()` [#2380/C/C-only].
`getEnergy` is `0.6 × (1 − (0.4h + 0.6h²)) + 0.4 × (1 − (0.4f + 0.6f²))` over hunger `h` and fatigue `f`, so a hungry, tired character generates less heat in the cold [#2380/C/C-only].
Hot-side heat loss is scaled by `0.2 + 0.8 × (1 − thirst)`, so a thirsty character sheds less heat [#2380/C/C-only].
The thermoregulator reaches `Nutrition` in exactly two places, its constructor and the `getWeight` call in `updateNodesHeatDelta`, and never reads a lipid store or a separate fat store [#2381/C/C-only].
What the thermoregulator's totals do to calorie burn, thirst and fatigue is stated at [body-and-weight.md#multipliers](body-and-weight.md#multipliers) [#0464].

## Walls and bounds
<a id="walls"></a>

- The engine has no `FoodSicknessLevel`, `getInfectionLevel`, `FakeInfectionLevel`, `getWoundHealingRate`, `setHealthAdditionModifier` or `FEAR` character stat: the first five are absent from every class entry, and `FEAR` occurs only in a book class and bundled native-access classes [#2382/C/C-only].
- The engine has no unconscious or fainting state: `Unconscious`, `setUnconscious`, `Fainted` and `setFainted` are each absent from every class entry, so a mod can set the sleep and knock-down flags and nothing in the jar says a state follows [#2383/C/C-only].
- `BodyDamage.Update` runs the thermoregulator and then nine sub-updaters in a fixed order — dragging-corpse, wetness, cold, boredom, strength, panic state, temperature state, discomfort and illness — before regeneration and the drain, and their bodies are unread, so which of them overwrites a stat a mod writes between ticks is not established [#2384/C/C-only].
- `damageScaler` has no setter and the moodle thresholds are unreachable from Lua, stated at [#wounds](#wounds) and [#mood-surface](#mood-surface) [#1141/C/C-only] [#2363/C/C-only].
- No thermal node, insulation or thermal-resistance value has a setter; the temperature stat is the only door [#2376/C/C-only] [#2373/C/C-only].
Not covered: the nine sub-updater bodies (`UpdatePanicState` and `UpdateBoredom` among them, where panic and boredom are driven), `BodyPartType.getDamageModifyer` and `getPainModifyer`, `CombatManager.applyDamage`, the `generate*` wound and fracture methods, `getGeneralWoundInfectionLevel` and `getApparentInfectionLevel`, `Kill`, `dieNetwork` and `addOnDiedListener`, the carrier of `IsoGameCharacter.health` to a client, the thermoregulator's own formulas beyond the fat, energy and fluid terms, and `ThermalNode.calculateInsulation`.

## Open
<a id="open"></a>

- Whether a mod kills through `ReduceGeneralHealth(110)` or through `setHealth(0)` is a decision: the first is the engine's own fatal move, while the second writes a separate field whose route to a client is unread [#2348/C/C-only] [#2350/C/C-only].
- Whether a healing-rate effect moves the four regeneration constants, the per-part timers, or both is a decision: the constants scale whole-body regeneration per character, and the timers are the only per-wound lever [#2354/C/C-only] [#2366/C/C-only].
- Whether a bleeding effect scales `bleedingTime` or adds bleeds is a decision the squared total forces: a multiplier on the time is felt as roughly its square [#2365/C/arith.].
- Whether a temperature effect writes `CharacterStat.TEMPERATURE` every update or accepts the halfway step of one write is a decision the lerp forces [#2373/C/C-only].
- Whether a knock-down or sleep effect can rest on `setKnockedDown` or `setAsleep` is a decision that waits on a live probe, because both are bare field writes with no state machine read behind them [#2351/C/C-only] [#2383/C/C-only].
- Whether the non-monotonic `HYPOTHERMIA` ladder matters to a mod that reads the moodle is a decision that waits on a read of `Moodle.Update` [#2370/C/C-only].

## See also

- [character-stats.md](character-stats.md) — the stat registry, the updaters and the stat hook's place in the tick.
- [body-and-weight.md](body-and-weight.md) — the hunger and thirst moodles, their regeneration tiers and drain costs, and the thermoregulator's multipliers.
- [endurance-fatigue-sleep.md](endurance-fatigue-sleep.md) — endurance, fatigue and sleep, which share the thermoregulator's fatigue multiplier.
- [../platform/mp-model.md](../platform/mp-model.md) — the server-only side gates and the `syncBodyPart` global.
- [wire-packets.md](wire-packets.md) — the body-part packet's field mask and the player-stats packet.
- [../platform/lua-platform.md](../platform/lua-platform.md) — `OnPlayerGetDamage` and the `CalculateStats` hook.
