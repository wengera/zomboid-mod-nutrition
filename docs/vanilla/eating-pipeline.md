# Eating pipeline — food item → Stats and Nutrition

**Verified against: 42.20.4 (`b0bbce05d5`)** · 2026-09-10 · slice 01 (P1a); slice-03
corrections 2026-09-10.
Evidence grades: **C** read from bytecode/Lua/scripts, **M** measured on the live
dedicated server (run id given), **W** wiki mirror (secondary).

## Summary

1. One Java method does all of it: `IsoGameCharacter.Eat(InventoryItem,float,boolean)` moves
   hunger/thirst/endurance/stress/fatigue into `Stats` and calories/carbs/proteins/lipids into
   `Nutrition`, every one of them scaled by a single fraction `f`.
2. `f` is not the menu fraction — it is re-expressed as a share of *what is left* of the item,
   promoted to `1` when the leftover would be a crumb, and the remainder's fifteen stored fields
   are then multiplied by `(1 - f)`.
3. Item state modifies hunger (cooked ×1.3 beats burnt ÷3, stale ÷1.3, rotten ÷2.2) and thirst
   (burnt ÷5 beats cooked ÷2), but the four nutrients have **no state modifier at all**: the only
   nutrition modifier in the game is `Eat`'s ÷5 for burnt items, so rotten food gives full calories.
4. In multiplayer the whole method runs on the **server** — an MP client never runs
   `ISEatFoodAction:complete()` — and the server pushes the entire `Nutrition` object at eat time
   (`EatFoodPacket`) and again once a second (`PlayerStatsPacket`); a client-side write is
   discarded inside 3 s (measured).
5. The sandbox `Nutrition` option gates only `Nutrition.update()` (macro drain, calorie burn,
   weight); it never touches intake, so with it off the stores keep filling and nothing burns them.

---

## Model

### Glossary — the five near-identical `Food` getters

`Food` exposes several names one letter apart and the pipeline uses each for a different job.
Ev **C** throughout (jar dumps).

- **`getBaseHunger()`** (`Food.getBaseHunger()F @0 L1891`) — bare read of `Food.baseHunger`, the
  item's script/base hunger value (`HungerChange/100` at instantiation, never touched by
  `multiplyFoodValues`). Used **only** for the fraction rescale, so a fraction means "x% of the
  whole item", not "x% of what is left".
- **`getHungChange()`** (`Food.getHungChange()F @0 L1816`; `getBaseHungChange` is an alias, `@0
  L1812`) — bare read of `Food.hungChange`, the **raw remaining** hunger on this instance, no state
  modifiers. Drives the fraction rescale and both crumb rules; it is what `multiplyFoodValues`
  shrinks and what `Eat` zeroes when the item is finished.
- **`getHungerChange()`** (`Food.getHungerChange()F @L1682–L1708`) — the **state-modified** value
  (cooked ×1.3, else burnt /3.0, stale /1.3, rotten /2.2, each floored at 0.01 with the sign kept).
  This is the one that drives the `HUNGER` stat.
- **`getThirstChange()`** (`Food.getThirstChange()F @L1866–L1875`) — state-modified thirst: burnt
  /5.0 takes precedence over cooked /2.0, and rot does not touch thirst at all. Drives the `THIRST`
  stat, and its raw value also gates the second crumb rule.
- **`getThirstChangeUnmodified()`** (`Food.getThirstChangeUnmodified()F @0 L1746`) — the bare
  `thirstChange` field. It is what `multiplyFoodValues` reads (`@44`) so cooked/burnt multipliers
  are never baked into the leftover.

### The `Eat` algorithm

`zombie/characters/IsoGameCharacter.Eat(InventoryItem,float,boolean)Z`, 968 bytes. The other two
overloads are trampolines: `Eat(item,f)` → `Eat(item,f,false)` (`@3 L5721`), `Eat(item)` →
`Eat(item,1.0f)` (`@2 L5848`). Offsets below are bytecode offsets in that dump; `L…` is the
source-line label pzdis prints alongside. Ev = C throughout this block.

```java
boolean Eat(InventoryItem item, float f, boolean useUtensil) {

    if (!(item instanceof Food)) return false;                        // @1  L5741
    Food food = (Food) item;

    f = PZMath.clamp(f, 0f, 1f);                                      // @18 L5747
    float f0 = f;                                                     // @25 L5749  (weight math only)

    // fraction is re-expressed as a share of what is LEFT
    if (food.getBaseHunger() != 0f && food.getHungChange() != 0f)     // @28 L5753
        f = PZMath.clamp(food.getBaseHunger() * f / food.getHungChange(), 0f, 1f);   // @57 L5755

    // never leave a crumb (0.01 hunger unit = 1 script point)
    if (food.getHungChange() < 0f
        && food.getHungChange() * (1f - f) > -0.01f) f = 1f;          // @79  L5760
    if (food.getHungChange() == 0f && food.getThirstChange() < 0f
        && food.getThirstChange() * (1f - f) > -0.01f) f = 1f;        // @107 L5764

    // stats — each clamped by CharacterStat; HUNGER and THIRST are [0, 1]
    stats.add(THIRST,    food.getThirstChange()    * f);              // @145 L5768
    stats.add(HUNGER,    food.getHungerChange()    * f);              // @163 L5769
    stats.add(ENDURANCE, food.getEnduranceChange() * f);              // @181 L5770
    stats.add(STRESS,    food.getStressChange()    * f);              // @199 L5771
    stats.add(FATIGUE,   food.getFatigueChange()   * f);              // @217 L5772

    // nutrition — players only; burnt costs 80 %
    IsoPlayer p = Type.tryCastTo(this, IsoPlayer.class);               // @235 L5774
    if (p != null && !food.isBurnt()) {                                // @246 L5776
        Nutrition n = p.getNutrition();
        n.setCalories     (n.getCalories()      + food.getCalories()      * f);        // @281 L5778
        n.setCarbohydrates(n.getCarbohydrates() + food.getCarbohydrates() * f);        // @299 L5779
        n.setProteins     (n.getProteins()      + food.getProteins()      * f);        // @317 L5780
        n.setLipids       (n.getLipids()        + food.getLipids()        * f);        // @335 L5781
    } else if (p != null && food.isBurnt()) {                          // @341 L5783
        Nutrition n = p.getNutrition();
        n.setCalories     (n.getCalories()      + food.getCalories()      * f / 5.0f); // @380 L5784
        n.setCarbohydrates(n.getCarbohydrates() + food.getCarbohydrates() * f / 5.0f); // @402 L5785
        n.setProteins     (n.getProteins()      + food.getProteins()      * f / 5.0f); // @424 L5786
        n.setLipids       (n.getLipids()        + food.getLipids()        * f / 5.0f); // @446 L5787
    }

    bodyDamage.setPainReduction(bodyDamage.getPainReduction() + food.getPainReduction() * f);  // @449 L5789
    bodyDamage.setColdReduction(bodyDamage.getColdReduction() + food.getFluReduction()  * f);  // @471 L5790

    // food-sickness cure, gated by the edible-buff cooldown
    if (stats.isAboveMinimum(FOOD_SICKNESS) && food.getFoodSicknessChange() < 0
        && effectiveEdibleBuffTimer <= 0f) {                           // @494 L5791
        float a = Math.abs(food.getFoodSicknessChange()) * f;          // @524 L5792
        stats.remove(FOOD_SICKNESS, a);                                // @537 L5793
        stats.remove(POISON,        a);                                // @550 L5794
        effectiveEdibleBuffTimer = Rand.Next(ironGut  ?  80f : weakStomach ? 200f : 120f,
                                             ironGut  ? 150f : weakStomach ? 280f : 230f);  // @563–@633 L5795–L5800
    }

    bodyDamage.JustAteFood(food, f, useUtensil);                       // @634 L5803  (the ONLY use of useUtensil)

    if (GameServer.server && this instanceof IsoPlayer) {               // @645 L5805
        INetworkPacket.send(SyncPlayerStats, this,
                            bits(THIRST|HUNGER|ENDURANCE|STRESS|FATIGUE|PAIN));  // @658 L5806
        GameServer.sendSyncPlayerFields((IsoPlayer) this, 8);          // @723 L5807
        INetworkPacket.send(EatFood, this, food, Float.valueOf(f));    // @732 L5808
    }

    if (food.getOnEat() != null) {                                     // @762 L5811
        Object fn = LuaManager.getFunctionObject(food.getOnEat());
        if (fn != null) LuaManager.caller.pcallvoid(LuaManager.thread, fn,
                            item, this, BoxedStaticValues.toDouble(f));            // @785 L5814
    }

    if (f == 1.0f) {                                                   // @803 L5819
        food.setHungChange(0f); food.UseAndSync();                     // @809–@815 L5820–L5821
    } else {
        float oldHung = food.getHungChange(), oldThirst = food.getThirstChange();  // @823–@830 L5823
        food.multiplyFoodValues(1.0f - f);                             // @837 L5825
        if (oldHung == 0f && oldThirst < 0f && food.getThirstChange() > -0.01f) {   // @845 L5826
            food.setHungChange(0f); food.UseAndSync(); return true;     // @871–@882 L5827–L5829
        }
        if (food.isCustomWeight()) {                                   // @887 L5833
            float base = replaceOnUseItem == null ? 0f : replaceOnUseItem.getActualWeight();  // @926 L5837
            float w = food.getWeight();
            food.setWeight((w - base) - f0 * (w - base) + base);        // @933 L5839  — note f0, not f
        }
    }
    food.syncItemFields();                                             // @961 L5841
    return true;                                                       // @966 L5843
}
```

