# Health surfaces
Verified against 42.20.4 (b0bbce05d5) · 2026-10-01 · scope: what a mod can drive in the body-damage model — overall and per-part health, regeneration, the severe-moodle drain, poison and infection, pain, wounds and healing, the mood moodles and the thermal door; the stat registry, the updaters, the side gates and the packets are handed off.

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
Vanilla makes that call with its reduction total, the poison and severe-moodle terms, on every server tick that reaches the drain, whether or not the total is zero, and the wake test runs before the zero return, so a sleeper at 10 health or less, above 0 and outside god mode, is woken every tick with no drain running [#3900/C/inference].
`AddGeneralHealth(f)` counts only the parts below `100` health, divides the argument among them and applies no damage modifier [#2347/C/C-only].
A heal therefore concentrates on the damaged parts, while a loss lands on every part [#2346/C/C-only] [#2347/C/C-only].
The damage modifiers are 0.1 for the hands, 0.2 for the forearms, lower legs and feet, 0.3 for the upper arms and upper legs, 0.35 for the upper torso, 0.4 for the lower torso and groin, 0.6 for the head and 0.7 for the neck, 5.05 over the 17 parts [#3898/C/C-only].
A general loss of 100 from full therefore leaves the hands at 41.18 and the neck at 91.60 with no part clamped, and a heal of y spread over 17 damaged parts that none of them completes raises overall health by y × 5.05 / 17, about 0.297 y [#3898/C/C-only].
A general loss marks no injury: `BodyPart.ReduceHealth` only clamps and writes the part's health, `BodyPart.DamageUpdate` reads part health only to clamp it at 0, and `BodyPart.HasInjury` reads no health [#3899/C/C-only].
The health panel, outside cheat mode, lists a part only on an injury, a bandage, stitches, a splint, additional pain over 10 or stiffness over 5, and prints part health only in cheat mode, so a player sees a general drain only as overall health falling [#3899/C/C-only].
Measured live, a server `ReduceGeneralHealth(10)` reached the owning client's overall and per-part health within about a second, the client's later copies equalling server reads taken a fraction of a second before; the packet that carries them was not identified [#3040/M/n=1].

The tick stops when overall body health is exactly zero [#2343/C/C-only].
At that value `BodyDamage.Update` returns before its regeneration, the severe-moodle drain, poison, pain, infection, the per-part update and the overall-health recompute [#2343/C/C-only].
A negative value, which only a raw `setOverallBodyHealth` write can produce, does not trigger the stop [#2343/C/C-only] [#2345/C/C-only].

Death needs no new API [#2349/C/C-only].
A character is dead when its own `health` field or its overall body health is at or below zero [#2349/C/C-only].
`IsoGameCharacter.updateInternal` then calls `die()`, and only when the process is a server [#2349/C/C-only].
The engine's own fatal move is `ReduceGeneralHealth(110.0f)`, used on both lethal arms of the zombie-infection path — at once under the mortality option's first value, and when the mortality clock completes [#2348/C/C-only].
The recompute caps the damage sum at `100`, so after that call overall health reads exactly zero and the next tick stops at once [#2348/C/C-only] [#2345/C/C-only] [#2343/C/C-only].
Run on a live dedicated server through the harness's `health.reduce admin 110`, that call killed the character: the server read it dead at the first poll after the call and its overall health 0 at the next read [#3278/M/n=1]; the engine's own two zombie-infection arms were not exercised.

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
A tier index is built from the `HUNGRY`, `SICK` and `THIRST` moodle levels, and a `tableswitch` maps it to one of four constants [#2353/C/C-only] [#2721/C/C-only].
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

Each test is an equality on a moodle level, run in ascending order, so the highest matching level wins [#2353/C/C-only] [#2721/C/C-only].
The sleeping addition is zeroed by a level-4 hunger or thirst [#0515/C/C-only].
While `healthFromFoodTimer` is above zero the same accumulator also takes `getHealthFromFood() × mult`, `healthFromFood` defaulting to `0.015`, and the timer falls by one multiplier unit per tick [#2385/C/C-only].
That zero-out sits inside the asleep branch, so a sleeper at level-4 hunger or thirst loses the food term with the rest while an awake character keeps it [#2385/C/C-only].
How the tiers read against the hunger and thirst moodles is stated at [body-and-weight.md#moodles](body-and-weight.md#moodles), which cites this decoded switch.

The four constants live on the character's own `BodyDamage` and are set in its constructor [#2354/C/C-only].
Their defaults are `0.002` standard, `0.0013` reduced, `0.0008` severely reduced and `0.02` sleeping [#2354/C/C-only].
Each has a public getter and setter on an exposed class, so a mod can retune the whole ladder for one character without touching another's [#2354/C/C-only].
`BodyDamage` has no `setHealthAdditionModifier`: the ladder is moved by writing the four constants [#2354/C/C-only] [#2382/C/C-only].
The four constants are not saved: no save or load body names them, so a mod's values are lost at a reload and the constructor's defaults return [#3020/C/inference].
Within a session the written constants held: halved, they read back unchanged 31.9 s later; whether the halving halves awake regeneration is unmeasured, because both windows ran at hunger moodle level 4, whose tier adds nothing [#3045/M/n=1/open].

The severe-moodle constant sits beside them [#2355/C/C-only].
`healthReductionFromSevereBadMoodles` defaults to `0.0165` and has a public getter and setter [#2355/C/C-only].
It is the single constant every severe-moodle health-loss term is built from, so one write scales all six terms together [#2355/C/C-only].
The food heal, the 1600 standard health-from-food time and the severe-moodle constant are not saved either: each is set only by the constructor and its own setter, and no save or load body names it, so a value a mod writes is gone after a reload [#3897/C/inference].
The standard time is read only through its getter, by `Moodle.Update`, and the severe-moodle constant only by `BodyDamage` and `Nutrition` [#3897/C/inference].
The severe-moodle constant is not saved: in run x451 the constant written to 0.00419999985024333 read 0.016499999910593033 after the server's quit and a reuse boot of the same save, the character the saved one by its modData marker and its health, 69.2044677734375 before and 69.29570007324219 after. [#3932/M/n=1]

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
The heavy-load term's roll succeeds one tick in ten whatever the frame rate: `Rand.PerThirtiethOfASecond(10)` draws `RandStandard.Next(0, 10 x f)` and succeeds when the draw is under `f`, the thirty-frames multiplier, and `RandAbstract.Next(float, float)` returns `min + nextFloat() x (max - min)`, a uniform draw, so the term, the constant over `(5 - level) / 10` times the multiplier on a success, costs in expectation the constant over `(5 - level)` per multiplier unit. [#3924/C/inference] Vanilla's shared severe-moodle constant is per player and, written to 0 from server Lua, stops the HUNGRY-4, THIRST-4, SICK-4 and under-35 kg health terms: in run x451, with HUNGER held at 0.800000011920929 and THIRST at 0.8999999761581421, health fell 3.5656904628358954 a game hour at the constant's 0.016499999910593033 under HUNGRY 4 and THIRST 4; with it at 0 health read 96.87430572509766 at both reads over 0.4429056655750898 game hours with no HUNGRY or THIRST damage tag, and held again under SICK 4 with no SICK tag; and five setWeight calls under the weight floor cost 0.39505350364156366 beyond the drain with the constant on and 0.0 at 0. [#3930/M/n=1] The per-part bleeding damage runs with the severe-moodle constant at 0 and the constant's BLEEDING-4 term adds to it: in run x451, with four parts bleeding at BLEEDING 4 and the constant at 0, health fell 5.963110742769263 a game hour with the BLEEDING tag counting 500 and no HUNGRY, THIRST or SICK tag, and with the constant restored under HUNGRY 4, THIRST 4, SICK 4 and BLEEDING 4 it fell 67.41010440917394 a game hour, 61.44699366640468 over the constant-0 rate, the BLEEDING tag counting 455 against 91 each for HUNGRY, THIRST and SICK. [#3931/M/n=1]
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
Poison then decays by `ZomboidGlobals.poisonLevelDecrease` per multiplier unit, and while the food-eaten moodle is up by a further 1.5e-4 times its level a tick, a term without the multiplier [#3894/C/C-only].

Poison feeds food sickness on every tick it is above zero [#2359/C/C-only].
`FOOD_SICKNESS` grows by `getInfectionGrowthRate() × (2 + round(POISON / 10))` per multiplier unit, the growth rate defaulting to `0.001` [#2359/C/C-only].
The growth rate has a public setter, so it is a lever on both food sickness and the infection terms that share it [#2359/C/C-only] [#2360/C/C-only].

Infection resistance is a character field, not a stat [#2360/C/C-only].
While `IsoGameCharacter.getReduceInfectionPower` is positive and overall health is above zero, it drains `ZOMBIE_FEVER` by the infection growth rate per multiplier unit [#2360/C/C-only].
It decrements itself by the same amount and is floored at zero, so a value written to it is a budget that spends down [#2360/C/C-only].
Its setter is public [#2360/C/C-only].

The sickness stat behind the `SICK` moodle is not food sickness, and nothing in the engine's character classes lowers it.
`CharacterStat.SICKNESS` is only read in the body-damage, character, player, thermoregulator, stats, moodle and item-stats classes — by the thermoregulator's set point and by the `SICK` moodle — so a value once written stays until something writes it again [#3019/C/inference].
What the set point does with it is under [the thermal door](#thermal).

Catching a cold is an accumulator, `catchACold`, filled by the wetness updater rather than the cold updater [#3021/C/C-only].
While no cold is running and the thermoregulator's catch-a-cold delta is above 0.1, the delta, × 1.7 for Prone to Illness, × 0.45 for Resilient and × 0.25 for Outdoorsman, times 0.003 per multiplier unit is added, and at 100 the accumulator is zeroed and a cold of strength 20 starts [#3021/C/C-only].
With the delta at or below 0.1 the accumulator falls by 0.175 on every update, with no game-time multiplier, floored at 0 [#3021/C/C-only].
The cold updater only runs the course of a cold already caught [#3022/C/C-only].
A cold weakens only while the character is in a room, dry, free of hypothermia and at fatigue 0.5 or less, hunger 0.25 or less and thirst 0.25 or less, or while a cold-reduction medicine acts; otherwise it strengthens up to 100 [#3022/C/C-only].
When its strength falls below zero the cold ends and the accumulator is zeroed [#3022/C/C-only].
Nothing else resets the accumulator per tick, and it is written into the character's save [#3023/C/C-only].
Measured live, a character under a climate override of -10 (the reply's final temperature 21.861122131347656 that tick, -10 by the window's end) with WETNESS written to 100 kept the catch-a-cold delta at or under 0.022158874198794365 for about 55 s, so catchACold never left 0 [#3114/M/n=1].

<a id="pain"></a>
### Pain

The `PAIN` stat is driven toward a target the parts define [#2362/C/C-only].
With no pain effect running, the target is `Σ part pain × getPainModifyer(i) − getPainReduction()` [#2362/C/C-only].
When the target is above the current `PAIN`, the stat rises by one five-hundredth of the gap per tick [#2362/C/C-only].
When the target is lower, `PAIN` snaps down to it at once [#2362/C/C-only].
`painReduction` itself decays by `0.005` per multiplier unit and is floored at zero [#2362/C/C-only].
Pain therefore rises slowly and falls instantly, so a mod that raises a part's pain sees the stat lag, and one that lowers it sees no lag [#2362/C/C-only].

`BodyPart.setAdditionalPain(F)` is a bare write of the part's `additionalPain` field, `getAdditionalPain()` returns the field, and `getAdditionalPain(true)` returns it plus the part's `stiffness` divided by 3.5. [#4057/C/C-only]
`BodyPart.DamageUpdate` returns at once on a client for its local player, so a part's added pain falls only on the server. [#4058/C/C-only]
Each `BodyPart.DamageUpdate` lowers a part's `additionalPain` by 0.005 × `GameTime.getMultiplier()` while it is above 0 and floors it at 0, so with the multiplier summing to 2 × the day length in real minutes over a game minute (#2922) added pain falls 0.01 × that day length a game minute: 0.9 on the 90-minute day and 0.15 on the 15-minute day. [#4059]
`BodyPart.getPain` adds `getAdditionalPain(true)` to the part's wound terms and then scales the sum by a switch on the `InjurySeverity` sandbox option, one case ×0.7 and another ×1.3, the remaining value unscaled. [#4060/C/C-only]
`BodyPartType`'s pain modifier, the first float of its constructor, is 0.5 for the hands and feet, 0.6 for the forearms, upper arms and lower legs, 0.7 for the upper torso, groin and upper legs, 0.78 for the lower torso and 0.8 for the head and neck. [#4061/C/C-only]
`BodyDamage.Update` returns at once on a client for a living player, and on the server sets the PAIN target to the sum over parts of `getPain()` × the part's pain modifier less `painReduction`, raising PAIN by (target − PAIN)/500 a call when the target is above it and setting PAIN to the target otherwise, unless a pain effect is running, when PAIN is lowered by 0.0233 × the thirty-FPS multiplier instead. [#4062]
Added pain is saved with the character: `BodyDamage.save` writes each part's `getAdditionalPain()`, `BodyDamage.load` reads it back through `setAdditionalPain`, and `IsoGameCharacter.save` and `.load` call them. [#4063/C/C-only]
With a server-side `setAdditionalPain` of 20 on the lower torso re-applied once a game minute, the Pain moodle read level 1 on the server and on the client at the arm's last paired reads, and at 40 it read level 2 on both. [#4068/M/n=1]
From added pain 20 set on the lower torso at an arm start 102.84 s into the session, the client's Pain moodle first read level 1 at its read at 158.7475 s and the server's at its read at 168.115 s; from 40 set at 245.373 s, with PAIN at 14.307312965393066, level 2 first read at 268.7795 s on the client and 275.6855 s on the server. [#4069/M/n=1]
PAIN approached its target at the jar's rate (#4062): over 2347 one-tick steps with PAIN under its target by more than the grade's gap the median of the step against the predicted step was 0.9999999821124849, the server ticking 10.000211420960275 times a second. [#4070/M/n=1]
After the hold was released, PAIN followed the falling target down at once: on 255 one-tick steps PAIN read the lower torso's pain modifier times the previous tick's added pain, within the grade's tolerance. [#4071/M/n=1]
Re-set once a game minute on DayLength 4, added pain fell 0.899983361325089 a game minute at speed 1 (54.88547897338867 over 60.98499298095703 game minutes) and 0.9000071274474525 at speed 5, each minute's fall within one tick of the jar's decay over its summed multiplier (37 and 24 minutes at speed 1). [#4072/M/n=1]
On DayLength 1 added pain re-set once a game minute fell 0.15000031795638447 a game minute (9.897998809814453 over 65.98651885986328 game minutes), each of 66 minutes within one tick of the jar's decay over its summed multiplier. [#4074/M/n=1]
Added pain set to 60 on the lower torso and read 59.85633087158203 before the player quit read 59.48550033569336 at the server's first read after the player's quit, a graceful server stop and restart with no player online, and a rejoin from a fresh client restore, the server's reads between the quit and the restart finding no online player. [#4075/M/n=1]
Starvation's added pain on the lower torso, set at the onset drain, first showed the Pain moodle between 65.07650000000001 and 66.43 s after that drain on the server and between 56.58500000000001 and 56.68950000000001 s on the client, the server ticking 10.0 times a second and the client drawing 60.0 frames a second. [#4081/M/n=1]
When beriberi's legs were set with PAIN near its first threshold, the server's Pain moodle read 0 on two pairs with its PAIN at 13.10213565826416 and 13.687191009521484, and no client read was off its own PAIN's level, the client drawing 60.0 frames a second. [#4098/M/n=1]

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

`syncBodyPart` sends a per-part field to the owning client at once; its gate is stated among the sync globals of [../platform/mp-model.md](../platform/mp-model.md#sync-globals) and its field mask with the body-part packet of [wire-packets.md](wire-packets.md).
It is not the only route: measured live, a server write of a hand's `bleedingTime` with no sync reached the client 1.27 s after the write and then followed the server's countdown in steps about two seconds apart, while the same write with the sync read on the client at once; the carrier of the unsynced copy was not identified [#3041/M/n=1].
The written timer counted down on the server near the unbandaged rate, 0.035657223114633624 per game hour, and bled through the `BLEEDING` damage tag on 151 ticks of an 18 s window [#3042/M/n=1].
An infected open wound's level rose at the untreated rate, 0.018090308722325733 per game hour, and with the part's alcohol level written to 1 it fell at 0.35913723562284106 per game hour [#3043/M/n=1].
Twenty writes of an extra rise, each driven over the harness bus after a read about a second earlier, reached only 1.179928563584732 times the untreated slope rather than 2.3 times; the vanilla rise that each write overwrote predicts 1.1946730180991645 (arith., inference), so the shortfall is read as the overwritten gap, not measured as its cause [#3044/M/n=1].
In a second session, with every fold of the mod idle, an unbandaged scratch counted down 0.017937586994153862 per game hour, a bleed 0.03585957751468073 and an infected scratch's level rose 0.017989861790033753 [#3113/M/n=1].
The wound-infection level is capped at 10: every branch of the update's wound-infection section reaches a check that writes `setWoundInfectionLevel(10.0)` where the level reads above 10.0, so a fold that scales the level's rise saturates there [#3131/C/C-only].

<a id="mood-surface"></a>
### The mood surface

The mood stats are registered stats with their own ranges, listed at [character-stats.md#registry](character-stats.md#registry).
Stress and the wake-state updaters run inside `calculateStats`, which any registered `CalculateStats` handler skips whatever it returns [#2238/C/C-only]; panic, boredom, pain and sickness are driven inside `BodyDamage.Update`, which that hook does not reach [#2352/C/C-only] [#2384/C/C-only].
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

The hunger, thirst, endurance and heavy-load thresholds are stated at [body-and-weight.md#moodles](body-and-weight.md#moodles) [#0508/M/n=1] [#0509/M/n=1] [#3926/C/C-only].
The comparison operator and evaluation order inside `Moodle.Update` were re-read for hunger and thirst first, and for Pain, Unhappy and Stress below; the first two levels of those three were read live at held values inside their bands, consistent with the rows above, though no run bracketed a threshold [#2369/C/C-only] [#4068/M/n=1] [#4079/M/n=1].
The SICK moodle's input was read as well: on a character whose health is not 0, `Moodle.Update` divides the apparent infection level, the largest of FOOD_SICKNESS, ZOMBIE_FEVER and ZOMBIE_INFECTION, by 100, adds SICKNESS straight onto it unscaled and passes each SICK threshold by a strict greater-than, so a FOOD_SICKNESS on its 0 to 100 scale is read against the 0 to 1 ladder as a hundredth [#3130/C/C-only].

One ladder is not monotonic [#2370/C/C-only].
The `HYPOTHERMIA` moodle's third threshold is `9.0`, below its first at `30` and its second at `70`, as shipped [#2370/C/C-only].
How `Moodle.Update` resolves a ladder in that shape is not read [#2370/C/C-only].

The thresholds cannot be retuned from Lua [#1141/C/C-only].
`MoodleStat` does not appear anywhere in the `LuaManager$Exposer.exposeAll()` class set, so a mod never reaches its public threshold setters, the wall stated at [../reference/wall-map.md#d2-d3](../reference/wall-map.md#d2-d3) [#1141/C/C-only].
A mod moves a moodle only by moving the stat behind it [#1141/C/C-only].

`Moodle.Update` recomputes the Pain moodle only once every 120 calls, through its `painTimer`, and then reads the PAIN stat against the Pain thresholds by a strict greater-than while the body's health is not 0, so a character's Pain moodle lags its PAIN by up to 120 updates. [#4065]
`Moodle.Update` reads the Unhappy moodle from UNHAPPINESS upward by a strict greater-than while the body's health is not 0. [#4066/C/C-only]
`Moodle.Update` reads the Stress moodle from `Stats.getNicotineStress`, STRESS plus NICOTINE_WITHDRAWAL clamped to STRESS's range, from the top threshold down and with no health check. [#4067/C/C-only]
Held once a game minute as floors, UNHAPPINESS 25 and 50 kept the Unhappy moodle at levels 1 and 2 and STRESS 0.3 and 0.55 the Stress moodle at levels 1 and 2 on every server tick and client frame of each arm from a settle after its write. [#4079/M/n=1]
Between minute writes on DayLength 4 UNHAPPINESS did not fall from its floor of 25 or 50, while STRESS fell from 0.3 to between 0.298178106546402 and 0.29841962456703186 and from 0.55 to between 0.5481770634651184 and 0.5494725704193115. [#4080/M/n=1]

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
Measured live, one server write of the stat from 36.43119812011719 to 36.83125686645508 moved the core to 36.63 at the next tick, the window's maximum core reading 36.63119888305664, halfway, after which the core fell to 36.577354431152344 at about 8 s [#3046/M/n=1].
At rest on the default fixture the core sat about 0.45 degrees under the set point of 37, reading 36.55016326904297 to 36.548282623291016, and a 20-game-minute squat set raised it from 36.538387298583984 to 36.663856506347656 [#3115/M/n=1].

The core the regulator steers toward is readable but not writable [#3024/C/C-only].
`Thermoregulator.getSetPoint()` is public on the exposed class and returns a private set point with no setter, which the update resets to 37 °C at its start and raises by twice the `SICKNESS` stat when that stat is above its minimum [#3024/C/C-only].
The heat-delta step scales heat loss up when the core is above the set point and heat gain up when it is below, so the set point is the regulator's target [#3024/C/C-only].
A held sickness is therefore a fever: `SICKNESS` 0.30, 0.55 and 0.90 put the target at 37.6, 38.1 and 38.8 °C while held [#3025/C/arith.].

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
Not covered: the sub-updater bodies other than panic state, boredom, cold and illness (read at [character-stats.md](character-stats.md#tick-order) and above), the thermoregulator's catch-a-cold delta, `BodyPartType.getDamageModifyer` and `getPainModifyer`, `CombatManager.applyDamage`, the `generate*` wound and fracture methods, `getGeneralWoundInfectionLevel` and `getApparentInfectionLevel`, `Kill`, `dieNetwork` and `addOnDiedListener`, the carrier of `IsoGameCharacter.health` to a client, the thermoregulator's own formulas beyond the fat, energy and fluid terms, and `ThermalNode.calculateInsulation`.

## Open
<a id="open"></a>

- Whether a mod kills through `ReduceGeneralHealth(110)` or through `setHealth(0)` is a decision: the first is the engine's own fatal move, while the second writes a separate field whose route to a client is unread [#2348/C/C-only] [#2350/C/C-only].
- Whether a healing-rate effect moves the four regeneration constants, the per-part timers, or both is a decision: the constants scale whole-body regeneration per character, and the timers are the only per-wound lever [#2354/C/C-only] [#2366/C/C-only].
- Whether a bleeding effect scales `bleedingTime` or adds bleeds is a decision the squared total forces: a multiplier on the time is felt as roughly its square [#2365/C/arith.].
- Whether a temperature effect writes `CharacterStat.TEMPERATURE` every update or accepts the halfway step of one write is a decision the lerp forces [#2373/C/C-only].
- Whether a knock-down or sleep effect can rest on `setKnockedDown` or `setAsleep` is a decision that waits on a live probe, because both are bare field writes with no state machine read behind them [#2351/C/C-only] [#2383/C/C-only].
- Whether the non-monotonic `HYPOTHERMIA` ladder matters to a mod that reads the moodle is a decision that waits on a read of `Moodle.Update` [#2370/C/C-only].
- Whether a body part's added pain survives a relog alone, apart from a server restart, is unmeasured: run x492 read the value back after a quit, a graceful restart and a rejoin together (#4075), its relog grade unmeasured, so the save at the quit and the save at the restart are not separated live. [#4113/C/inference/open]

## See also

- [character-stats.md](character-stats.md) — the stat registry, the updaters and the stat hook's place in the tick.
- [body-and-weight.md](body-and-weight.md) — the hunger and thirst moodles, their regeneration tiers and drain costs, and the thermoregulator's multipliers.
- [endurance-fatigue-sleep.md](endurance-fatigue-sleep.md) — endurance, fatigue and sleep, which share the thermoregulator's fatigue multiplier.
- [../platform/mp-model.md](../platform/mp-model.md) — the server-only side gates and the `syncBodyPart` global.
- [wire-packets.md](wire-packets.md) — the body-part packet's field mask and the player-stats packet.
- [../platform/lua-platform.md](../platform/lua-platform.md) — `OnPlayerGetDamage` and the `CalculateStats` hook.