**Scale note.** `Item.InstanceItem` divides the script's `HungerChange` / `ThirstChange` /
`EnduranceChange` by **100** before storing them (`zombie/scripting/objects/Item.InstanceItem(String,boolean)
@546–@595`), because `CharacterStat.HUNGER`/`THIRST` are registered `min 0, max 1`
(`zombie/characters/CharacterStat.<clinit> @91–@99`, `@231–@239`). `Calories`, `Carbohydrates`,
`Lipids` and `Proteins` are **not** rescaled (`Item.InstanceItem @745–@781`). So `Base.Apple`
(`media/scripts/generated/items/food.txt:8658`) carries `hungChange = -0.16`,
`thirstChange = -0.07`, `calories = 95.0`, `carbohydrates = 25.13` — confirmed live, script
`HungerChange = -16` ↔ item `hungChange = -0.16` (M, run `exp01-20260910-003929`). Ev C+M.

**Ordering that matters.** Nutrition is written *before* the item is consumed and *before* the
`OnEat` hook fires, so a hook sees the post-intake `Nutrition` and the pre-consume item.
`Nutrition` is **player-only**: `Type.tryCastTo(this, IsoPlayer.class)` — an `IsoAnimal` or NPC
gets stats, pain, cold and sickness but no nutrient write (`Eat @235–@251 L5774–L5776`, C).

### Every modifier, in one table

| Modifier | Applies to | Effect (with constant) | Source | Ev |
|---|---|---|---|---|
| argument clamp | fraction `f` | `f = PZMath.clamp(f, 0, 1)` | `IsoGameCharacter.Eat @18 L5747` | C |
| baseHunger rescale | fraction `f` | `f = clamp01(baseHunger * f / hungChange)` when both ≠ 0 | `Eat @28–@78 L5753–L5757`; half-eaten apple at fraction 1.0 gave +47.5 kcal, not +95 | C+M `exp01-20260910-000351` |
| hunger crumb rule | fraction `f` | `f = 1` if `hungChange < 0 && hungChange*(1-f) > -0.01` | `Eat @79–@106 L5760–L5761` | C |
| thirst crumb rule | fraction `f` | `f = 1` if `hungChange == 0 && thirstChange < 0 && thirstChange*(1-f) > -0.01` | `Eat @107–@144 L5764–L5765` | C |
| fraction scaling | THIRST, HUNGER, ENDURANCE, STRESS, FATIGUE | each `stats.add(stat, getter() * f)` | `Eat @145/@163/@181/@199/@217 L5768–L5772`; apple at f = 0.25 gave dHunger −0.04, dThirst −0.0175 | C+M `exp01-20260910-003929` |
| fraction scaling | calories, carbs, proteins, lipids | `nutrition.setX(getX() + itemX * f)` | `Eat @246–@338 L5776–L5782`; apple 1.0/0.5/0.25 → 95 / 47.5 / 23.75 kcal, exact on all six numeric fields | C+M `exp01-20260910-003929` |
| **burnt (intake)** | the four nutrients | `+ itemX * f / 5.0` instead | `Eat @341–@446 L5783–L5787`; measured 4× — apple 95→19, steak 220→44, bread 532→106.4, carrots 25→5 | C+M `exp01-20260910-003929` |
| non-player guard | the four nutrients | skipped entirely when `Type.tryCastTo(IsoPlayer)` is null | `Eat @235–@251 L5774–L5776` | C |
| stat clamp | HUNGER, THIRST | `PZMath.clamp(v, 0, 1)` — **overshoot silently discarded** | `Stats.set @6`; `CharacterStat.clamp @0 L70`; `CharacterStat.<clinit> @91/@231`; satiated character kept all 532 kcal of rotten bread and ~0 of its hunger relief | C+M `exp01-20260910-000351` |
| store clamp | calories | `[-2200, 3700]` | `Nutrition.setCalories @1 L321, @12 L324`; `set 9999` → 3700.000, `set -9999` → −2200.000 | C+M `exp01-20260910-003929` |
| store clamp | carbs / proteins / lipids | `[-500, 1000]` each | `Nutrition.setCarbohydrates/setProteins/setLipids @1/@12`; all three clamped exactly, both signs | C+M `exp01-20260910-003929` |
| fraction scaling | painReduction, coldReduction | `+= getPainReduction()*f`, `+= getFluReduction()*f` | `Eat @449 L5789`, `@471 L5790` | C |
| food-sickness cure | FOOD_SICKNESS, POISON | `-= abs(foodSicknessChange) * f` each, gated by `stat above min && change < 0 && effectiveEdibleBuffTimer <= 0` | `Eat @494–@562 L5791–L5794` | C |
| Iron Gut (buff timer) | `effectiveEdibleBuffTimer` | `Rand.Next(80, 150)` | `Eat @576–@586 L5796` | C |
| Weak Stomach (buff timer) | `effectiveEdibleBuffTimer` | `Rand.Next(200, 280)` | `Eat @605–@615 L5798` | C |
| no trait (buff timer) | `effectiveEdibleBuffTimer` | `Rand.Next(120, 230)` | `Eat @621–@631 L5800` | C |
| **cooked** | `getHungerChange` | `× 1.3` — **takes precedence over burnt and rot** | `Food.getHungerChange @11–@23 L1686-L1687`; apple −0.16 → −0.208 | C+M `exp01-20260910-003929` |
| **burnt** | `getHungerChange` | `max(abs(h)/3.0, 0.01) × sign(h)` | `Food.getHungerChange @42–@62 L1697-L1698`; apple → −0.0533 | C+M `exp01-20260910-003929` |
| **stale** (`offAge ≤ age < offAgeMax`) | `getHungerChange` | `max(abs(h)/1.3, 0.01) × sign(h)` | `Food.getHungerChange @63–@102 L1700-L1701` | C |
| **rotten** (`age ≥ offAgeMax`) | `getHungerChange` | `max(abs(h)/2.2, 0.01) × sign(h)` | `Food.getHungerChange @103–@129 L1703-L1704`; apple → −0.0727 | C+M `exp01-20260910-003929` |
| **burnt** | `getThirstChange` | `/ 5.0` — **takes precedence over cooked** (opposite order to hunger) | `Food.getThirstChange @5–@17 L1868-L1869`; apple −0.07 → −0.014, HotDrink −0.20 → −0.04 | C+M `exp01-20260910-003929` |
| **cooked** | `getThirstChange` | `/ 2.0` | `Food.getThirstChange @18–@28 L1871-L1872`; apple → −0.035, HotDrink → −0.10 | C+M `exp01-20260910-003929` |
| **rotten** | `getThirstChange` | none — rot does not touch thirst | `Food.getThirstChange @0–@28 L1866–L1875`; rotten apple still −0.07, rotten HotDrink still −0.20 | C+M `exp01-20260910-003929` |
| *(none)* | `getCalories/Carbohydrates/Lipids/Proteins` | bare `getfield` — **no cooked/burnt/rotten/frozen modifier exists** | `Food.getCalories @0 L2139` (+ L2115/L2123/L2131); cooked, rotten and frozen rows all delivered full values (rotten bread 532 kcal / 99 g carbs) | C+M `exp01-20260910-003929` |
| frozen | intake (all six numbers) | no-op — frozen moves boredom/unhappiness only | `Food.getHungerChange`/`getThirstChange`/`getCalories` carry no frozen branch; all five items measured identical fresh vs frozen | C+M `exp01-20260910-003929` |
| burnt / stale / cooked | `getEnduranceChange` | `/3` · `/2` · `×2` | `Food.getEnduranceChange @0–@67 L1605–L1615` | C |
| burnt / stale / rotten / cooked | `getStressChange` | `/4` · `/1.3` · `/2` · `×1.3` | `Food.getStressChange @12–@103 L1717–L1730` | C |
| burnt / stale / rotten / cooked | `getFoodSicknessChange` | `/3` · `/1.3` · `/2.2` · `×1.3` (int truncation) | `Food.getFoodSicknessChange @0–@103 L2078–L2090` | C |
| frozen | `getBoredomChange`, `getUnhappyChange` | `+30` each, unless `type == "Icecream"` or tag `GOOD_FROZEN` | `Food.getBoredomChange @43–@59 L1663-L1664`; `getUnhappyChange @43–@59 L1631-L1632` | C |
| burnt / stale / rotten | `getBoredomChange`, `getUnhappyChange` | `+20` · `+10` · `+20` each | `Food.getBoredomChange @60–@123 L1666–L1675` | C |
| badCold / goodHot | `getUnhappyChange` | `+2` if `isBadCold && isCookable && isCooked && heat < 1.3`; `-2` if `isGoodHot && isCookable && isCooked && heat > 1.3` | `Food.getUnhappyChange @124–@195 L1645–L1649` | C |
| fertilized | boredom / unhappy / stress | all modifiers bypassed, raw field returned; `isRotten()` also forced false | `Food.getBoredomChange @5`, `getUnhappyChange @5`, `getStressChange @0`, `isRotten @0 L1832` | C |
| **RemoveNegativeEffectOnCooked** | item fields `thirstChange`, `unhappyChange`, `boredomChange` | on the cook transition each is set to 0 **if positive**; permanent, one-shot; nutrition untouched | `Food.update @578–@626 L451–L459` (cook block starts `@413 L423`) | C |
| removeUnhappinessWhenCooked | item field `unhappyChange` | set to 0 on the cook transition | `Food.update @418–@432 L424-L425` | C |
| **useUtensil** | BOREDOM | `× 1.25` if `boredomChange*f < 0`, else `× 0.75` | `BodyDamage.JustAteFood(Food,float,boolean) @322–@379 L624–L633` | C |
| **useUtensil** | UNHAPPINESS | `× 1.25` if `unhappyChange*f < 0`, else `× 0.75` | `JustAteFood @383–@440 L636–L644` | C |
| **useUtensil** | eating duration | `eatingLoop -= 1` when `eatingLoop ≥ 2` (undone for drink-type items at `:232`) | `media/lua/shared/TimedActions/ISEatFoodAction.lua:224–229` | C |
| poison power | POISON, PAIN | `POISON += poisonPower*f` (Iron Gut `/2` unless type `Bleach`; Weak Stomach `×2`); `PAIN += poisonPower*f/6` | `JustAteFood @0–@101 L587–L598` | C |
| tainted | POISON, PAIN | `POISON += 20.0*f`; `PAIN += 10.0*f/6` | `JustAteFood @177–@223 L607–L610` | C |
| rot sickness roll | POISON | chance % = `clamp(age-offAgeMax,1,5)/(offAgeMax-offAge)*100` (100 if `offAgeMax ≤ offAge`), Iron Gut `/2`, Weak Stomach `×2`, skipped if already infected; hit → `+5*abs(hungChange*10)*f`, miss → `+2*abs(hungChange*10)*f` | `JustAteFood @677–@953 L703–L743` | C |
| dangerous uncooked | POISON, healthFromFoodTimer | `healthFromFoodTimer = 0`; chance 75 (5 with tag `EGG`), Iron Gut `/2` (0 for eggs), Weak Stomach `×2`; on hit, not infected, not burnt → `POISON += 15.0*f` | `JustAteFood @555–@676 L669–L696` | C |
| hunger-at-zero health tick | healthFromFoodTimer | when HUNGER is at minimum: `+= abs(getHungerChange())*f*getHealthFromFoodTimeByHunger()`, doubled if `isCooked()`, capped at `11000.0` | `JustAteFood @454–@538 L650–L660` | C |
| alcoholic | intoxication | `isAlcoholic()` → `JustDrankBooze(food, f)` | `JustAteFood @441–@453 L646-L647` | C |
| Tutorial game mode | everything after mood | early `return` before the sickness rolls | `JustAteFood @539–@554 L664-L665` | C |
| **leftover scaling** | 15 item fields incl. calories/carbs/proteins/lipids | `multiplyFoodValues(1 - f)`; `fluReduction`, `foodSicknessChange`, `poisonPower` truncate to int | `Eat @837–@844 L5825`; `Food.multiplyFoodValues @0–@153 L2288–L2302`; half-eaten apple left at `calories 47.5`, `hungChange −0.08` | C+M `exp01-20260910-000351` |
| full-consume | item | `f == 1.0f` → `setHungChange(0)` + `UseAndSync()` | `Eat @803–@820 L5819–L5821`; every `fraction 1.0` row consumed its item | C+M `exp01-20260910-000351` |
| post-partial crumb sweep | item | `oldHung == 0 && oldThirst < 0 && newThirst > -0.01` → `setHungChange(0)` + `UseAndSync()` | `Eat @845–@883 L5826–L5829` | C |
| custom weight | item weight | `w' = (w - base) - f0*(w - base) + base`, `base` = the `replaceOnUse` item's actual weight; **uses the pre-rescale `f0`** | `Eat @884–@960 L5832–L5839` | C |
| *(none)* | `Nutrition.weight` | `Eat` never writes weight — only `updateWeight()` does | the `Nutrition` block of `Eat` (`@246–@446 L5776–L5787`) writes the four nutrient setters and nothing else; `dWeight = 0.0000` on all 27 matrix rows | C+M `exp01-20260910-003929` |
| `setCooked` / `setBurnt` | item state | the flags stick on an `IsCookable = false` item and the modifiers then apply in full (uncookable bread flagged cooked gave ×1.3 hunger; flagged burnt gave ÷5 calories) | matrix rows `Base.Bread` cooked/burnt, `Base.Apple` cooked/burnt | M `exp01-20260910-003929` |
| `setRotten(true)` | item state | does **not** stick; the working route is `setAge(getOffAgeMax() + 1)` | smoke probe: `isRotten()` still false after `setRotten(true)`; age route gave `rotten: true, age 7` on `Base.Bread` | M `exp01-20260910-000351` |
| script→stat scale | HungerChange / ThirstChange / EnduranceChange | `/100` at instantiation; Calories/Carbs/Lipids/Proteins **not** scaled | `Item.InstanceItem @546–@595`, `@745–@781`; script `HungerChange -16` ↔ item `hungChange -0.16` | C+M `exp01-20260910-003929` |
| **fluid path** | calories, carbs, proteins, lipids | `nutrition.setX(getX() + props.getX()*f)` from `SealedFluidProperties`, applied **before** any fluid is removed; **no burnt divisor, no other modifier** | `IsoGameCharacter.DrinkFluid(FluidContainer,float,boolean) @11–@100 L5876–L5881` | C |
| **fluid path** | THIRST, HUNGER, ENDURANCE, STRESS, FATIGUE, BOREDOM, UNHAPPINESS | taken from the `FluidConsume` returned by `removeFluid(amount*f, true)` and **not** re-multiplied by `f` | `DrinkFluid @129–@253 L5885–L5894` | C |
| **fluid path** | POISON | `p = fc.getPoison()`; tainted `×0.75`; Iron Gut → 0 if tainted else `/2` unless primary fluid is `FluidType.Bleach`; Weak Stomach `×1.2` if tainted else `×2` | `DrinkFluid @349–@451 L5906–L5924` | C |
| sandbox `Nutrition = false` | macro drain, `updateCalories`, `updateWeight` | all three skipped by one early return; **`Eat`/`DrinkFluid` stores unaffected** | `Nutrition.update @0–@12 L65-L66` — the only runtime read of the option in the jar | C |
| `SystemDisabler.doCharacterStats` | `Nutrition.update` | not called at all when false | `IsoPlayer.updateInternal2 @392–@402 L2306-L2307` | C |
| MP client | macro drain + `updateCalories` | skipped when `GameClient.client`; `updateWeight()` is still *reached*, but it **computes the weight delta and discards it** — a `GameClient.client` skip sits before `setWeight` | `Nutrition.update @42 L75`, `@106 L81`; `updateWeight @317–@320 L198` before `@323 L199` | C+M `exp03-20260910-045523` |
| passive drain | carbs / lipids / proteins | `−0.0035` / `−0.00113` / `−0.00086` per game-world second | `Nutrition.update @48/@66/@84 L76–L78`; control window −34.4194 g carbs over +2.7583 game-h = 0.00347/game-s (99.0 % of the coded rate) | C+M `exp01-20260910-003929` |
| passive burn | calories | `−0.13×mod×weightRatio` running/sprinting (`mod` 1.0 / 1.3), `−0.13×0.6×…` walking, `−0.003×…` asleep, `−0.016×…` idle; `weightRatio = weight/80`; `mod` = 8.0 while swiping/climbing, else the action's `caloriesModifier` | `Nutrition.updateCalories @0–@318 L88–L118`; idle at `settimespeed 1` measured 0.259 kcal/s (0.256 in the earlier run) | C+M `exp01-20260910-003929` |
| eating duration | `maxTime` | `232 × eatingLoop` (food) or `171 × eatingLoop` (drink); loop 1/2/3 at hungerConsumed ≥30/≥80 (food) or thirst ≥3/≥6 (drink) | `ISEatFoodAction.lua:214–243`; whole fresh apple measured `maxTime 232.24` | C+M `exp01-20260910-003929` |
| zero-hunger item | `maxTime` | `460` | `ISEatFoodAction.lua:246` | C |
| `EatTime` script field | `maxTime` | hard override when `> 0` | `ISEatFoodAction.lua:247` | C |
| `EatType == "popcan"` | `maxTime` | `160` | `ISEatFoodAction.lua:250–252` | C |
| moodles / pain / temperature | `maxTime` | `× (1 + UNHAPPY/4) × (1 + DRUNK/4) × (1 + handPain/300) × getTimedActionTimeModifier()`; hand pain skipped because `ignoreHandsWounds = true` | `media/lua/shared/TimedActions/ISBaseTimedAction.lua:99–122`; `ISEatFoodAction.lua:325` | C |
| instant-action cheat | `maxTime` | `return 1` | `ISEatFoodAction.lua:204–206` | C |
| FOOD_EATEN moodle | the whole action | `isValidStart` false at moodle level ≥ 3; the menu shows "can't eat more" | `ISEatFoodAction.lua:14`; `media/lua/client/ISUI/ISInventoryPaneContextMenu.lua:500–504` | C |

### Partial eating

Menu fractions are 1 / 0.5 / 0.25 (`ISInventoryPaneContextMenu.lua:508`, `:513`, `:516`), Half
offered only when `abs(hungerChange*100) ≥ 2` and `≥ baseHunger/2`, Quarter when `≥ 4` and
`≥ baseHunger/4` (`:510–:516`). Ev C.

```
f_arg = clamp01(f_menu)
if baseHunger != 0 and hungChange != 0:
    f = clamp01(baseHunger * f_arg / hungChange)     # share of what is LEFT
```

`baseHunger` is initialised **equal to** `hungChange` at instantiation
(`Item.InstanceItem @572–@582`) and is deliberately **not** scaled by `multiplyFoodValues`, so it
stays at the full-portion value while `hungChange` shrinks (C). Consequence: "eat a quarter" of an
already-half-eaten apple asks for a quarter of the *original* apple = half of the remainder, so
`f = 0.5`. Measured: the leftover half-apple eaten at `fraction 1.0` delivered **+47.5 kcal**, not
+95 (M, `exp01-20260910-000351`). The same arithmetic is duplicated in Lua for the tooltip
(`ISInventoryPaneContextMenu.lua:2062–2070`) and the utensil-scrape sound
(`ISEatFoodAction.lua:279–284`).

The remainder is scaled by `multiplyFoodValues(1 - f)`, which multiplies **fifteen** stored fields:
`boredomChange, unhappyChange, hungChange, fluReduction (int), thirstChange, painReduction,
foodSicknessChange (int), endChange, stressChange, fatigueChange, calories, carbohydrates, proteins,
lipids, poisonPower (int)` (`Food.multiplyFoodValues @0–@153 L2288–L2302`, C). It feeds itself the
*unmodified* getters where they exist, so cooked/rotten multipliers are never baked in; the three
`int` fields truncate toward zero, so `fluReduction`, `foodSicknessChange` and `poisonPower` erode
faster than linearly on small items (C). Measured: half an apple leaves `calories 47.5`,
`hungChange −0.08` (M, `exp01-20260910-000351`).

**Crumb rules.** Steps at `@79` and `@107` promote `f` to `1.0` when the leftover would be smaller
than `0.01` hunger units (one script point), and `@845` re-checks the same thing for drink-type
food after the multiply — you can never leave a half-point sliver (C).

### Drinks

Two paths that share no code (C):

- **Food-type drinks** — a `Food` item with `ThirstChange` — go through `Eat` exactly like solid
  food. `CustomMenuOption = Drink` changes only the animation (`ISEatFoodAction.lua:118–121`) and
  the duration formula (`:232–241`). Thirst is the `stats.add(THIRST, …)` step, calories and macros
  are the `Nutrition` step, and **both are scaled by the same `f`** — thirst and nutrition are
  coupled. Measured on `Base.HotDrink` (`ThirstChange = -20`, no macros): dThirst −0.20 fresh,
  −0.10 cooked, −0.04 burnt, −0.20 rotten/frozen, zero nutrition throughout
  (M, `exp01-20260910-003929`).
- **`DrinkFluid`** — the B42 fluid-container path — writes nutrition from
  `FluidContainer.getProperties()` **first**, before any fluid is removed, with no burnt divisor;
  then takes every stat delta from the `FluidConsume` returned by `removeFluid(amount*f, true)`
  without re-applying `f`. It has **no** `PZMath.clamp` on the fraction, no `baseHunger` rescale, no
  crumb rules, no `OnEat` hook, no `JustAteFood` and no `EatFood` packet; its `boolean` third
  argument is never read (no utensil effect on drinking). Its Lua driver
  `media/lua/shared/TimedActions/ISDrinkFluidAction.lua` calls it **incrementally** during the
  action (`updateEat`, `:109–120`), consuming only the difference between the target ratio and what
  is already gone, so the call is idempotent; `update()` calls it when `not isClient()` (`:26–29`)
  and `animEvent` when `isServer()` (`:42–48`). Ev C — the fluid path was **not** exercised on the
  live server in this slice.

### The sandbox `Nutrition` option

`SandboxOptions.<init> @1080–@1089 L132` — `this.nutrition = newBooleanOption("Nutrition", false)`.
The Java default is `false`; every shipped preset sets it true (`media/lua/shared/Sandbox/Apocalypse.lua:64`,
`Extinction.lua:64`, `Outbreak.lua:64`, `Rising.lua:64`, `SixMonthsLater.lua:39`). The test fixture
reads `Nutrition = true` (M, `exp01-20260910-003929`).

A whole-jar scan for reads of `SandboxOptions.nutrition` returns exactly two sites: the constructor
that creates it, and `Nutrition.update()` @3 (C).

```java
void Nutrition.update() {
    if (!SandboxOptions.instance.nutrition.getValue()) return;   // @0–@12  L65-L66
    if (parent == null || parent.isDead())            return;    // @13–@30 L68-L69
    if (parent.isGodMod())                            return;    // @31–@41 L71-L72
    if (!GameClient.client) {                                    // @42     L75
        setCarbohydrates(getCarbohydrates() - 0.0035f  * gameWorldSecondsSinceLastUpdate);
        setLipids       (getLipids()        - 0.00113f * …);
        setProteins     (getProteins()      - 0.00086f * …);
        updateCalories();                                        // @102    L79
    }
    updateWeight();                                              // @106    L81
}
```

**So the option gates only `Nutrition.update()` — drain, calorie burn and weight — and never
intake** (C). `Eat` and `DrinkFluid` carry no sandbox guard anywhere on the store-writing path.
With `Nutrition = false` the stores keep filling (clamped at 3700 / 1000), nothing burns them off,
and weight freezes; save/load and the MP packets still carry the values
(`Nutrition.save/load @0 L209/L217`). A runtime flip through `getSandboxOptions():set(name, value)`
works and reads back in both directions (M, `exp01-20260910-003929`) — but see **Open questions**
for what that flip did and did not establish, and note that `SandboxVars.Nutrition`, the Lua mirror
table, stays stale after such a flip (M, same run).

### `OnEat`, `EatType`, `Eattime`

| Field | Where it is read | What it does | Ev |
|---|---|---|---|
| `OnEat` | `Eat @762–@802 L5811–L5814` | `fn(item, character, fraction)` via `LuaCaller.pcallvoid`, fired **after** every stat/nutrition/mood write and **before** the item is consumed; `fraction` is the **rescaled** `f`, not the menu percentage; the return value is ignored. A hook can still mutate `hungChange`/`calories` and have `multiplyFoodValues` operate on the mutated values | C |
| `OnEat` (packet twin) | `IsoGameCharacter.EatOnClient @0–@57 L5725–L5736` | type-check → the identical `OnEat` call → `return true`. **No stats, no nutrition** — it exists so the packet receiver can run mod hooks without double-applying effects | C |
| `EatType` | no Java consumer (jar-wide scan finds only script generators) | presentational plus one timing rule: picks the animation `FoodType` and the second-hand utensil model (`ISEatFoodAction.lua:73–110`), `"Pot"`/`"PotForged"` hand overrides (`:112–114`), the canned-scrape sound (`:42–48`), which types auto-pick a utensil at all — `2handbowl` returns the spoon on its own early-return branch (`:259–261`), while `Can`, `Candrink`, `2hand` and `Plate` take the fork-or-spoon branch (`:264–265`); both feed `useUtensil` at `:313–315` — and `"popcan"` → `maxTime = 160` (`:250–252`). It never touches hunger, thirst or nutrition | C |
| `Eattime` (script) / `getEatTime()` | no Java consumer | one Lua use, `ISEatFoodAction.lua:247`: a hard override of the computed duration. Duration only; no effect on what is absorbed. The script-parser spelling is `Eattime` | C |

### Eating time — and why slice 04 must not depend on it

```lua
-- media/lua/shared/TimedActions/ISEatFoodAction.lua:203–254
if character:isTimedActionInstant() then return 1 end                      -- :204-206

-- DEAD CODE: computed at :208–212, then unconditionally overwritten at :243
local maxTime = math.abs(item:getBaseHunger() * 150 * percentage) * 8

hungerConsumed = math.abs(item:getBaseHunger() * percentage * 100)         -- :214
eatingLoop = 1
if hungerConsumed >= 30 then eatingLoop = 2 end                            -- :216-218
if hungerConsumed >= 80 then eatingLoop = 3 end                            -- :219-221
if useUtensil and eatingLoop >= 2 then eatingLoop = eatingLoop - 1 end     -- :224-229

timerForOne = 232                                                          -- :231
if item:getCustomMenuOption() == getText("ContextMenu_Drink") then         -- :232
    hungerConsumed = math.abs(item:getThirstChange() * percentage * 100)   -- :233
    timerForOne = 171                                                      -- :234
    if hungerConsumed >= 3 then eatingLoop = 2 end                         -- :235-237
    if hungerConsumed >= 6 then eatingLoop = 3 end                         -- :238-240
end

maxTime = timerForOne * eatingLoop                                         -- :243
if hungerConsumed == 0 then maxTime = 460 end                              -- :246
if item:getEatTime() and item:getEatTime() > 0 then maxTime = item:getEatTime() end  -- :247
if item:getEatType() == "popcan" then maxTime = 160 end                    -- :250-252
```

Real results: **232 / 464 / 696** ticks for food, **171 / 342 / 513** for drink, **460** for
zero-hunger items (cigarettes), or an `EatTime` / `popcan`-160 override; then
`ISBaseTimedAction:adjustMaxTime` multiplies by `(1 + UNHAPPY/4) × (1 + DRUNK/4) × (1 + handPain/300)
× getTimedActionTimeModifier()` (`ISBaseTimedAction.lua:99–122`, hand pain skipped here because
`ignoreHandsWounds = true`). Lines `:208–212` are computed and discarded. The drink branch at `:232`
reassigns `eatingLoop`, which **undoes** the utensil reduction for drink-type items. Ev C.

Measured: a whole fresh apple reported `maxTime 232.24` — `timerForOne 232 × eatingLoop 1` times a
body-temperature modifier of ≈1.001 — and the intake landed on the client **5.5 s** after queuing
(M, both runs). Those 232 ticks were therefore consumed in at most 5.5 s — part of which is the
server→client push — so ≥42 ticks per wall-second, consistent with a per-frame budget rather than a
game-clock interval; **no accelerated (`settimespeed > 1`) `eat.action` run exists**, so the scaling
behaviour is an open question. The practical consequence is unaffected either way: the 3-day scenario drives
`Nutrition` directly on the server rather than through timed eats (see below).

---

## Code map

```
menu:  ISInventoryPaneContextMenu.onEatItems(:3782) -> eatItem(:3584)
         -> ISTimedActionQueue.add(ISEatFoodAction:new(character, item, percentage))   (:3639)

SP:    LuaTimedActionNew.complete()  --(GameClient.client == false)-->  ISEatFoodAction:complete() (:174)
                                                                          -> character:Eat(item, percentage, useUtensil)

MP:    client LuaTimedActionNew.start() @60 L127  -> ActionManager.createNetTimedAction -> NetTimedActionPacket
       server ActionManager.update() @0 L66 (server-gated) -> @72 L70 action.perform()
              NetTimedAction.perform() @0–@27 L140 -> ISEatFoodAction:complete() (:174) -> IsoGameCharacter.Eat
       cancel: client LuaTimedActionNew.stop() @70 L143 -> ActionManager.remove(id,true) -> GeneralActionPacket.setReject
              server GeneralActionPacket.processServer @29 L41 -> ActionManager.stop -> NetTimedAction.stop() @0–@53 L114
                     -> ISEatFoodAction:serverStop() (:141–153) -> :eat(item, netAction:getProgress()) (:151) -> Eat

Eat -> Food getters (getHungerChange/getThirstChange/getCalories/…)
    -> Stats.add(CharacterStat.*)              [HUNGER, THIRST clamped 0..1]
    -> Nutrition.setCalories/setCarbohydrates/setProteins/setLipids   [clamped]
    -> BodyDamage.setPainReduction / setColdReduction / JustAteFood
    -> (server only) SyncPlayerStats + GameServer.sendSyncPlayerFields + EatFoodPacket
    -> OnEat lua hook
    -> Food.multiplyFoodValues(1-f) | UseAndSync ; Food.syncItemFields
```

| Element | Where | Note | Ev |
|---|---|---|---|
| `IsoGameCharacter.Eat(InventoryItem,float,boolean)Z` | jar | the whole pipeline; two trampoline overloads | C |
| `IsoGameCharacter.EatOnClient(InventoryItem,float)Z` | jar `@0–@57 L5725–L5736` | hook-only twin used by the packet receiver | C |
| `IsoGameCharacter.DrinkFluid(FluidContainer,float,boolean)Z` | jar `L5873–L5940` | the fluid path; four overloads funnel here | C |
| `Food.getHungerChange/getThirstChange` | jar | the only state-modified intake getters | C+M `exp01-20260910-003929` |
| `Food.getCalories/getCarbohydrates/getLipids/getProteins` | jar `@0 L2139/L2115/L2123/L2131` | bare `getfield`, no modifiers | C+M `exp01-20260910-003929` |
| `Nutrition.setCalories/…` | jar `@1/@12` | the clamping store setters | C+M `exp01-20260910-003929` |
| `Nutrition.update/updateCalories/updateWeight` | jar `L65–L138` | drain, burn, weight; sandbox-gated; `updateWeight` is *called* on both sides but only the server's call writes (`@317–@320 L198`) — the full burn model is [body-stats.md](body-stats.md) | C |
| `ISEatFoodAction` | `media/lua/shared/TimedActions/ISEatFoodAction.lua` | `:174` complete → `Eat`; `:199` partial eat; `:168` the `perform` call is commented out; `:136` `not isClient() and not isServer()` makes SP call `serverStop` itself | C |
| `ISDrinkFluidAction` | `media/lua/shared/TimedActions/ISDrinkFluidAction.lua` | incremental `DrinkFluid`; `:26–29` non-client, `:40–46` server | C |
| `LuaTimedActionNew.complete()` | jar `@31 L162` | `if (GameClient.client) skip` — the gate that moves `Eat` to the server | C |
| `ActionManager` / `NetTimedAction` | jar `L66/L70/L140/L114` | the server-side driver of a mirrored timed action | C |
| `EatFoodPacket` | `zombie/network/packets/actions/EatFoodPacket` | `write` embeds `Nutrition.save`; `parse` calls `Nutrition.load` (overwrites the receiver's whole Nutrition); `processClient`/`processServer` both only call `EatOnClient` | C |
| `PlayerStatsPacket` | jar `write @19–@33 L34`, `parse @31–@45 L48` | embeds `Nutrition.save`/`load`; sent by `NetworkPlayerAI.syncStats` on a 1000 ms `UpdateLimit` | C |
| `GameClient.eatFood(IsoPlayer,Food,float)` | jar `@0–@49 L2041–L2047` | builds and sends `EatFoodPacket` client→server — **no callers anywhere in the jar or `media/lua`** | C |
| hunger/thirst read | `getStats():get(CharacterStat.HUNGER / .THIRST)` | **C** — `zombie/characters/Stats` has no `getHunger`/`getThirst` at all: its complete method list is 34 entries and the only stat accessors in it are `get/set/add/remove/reset/isAtMinimum/isAtMaximum/isAboveMinimum(CharacterStat)` (`./pz.sh methods zombie/characters/Stats`, read 2026-09-10). **M** — the enum route is the one every live snapshot answered with (`statsApi: "Stats:get(CharacterStat.HUNGER)"` on every row). Note the measurement's reach: `TK.nutritionSnapshot` tries the enum first and short-circuits (`testing/PZTestKit/.../PZTestKit_Core.lua:120–131`), so the `getHunger()` and `.hunger` fallbacks never ran — the run proves the enum route works; the method list is what rules the old getter out | C+M `exp01-20260910-000351` |
| script-level `Calories`/`Carbohydrates`/`Lipids`/`Proteins` | `getScriptManager():getItem(type)` | **not reachable from Lua** — public fields on `Item` with no getter; all four keys came back absent through `get<X>()`, `is<X>()` and the field route. Read them from an instantiated item or from `media/scripts` | M `exp01-20260910-000351` |

`Nutrition.save`/`load` order is calories, proteins, lipids, carbohydrates, weight (float)
(`Nutrition.save @0–@45 L209–L213`, `load @0–@41 L217–L221`); `load` goes through the clamping
setters (C).

---

## MP behaviour

**The server owns `Nutrition`; the client is a mirror.** This reverses the direction recorded by
spike S6 before slice 01; the S6 measurement (client and server agreeing within 0.2 kcal) is
consistent with both readings, and the authority probes below settle it.

| Fact | Mechanism | Ev |
|---|---|---|
| An MP client never runs `ISEatFoodAction:complete()`, so it never calls `Eat` | `LuaTimedActionNew.complete @31 L162` — `getstatic GameClient.client; ifne` skips the Lua call; `ISEatFoodAction:perform` has its `Eat` line commented out (`:168`) | C |
| The eat completes on the **server** | client `LuaTimedActionNew.start @60–@96 L127–L129` → `ActionManager.createNetTimedAction` → `NetTimedActionPacket`; server `ActionManager.update @0 L66` (server-gated) → `NetTimedAction.perform @0–@27 L140` → `ISEatFoodAction:complete()` → `IsoGameCharacter.Eat` | C |
| Cancels also resolve on the server | `NetTimedAction.stop @0–@53 L114` → `ISEatFoodAction:serverStop()` (`:141–153`), fraction from `self.netAction:getProgress()` (`:151`); `netAction` is injected by `NetTimedAction.parse @225` and exists **only** server-side. `serverStop` applies that partial eat only if neither of its two guards clears `applyEat`: the item is `Base.Cigarettes` (`:143–145`), or `abs(getHungerChange()*100) <= 1` (`:146–149`). So a cancelled eat of a cigarette — or of **any** item whose (state-modified) hunger change is ≤ 1 — applies nothing at all: no stats, no nutrition, no `multiplyFoodValues`, no consumption | C |
| The server pushes the whole `Nutrition` at eat time | `Eat @732–@759 L5808` sends `PacketType.EatFood`; `EatFoodPacket.write @19–@33 L71` embeds `Nutrition.save`; `parse @17–@31 L56` calls `Nutrition.load` on the receiver | C |
| …and again every second, unconditionally | `NetworkPlayerManager.update @0 L19` (server-gated) with `statsUpdateLimit = new UpdateLimit(1000)` (`<clinit> @13–@23 L10`) → `NetworkPlayerAI.syncStats @32–@50 L711` → `PacketType.PlayerStats`, whose `write`/`parse` embed `Nutrition.save`/`load` | C |
| `SyncPlayerStats` from `Eat` carries **no** nutrition bits | `Eat @658–@722 L5806` — THIRST, HUNGER, ENDURANCE, STRESS, FATIGUE, PAIN masks only, plus `GameServer.sendSyncPlayerFields(player, 8)` | C |
| Receiving `EatFood` applies no numbers | `EatFoodPacket.processClient @0–@19 L80–L81` and `processServer @0–@13 L85–L86` both call `EatOnClient`, which fires `OnEat` and nothing else; the numbers arrive via the `Nutrition.load` inside `parse` | C |
| The client does not simulate nutrition drain | `Nutrition.update @42 L75` skips the macro decay and `updateCalories()` when `GameClient.client` | C |
| **The client computes a weight and discards it** | `updateWeight()` at `@106 L81` is still called, but `updateWeight @317–@320 L198` (`getstatic GameClient.client; ifne`) sits **before** `setWeight` (`@323 L199`), before the trait counter and before `applyTraitFromWeight` (`@349 L202`). Client weight therefore comes only from `Nutrition.load` in the packets, and **weight band traits never apply client-side**. Measured: a client `setWeight(105)` read back 105 with `hasTrait(Obese)` false, then reverted to the server's 80 within 3 s with `Obese` still false | C+**M** `exp03-20260910-045523` ([`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json)); see [body-stats.md](body-stats.md) § MP behaviour |
| **A client-side `setCalories(3000)` never reached the server and was reverted within 3 s** | client read back 3000; server read 887.920 at that instant; client 3 s later 887.331 — the server's value | **M** `exp01-20260910-000351` |
| **A server-side `setCalories(2500)` propagated to the client within 3 s** | server 2500 → client 2499.436 after 3 s | **M** `exp01-20260910-000351` |
| **The real path lands on the client ~5.5 s after queuing, in one step equal to the direct-call delta** | `eat.action` on a server-spawned apple: +94.741 kcal at t = 5.5 s (95 less the 0.259 burned that second) vs +95 for a direct `Eat` call; reproduced in both runs | **M** `exp01-20260910-003929` |
| **Server and client `Nutrition` converge to bit-identical values** | witness rows: 746.838 / 746.967 before, 838.475 / 838.605 immediately after, 837.055 / 837.055 five seconds later — the ~0.13 kcal offset is sub-second sampling skew on a 0.259 kcal/s drain, not divergence | **M** `exp01-20260910-003929` |
| **Hunger and thirst behave identically** — `CharacterStat.HUNGER`/`THIRST` are server-owned too | a client `stats.set hunger 0.9` read back 0.9 while the server stayed at 0.0005 and the client fell back to 0.00098 within 3 s; a server-side `0.4` reached the client (0.400293) | **M** `exp01-20260910-003929` |
| Client-spawned food makes the server log a `SyncItemFields` NPE | `Eat`'s final `syncItemFields()` (`@961 L5841`) runs against an item the server never heard of. **Positive evidence** — the smoke run, whose harness `eat` spawned the item client-side, left two lines in `server_errors[0..1]` of [`eat-smoke.json`](../../testing/artifacts/exp01-20260910-000351/eat-smoke.json): `Error with packet of type: SyncItemFields` and `NullPointerException: Cannot invoke "zombie.inventory.InventoryItem.hasSharpness()" because "item" is null at SyncItemFieldsPacket.parse(SyncItemFieldsPacket.java:383)`. **Negative control** — the matrix run spawned every item server-side over RCON `additem` and logged **0** `SyncItemFields` lines and **0** server errors | C+M `exp01-20260910-000351` (positive), `exp01-20260910-003929` (control) |

**Cross-reference — what a client reads off a *cooked* item is not what the server reads.** The
rows above are the **player** side (`Nutrition`, hunger/thirst). The **item** side has a vanilla
distortion of its own: `ItemStatsPacket.setData` sends `Food.getThirstChange()`, the cooked-ladder
getter, while the receiver stores it as the raw field, so a cooked food's thirst value halves on
each server→client hop. Its graded, canonical row is
[`../modding/patterns.md`](../modding/patterns.md) § Measured MP sync facts → *The other
direction — server → client* (slice 09, runs `td1-20260910-192457` / `td1b-20260910-202029`); do
not restate the numbers here.

**What a mod must do to change intake for MP players.** Anything that alters what eating delivers
has to run where `Eat` runs — the server. A client-side Lua mod that writes vanilla nutrient numbers
onto `IsoPlayer` is overwritten within a second by the 1 Hz `PlayerStatsPacket`; a client-side mod
that writes its *own* fields is not overwritten (custom fields are not in the packet) but desyncs
from the vanilla numbers, which keep being recomputed server-side. The three viable shapes are:
(a) mutate on the server via the command bus (`sendClientCommand` → validate → mutate → the engine's
own push), (b) keep the parallel store in player modData and `transmitModData()` on change, or
(c) accept client-only semantics. `OnEat` is the one vanilla hook on the intake path, and in MP it
fires **on the server** inside `Eat` (and separately on any receiver of `EatFoodPacket`, through
`EatOnClient`, with no numeric effect). Ev C, with the authority rows above as M.

**No packet-level log evidence exists.** `EatFood` / `EatFoodPacket` produce zero lines in
`server-stdout.log`, the client `console.txt` and the client debug log even with
`-debuglog=Network` on 42.20.4 (M, `exp01-20260910-003929` — only that run grepped the server
log; the smoke run recorded errors but never grepped for `EatFood`); the packet path is evidenced
by its effect — the 5.5 s landing and the witness convergence — not by a log line.

---

## Inputs for the 3-day scenario (slice 04)

1. **Drive and read on the server.** Because the server owns `Nutrition`, the scenario must call
   `nutrition.set <user> calories …` on the **server** bus and assert on server-side reads; a
   client-side write is discarded within 3 s (M, `exp01-20260910-000351`). The same holds for
   hunger/thirst priming (M, `exp01-20260910-003929`). Client reads are usable only as a mirror
   check, and lag by up to the 1 Hz push (measured convergence to bit-identical within 5 s).
2. **`setCalories(+X)` adds exactly X, then clamps.** The store setter is
   `Nutrition.setCalories(getCalories() + X)` with `PZMath.clamp(v, -2200, 3700)` (C), measured
   exactly: `set 9999` → **3700.000**, `set -9999` → **−2200.000**; carbs/lipids/proteins each
   clamp to **[−500, 1000]** (M, `exp01-20260910-003929`). A "fixed daily intake" larger than the
   ceiling is silently lost, so the scenario must re-set or top-up per sample rather than assume
   accumulation.
3. **The burn runs against you while you sample.** With the player idle at `settimespeed 1` the
   server burned a very steady **0.259 kcal/s** (0.256 kcal/s in the earlier run) and the macro
   drain accounted for 99.0 % of the control window's game-time (M, `exp01-20260910-003929`).
   Expected weight must be computed from the *sampled* calorie series, not from the intended
   intake.
4. **Weight model** (`Nutrition.updateWeight`, re-read unchanged on this jar, C; restated from
   [nutrition-core.md](nutrition-core.md)):

   ```
   gainThreshold = 1000 + (weight - 80) x 40        # w70: 600 · w80: 1000 · w90: 1400
       trait Weight Gain (weight < 90): base 700
       trait Weight Loss (weight > 70): base 1800
   loseThreshold = min(0, (weight - 70) x 30)       # at weight >= 70 any negative calorie total loses
   if calories > gainThreshold:
       rate = 1.3e-5 /game-sec x min(1, calories/4000)
       if carbs > 700 or lipids > 700:   rate x3
       elif carbs > 400 or lipids > 400: rate x2
   elif calories < loseThreshold:
       rate = 8.5e-6 /game-sec x min(1, abs(calories)/2500)
   ```

5. **The clamps cap the model, which changes the expected numbers.** Calories can never exceed
   3700, so `min(1, calories/4000)` caps at **0.925** and the plain gain rate caps at
   `1.3e-5 × 0.925 × 86400 = 1.039 kg per game-day` — not the 1.12 kg/day that a naive reading of
   "at 4000 calories" suggests. With carbs or lipids above 700 (reachable: they clamp at 1000) the
   ×3 branch gives **≤ 3.117 kg/game-day**. On the loss side calories floor at −2200, so
   `min(1, 2200/2500) = 0.88` and loss caps at `8.5e-6 × 0.88 × 86400 = 0.646 kg/game-day`. These
   are derived from the C formula and the M clamps; treat them as the scenario's ceilings, not as
   measured outcomes. **Since measured on the server** (slice 04, `scenario-20260910-054012` and
   `-055029`): the loss ceiling landed exactly — a game-day spent on the −2200 floor lost
   **0.646 kg** — while the gain ceiling was, as expected, only approached from below, because a
   store fed under the clamp first ramps up from empty (day 1) and then sawtooths rather than sitting on it (0.842 kg/game-day over three days, 0.940 over days 2-3 alone; see the
   ramp/sawtooth split there). Both runs, with residuals and what they do not cover:
   [nutrition-core.md](nutrition-core.md) § Verified on server.
6. **Weight is server-only; the client computes it and discards it.** `Nutrition.update @106 L81`
   calls `updateWeight()` on both sides, but the method's own `GameClient.client` skip
   (`@317–@320 L198`) sits before `setWeight` (`@323 L199`) and before `applyTraitFromWeight`
   (`@349 L202`), so a client's computation is thrown away and its weight comes only from
   `Nutrition.load` in the packets — up to one push behind (C; corrected 2026-09-10 by slice 03).
   Both witness rows read `weight 80` on both sides (M, `exp01-20260910-003929`), and a client
   `setWeight(105)` reverted to the server's 80 within 3 s with `Obese` never applied
   (M, `exp03-20260910-045523`). Assert weight server-side.
7. **`Eat` never writes weight** — its `Nutrition` block writes only the four nutrient setters (C)
   and `dWeight = 0.0000` on all 27 matrix rows (M) — so weight moves
   only through `Nutrition.update() → updateWeight()`, which the sandbox `Nutrition` option gates
   (C). The scenario needs `Nutrition = true`; the fixture reads `true` (M,
   `exp01-20260910-003929`).
8. **Do not route the scenario through timed eats.** Intake through `eat.action` costs ≈5.5 s of
   wall time per item and its `maxTime` budget is a per-frame tick count whose behaviour under
   `settimespeed` was not measured (see Open questions). Driving `setCalories` directly on the
   server tests the weight model in isolation, which is what the slice plan specifies.

---

## Discrepancies vs the wiki

The mirrors agree with the code on the weight formulas and the store ceilings — the Nutrition
mirror's gain/loss math and its `3700 / -2200` and `1000 / -500` ceilings match the 42.20.4 jar and
the measured clamps exactly, despite the page being nine minors stale. The disagreements:

| # | Wiki claim (mirror, page version) | Code / measurement | Ev |
|---|---|---|---|
| 1 | "As food begins to rot, its effects will become more negative" — read as blanket ([food.md](../../references/wiki-mirrors/food.md), 42.20.0) | Rot leaves **all four nutrients untouched**: rotten bread delivered its full 532 kcal / 99 g carbs. Only hunger (÷2.2), stress (÷2), boredom/unhappiness (+20) and the sickness roll degrade; thirst is not touched either, and neither is endurance — `Food.getEnduranceChange` branches on burnt / stale / cooked only (see the modifier table above), so a rotten item (`age ≥ offAgeMax`, i.e. past the stale window `offAge ≤ age < offAgeMax`) falls through to its raw value | W vs C+M `exp01-20260910-003929` |
| 2 | Burnt "loses most of its positive effects" — never quantified ([food.md](../../references/wiki-mirrors/food.md), 42.20.0) | The one real nutrition modifier in the game: `Eat` divides all four nutrients by **5** for `isBurnt()` items, and `getThirstChange` divides by 5 while `getHungerChange` divides by 3. Measured on four items | W vs C+M `exp01-20260910-003929` |
| 3 | Nutritional-values rows are state-free ([nutritional-values.md](../../references/wiki-mirrors/nutritional-values.md), 42.20.0) | Correct for the macros (bare getfields) but **wrong for hunger**, which `Food.getHungerChange` scales ×1.3 cooked / ÷3 burnt / ÷1.3 stale / ÷2.2 rotten. The page's hunger column is also the raw script value (÷100 at instantiation), so it is an identity column, not an arithmetic one; and its "Fat" column is the script/Java `Lipids` | W vs C+M `exp01-20260910-003929` |
| 4 | The weight sim is always on; the sandbox `Nutrition` option is never mentioned ([nutrition.md](../../references/wiki-mirrors/nutrition.md), 42.11.0) | The option gates `Nutrition.update()` — drain, burn **and** weight — while intake continues unguarded | W vs C |
| 5 | Proteins 50–300 give ×1.5 Strength XP and below −300 ×0.7, self-dated "Build 34.5" ([nutrition.md](../../references/wiki-mirrors/nutrition.md), 42.11.0) | Not found on this jar: protein's only verified effect is `IsoGameCharacter.getRecoveryMod`, and Fitness/Strength XP gating (`canAddFitnessXp`) is **weight-trait** based, not protein-based ([nutrition-core.md](nutrition-core.md)) | W vs C |
| 6 | Cooking "increases nutrition of evolved recipes" ([cooking.md](../../references/wiki-mirrors/cooking.md), 42.18.0) | `Eat` reads calories and macros as bare fields with no skill term anywhere on the intake path, so any cooking-skill effect must be baked into the crafted item at recipe-build time — unverified here, and an input to slices 02/06 | W vs C |

---

## Open questions

1. **The sandbox flip.** Per bytecode, `SandboxOptions.set(String,Object)` writes only the local
   `ConfigOption` — pushing requires `SandboxOptions.sendToServer()` → `GameClient.sendSandboxOptionsToServer`,
   the admin panel's route (`media/lua/client/ISUI/AdminPanel/ISServerSandboxOptionsUI.lua:738` guards `getSandboxOptions():set()`
   with `if not isClient()` and uses `sendToServer()` instead). The matrix used the plain
   client-local flip with **no** push, yet the server-side drain appeared to halt (99.0 % of the
   control window accounted for vs 41.4 % of the flipped one, then two reads 1.7 s apart identical
   to six decimals). n = 1, no no-flip control repeat, and the mechanism is not established — this
   is **not** recorded as a fact. Re-test in slice 03 with an explicit `sendToServer` push and a
   no-flip control, polling the server every second to watch the drain stop and restart.
2. `SandboxVars.Nutrition` (the Lua mirror table) stayed `true` while the Java option went `false`
   and back (M, `exp01-20260910-003929`): any mod reading the Lua table sees a stale value after a
   runtime change. Whether it is also stale after an admin-panel push is unmeasured.
3. Whether a timed action's `maxTime` tick budget scales with `settimespeed`. Both `eat.action`
   measurements ran at `settimespeed 1`; the observed ≥42 ticks/wall-second is consistent with a
   per-frame budget but no accelerated run exists to confirm it.
4. **`f0` vs `f` in the custom-weight write.** `Eat @933 L5839` multiplies by `f0` (the clamped
   argument) while everything else uses the rescaled `f`; on a part-eaten custom-weight item the two
   differ, so weight and hunger drift apart. Bytecode is unambiguous about which local is used;
   whether it is intentional, and how large the drift gets, needs an experiment (quarter → quarter →
   quarter of a canned food, logging `getWeight`/`getHungChange`/`getBaseHunger`).
5. Which items ever set `baseHunger ≠ hungChange` at spawn. Every path found initialises them equal;
   `Food.copyNutritionFromRatio`, `IsoAnimal.modifyMeat`, `RecipeCodeOnCreate.makeCoffee` and
   `ItemStatsPacket.applyItemStats` write `baseHunger` separately and were not read (slice 02).
6. Whether `EatFoodPacket` is broadcast to all clients or only to the eater —
   `INetworkPacket.send(IsoPlayer, PacketType, Object[])` was not dumped. The receiver writes into
   `PlayerID.getPlayer().getNutrition()`, correct either way, but the traffic cost differs.
7. `GameClient.eatFood` has no callers in the jar or in `media/lua`: the client→server direction of
   this packet is latent. A mod could call it; note it if a mod conflict appears.
8. `Nutrition.caloriesMax` / `caloriesMin` (`updateCalories @319–@358 L121–L125`) are maintained but
   no reader was found — possibly UI/debug only.
9. `getHealthFromFoodTimeByHunger()` was not dumped; it scales the food→health loop, not intake.
10. The rot-roll denominator when `offAgeMax == offAge` takes the 100 % branch
    (`JustAteFood @759 L720`); no vanilla item was checked for that shape (scan `food.txt` for
    `DaysFresh == DaysTotallyRotten` in slice 02).
11. The fluid path (`DrinkFluid`) is C-only: no live measurement of a fluid container was taken in
    this slice.
12. The passive calorie-burn model (`updateCalories`: exertion, temperature and trait terms) is
    settled in [body-stats.md](body-stats.md) (slice 03): the model is decoded in full, the idle
    rate and the `weight/80` term are measured (M, `exp03-20260910-045523`), and the moving and
    asleep branches remain C with their own open questions there.

---

## Sources

**Jar (pzdis, 42.20.4 `b0bbce05d5`, `D:\SteamLibrary\steamapps\common\ProjectZomboid\projectzomboid.jar`)**
`zombie/characters/IsoGameCharacter.Eat(InventoryItem,float,boolean)`, `.EatOnClient`,
`.DrinkFluid`; `zombie/inventory/types/Food` (`getHungerChange`, `getThirstChange`, `getCalories`,
`getCarbohydrates`, `getLipids`, `getProteins`, `getEnduranceChange`, `getStressChange`,
`getFoodSicknessChange`, `getBoredomChange`, `getUnhappyChange`, `multiplyFoodValues`, `update`,
`isRotten`); `zombie/characters/BodyDamage/Nutrition` (`update`, `updateCalories`, `updateWeight`,
`setCalories`, `setCarbohydrates`, `setProteins`, `setLipids`, `save`, `load`);
`zombie/characters/BodyDamage/BodyDamage.JustAteFood`; `zombie/characters/Stats.set`,
`zombie/characters/CharacterStat`; `zombie/scripting/objects/Item.InstanceItem`;
`zombie/characters/CharacterTimedActions/LuaTimedActionNew`; `zombie/ai/ActionManager`,
`NetTimedAction`; `zombie/network/packets/actions/EatFoodPacket`, `PlayerStatsPacket`,
`GeneralActionPacket`; `zombie/network/NetworkPlayerManager`, `NetworkPlayerAI.syncStats`,
`GameClient.eatFood`; `zombie/SandboxOptions`; `zombie/characters/IsoPlayer.updateInternal2`.

**Lua (`D:\SteamLibrary\steamapps\common\ProjectZomboid\media\lua`)**
`shared/TimedActions/ISEatFoodAction.lua`, `shared/TimedActions/ISDrinkFluidAction.lua`,
`shared/TimedActions/ISBaseTimedAction.lua`, `client/ISUI/ISInventoryPaneContextMenu.lua`,
`client/ISUI/AdminPanel/ISServerSandboxOptionsUI.lua`, `shared/Sandbox/{Apocalypse,Extinction,Outbreak,Rising,SixMonthsLater}.lua`.

**Scripts** `media/scripts/generated/items/food.txt` (`Base.Apple` at `:8658`; `Base.Steak`,
`Base.Bread`, `Base.Carrots`, `Base.HotDrink`).

**Measured runs.** The result JSON each run wrote is committed byte-for-byte under
[`testing/artifacts/<run id>/`](../../testing/artifacts/README.md) — those are the files every
**M** row here cites. The full run directories (server and client logs, stdout, per-client dumps)
stay local under `testing/runs/<run id>/`, which is gitignored (`.gitignore:44`).
- `exp01-20260910-000351` — [`testing/artifacts/exp01-20260910-000351/eat-smoke.json`](../../testing/artifacts/exp01-20260910-000351/eat-smoke.json):
  direct `Eat` deltas, the `eat.action` real path, and the client/server authority probes.
- `exp01-20260910-003929` — [`testing/artifacts/exp01-20260910-003929/eat-matrix.json`](../../testing/artifacts/exp01-20260910-003929/eat-matrix.json):
  the 5 items × 5 states matrix plus fractions, the real path on a server-spawned item, the setter
  clamps, the hunger/thirst authority probe and the sandbox windows. Items were spawned by the
  server over RCON `additem`; the run's server log contains **no** `SyncItemFields` lines
  (`log_grep.SyncItemFields: []`) and no error lines at all, which is what shows the eaten items
  were server-side objects rather than client-local ones.
  *Caveat on that `log_grep` block:* the committed one was produced by a **case-sensitive**
  matcher, so a zero in it is only trustworthy for strings the log actually spells in that case.
  The `SyncItemFields` zero was re-verified case-insensitively against
  `testing/runs/exp01-20260910-003929/server-stdout.log` (`grep -ic syncitemfields` → 0, and
  `eatfood` → 0), so it stands. Its sibling **`Nutrition: []` does not** — the harness logs its
  own commands lowercase (`nutrition.get`), and a case-insensitive grep of the same log returns 27
  hits. `s01_eat_matrix.py:346–364` now matches case-insensitively; the artifact predates that fix.

**Wiki mirrors** [nutrition.md](../../references/wiki-mirrors/nutrition.md) (page version 42.11.0),
[food.md](../../references/wiki-mirrors/food.md) (42.20.0),
[nutritional-values.md](../../references/wiki-mirrors/nutritional-values.md) (42.20.0),
[cooking.md](../../references/wiki-mirrors/cooking.md) (42.18.0).

**Prior work in this library** `docs/superpowers/plans/01-notes.md` (the task-4 code map this
document is built on), [nutrition-core.md](nutrition-core.md),
[../testing/spikes.md](../testing/spikes.md) §S6 (whose nutrition-direction conclusion this slice
corrects), [../modding/patterns.md](../modding/patterns.md).

**Later work that corrects this document** [body-stats.md](body-stats.md) (slice 03) — the client
runs `updateWeight()` and *discards* the result (`updateWeight @317–@320 L198`), so the rows and
the scenario note above that read "the client still runs `updateWeight`" have been reworded;
measured in run `exp03-20260910-045523`
([`testing/artifacts/exp03-20260910-045523/body.json`](../../testing/artifacts/exp03-20260910-045523/body.json)).
