# The eating pipeline
Verified against 42.20.4 (b0bbce05d5) · 2026-10-01 · scope: what a food item or a fluid container delivers to a player's stats and `Nutrition` when it is eaten or drunk — the getters, the fraction, the modifier ladder, the leftover, the drink path and its two Lua drivers, the duration and the sandbox gate; the hook dispatch and the packet field lists are handed off.

## Key facts

- One method does all of it: `IsoGameCharacter.Eat` clamps and rescales the fraction, writes the five stats, then the four nutrients, then pain and cold reduction and the food-sickness cure, then `JustAteFood`, then the server's sends, then the `OnEat` hook, and consumes or rescales the item last [#0006].
- The fraction is not the menu fraction: when `baseHunger` and `hungChange` are both non-zero the menu's share of the whole item is re-expressed as a share of what is left, `clamp01(baseHunger * f / hungChange)` [#0014/M/one-fixture].
- Nutrition is written before the `OnEat` hook fires and before the item is consumed, so a hook sees the post-intake store and the pre-consume item [#0008].
- A burnt item's four nutrients are divided by 5 on the way into the store [#0019/M/one-fixture].
- That divisor is the only nutrition modifier in the game: calories, carbohydrates, lipids and proteins are bare field reads with no cooked, burnt, rotten or frozen branch [#0036/M/one-fixture].
- Hunger is state-modified, and cooked at times 1.3 takes precedence over burnt, which divides by 3, with stale dividing by 1.3 and rotten by 2.2 [#0029/M/one-fixture, #0030/M/one-fixture, #0031, #0032/M/one-fixture].
- Thirst runs the opposite precedence: burnt divides by 5.0 and beats cooked, which divides by 2.0 [#0033/M/one-fixture, #0034/M/one-fixture].
- HUNGER and THIRST are registered with a minimum of 0 and a maximum of 1 and every write is clamped, so overshoot is silently discarded [#0021/M/one-fixture].
- `Item.InstanceItem` divides the script's `HungerChange`, `ThirstChange` and `EnduranceChange` by 100 at instantiation and stores `Calories`, `Carbohydrates`, `Lipids` and `Proteins` unscaled [#0011/M/one-fixture].
- The remainder of a part-eaten item is scaled by `multiplyFoodValues(1 - f)`, which multiplies fifteen stored fields and truncates three of them to int [#0057/M/one-fixture].
- `Eat` never writes `Nutrition.weight`: its nutrition block writes the four nutrient setters and nothing else [#0061/M/one-fixture].
- A fluid's `Properties` are the effect of one litre, the container multiplies them by the litres it holds, and drinking spends that aggregate times the fraction drunk [#0630, #0633].
- Measured on the drink path, a full 0.3-litre can wrote 120.000031 calories and 31.200001 grams of carbohydrate, the same can at half wrote 60.0 and 15.6 [#1892/M/n=1].
- The drink action's Lua is interceptable: a wrapper of its `updateEat` and `complete` fired on the server and the client's counters stayed at 0 when the game's own drink action ran, the client's install not witnessed [#2825/M/n=1].
- The sandbox `Nutrition` option gates only `Nutrition.update()` — the macro drain, the calorie burn and weight — and leaves the `Eat` and `DrinkFluid` store writes untouched [#0067].
- An eat costs 232 ticks per loop for food and 171 for a drink-type item, and the real multiplayer path lands on the client about 5.5 s after the action is queued [#0071/M/one-fixture, #1189/M/n=1].
- Vanilla has no overeating effect in Java: `Eat` and `JustAteFood` add no stat for eating while full, and the one cap, the refusal at FOOD_EATEN level 3, is checked in client Lua alone [#3596/C/C-only] [#3597/C/C-only] [#3599/C/C-only] [#0522/C/C-only].

## How it works

<a id="getters"></a>
### The five `Food` getters

`Food` exposes five getters whose names differ by a letter, and the pipeline uses each for a different job.
Reading the wrong one is the commonest way to get an intake number wrong.

- `getBaseHunger()` returns the item's stored `baseHunger` unchanged and is read only by the fraction rescale, so an eat fraction means a share of the whole item rather than of what is left [#0001].
- `getHungChange()` is a bare read of the instance's remaining `hungChange` with no state modifiers; it drives the fraction rescale and both crumb rules, it is what `multiplyFoodValues` shrinks, and it is what `Eat` zeroes when the item is finished [#0002].
- `getHungerChange()` is the state-modified hunger value — the cooked, burnt, stale and rotten ladders, each floored at 0.01 with the sign kept — and it is the value that drives the HUNGER stat [#0003].
- `getThirstChange()` is the state-modified thirst value that drives the THIRST stat, and its raw value also gates the second crumb rule [#0004].
- `getThirstChangeUnmodified()` is a bare read of the `thirstChange` field and is the getter `multiplyFoodValues` reads, so cooked and burnt multipliers are never baked into the leftover [#0005].

Those two state-modified getters are the only ones on the intake path: a five-item, five-state matrix found no other intake number that moved with item state [#0102/M/one-fixture].
A mod that wants the number the player will actually receive reads `getHungerChange` and `getThirstChange`.
A mod that wants the number the item still stores reads `getHungChange` and `getThirstChangeUnmodified`.
The distinction survives every later step, because the fraction, the crumb rules and the leftover scaling are all computed from the unmodified pair.
A value read through the modified pair and written back onto the item compounds the state ladder each time it is written.

<a id="eat"></a>
### The order of writes inside `Eat`

`IsoGameCharacter.Eat(InventoryItem,float,boolean)` writes in one fixed order: the fraction is clamped and rescaled, then the five stats, then the four nutrition setters, then pain and cold reduction and the food-sickness cure, then `JustAteFood`, then the server's packet sends, then the `OnEat` hook, and only then is the item consumed or scaled down and synced [#0006].

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

The other two overloads are trampolines: `Eat(item,f)` calls `Eat(item,f,false)` and `Eat(item)` calls `Eat(item,1.0f)` [#0007].
Every number the method writes is an item getter times that one fraction, with the burnt divisor as the single exception, so the levers on what an eat delivers are the getter's input, the item's state and the fraction.
Two consequences of that order carry most of the design weight.
Nutrition is written before the `OnEat` hook fires and before the item is consumed, so a hook sees the post-intake `Nutrition` and the pre-consume item [#0008].
`BodyDamage.JustAteFood(food, f, useUtensil)` is the only use of the `useUtensil` argument inside `Eat` [#0009], so a utensil changes mood and duration and never intake.
`Eat` adds the item's endurance and fatigue changes times the fraction to the `ENDURANCE` and `FATIGUE` stats, and the server's follow-up player-stats send names both in its mask [#0017/M/one-fixture, #0115].
Which vanilla item writes an endurance change at all is [`../facts/food-item-model.md#script-keys`](../facts/food-item-model.md#script-keys)'s.
How `OnEat` resolves, which side calls it and what its client-side twin does not apply are [`../platform/lua-platform.md#script-hooks`](../platform/lua-platform.md#script-hooks), and the packets the server sends from inside the method are [`../facts/wire-packets.md#eat-food-packet`](../facts/wire-packets.md#eat-food-packet).

The eat action's completion step runs server-only and a Lua wrapper of it fires before the eat hook: one session recorded the wrapper and then the hook on the server while the client recorded only the hook, with one completion on the server and none on the client and the eaten item's type recorded server-side only — so a mod that needs the food item intact before the eat path consumes it has to sit in the wrapper, and the wrapper installs on the client too, where it stays silent [#0928/M/n=1].

One write is not symmetric with the rest.
The custom-weight write multiplies by `f0`, the clamped argument, and not by the rescaled `f`, so on a part-eaten custom-weight item weight and hunger drift apart; the bytecode fixes which local is used and the size of the drift is unmeasured [#0010/C/inference].

A `Food` item that carries a `ThirstChange` goes through `Eat` exactly like solid food, so its thirst and its macros are scaled by the same fraction, and `CustomMenuOption = Drink` changes only the animation and the duration formula — measured on one drink item across five states [#0083/M/one-fixture].
That is a different path from the fluid containers below, and the two share no code.

<a id="modifiers"></a>
### The modifier ladder

Every modifier an intake passes through, in the order `Eat` and its callees apply them.
The clamps on the four nutrient stores are the store's own and live at [`../facts/nutrition-core.md#clamps`](../facts/nutrition-core.md#clamps) ([#0022/M/n=2], [#0023/M/n=2]).
The poison, taint, rot-sickness and dangerous-uncooked rolls `JustAteFood` runs are [`../facts/food-item-model.md#poison`](../facts/food-item-model.md#poison) ([#0050], [#0051], [#0052], [#0053]).
The utensil's effect on the duration is under the duration below.
Each row here is one claim and carries its own tag, and a measured row names the arm it rests on.

| Modifier | Applies to | Effect |
|---|---|---|
| argument clamp | the fraction | `f = PZMath.clamp(f, 0, 1)`, before anything else [#0013] |
| `baseHunger` rescale | the fraction | when `baseHunger` and `hungChange` are both non-zero, `f = clamp01(baseHunger * f / hungChange)`; one measured arm, a half-eaten apple at menu fraction 1.0 giving 47.5 kcal rather than 95 [#0014/M/one-fixture] |
| hunger crumb rule | the fraction | promoted to 1 when `hungChange` is negative and the leftover `hungChange * (1 - f)` would be greater than -0.01 [#0015] |
| thirst crumb rule | the fraction | promoted to 1 when `hungChange` is 0, `thirstChange` is negative and the leftover `thirstChange * (1 - f)` would be greater than -0.01 [#0016] |
| fraction scaling | THIRST, HUNGER, ENDURANCE, STRESS, FATIGUE | each getter times the rescaled fraction is added to its stat; one item at a quarter gave -0.04 hunger and -0.0175 thirst [#0017/M/one-fixture] |
| fraction scaling | calories, carbohydrates, proteins, lipids | each times the rescaled fraction is added to the player's store; an apple at 1.0, 0.5 and 0.25 gave 95, 47.5 and 23.75 kcal, exact on all six numeric fields [#0018/M/one-fixture] |
| burnt | the four nutrients | divided by 5 on the way in; measured on four items — apple 95 to 19, steak 220 to 44, bread 532 to 106.4, carrots 25 to 5 [#0019/M/one-fixture] |
| non-player guard | the four nutrients | skipped entirely when `Type.tryCastTo(this, IsoPlayer.class)` is null, so an animal or an NPC gets stats, pain, cold and sickness but no nutrient write [#0020] |
| stat clamp | HUNGER, THIRST | registered with a minimum of 0 and a maximum of 1, every write clamped, overshoot silently discarded; a satiated character kept all 532 kcal of rotten bread and about none of its hunger relief [#0021/M/one-fixture] |
| fraction scaling | pain reduction, cold reduction | `getPainReduction() * f` and `getFluReduction() * f` added to the body's two reductions [#0024] |
| food-sickness cure | FOOD_SICKNESS, POISON | `abs(foodSicknessChange) * f` removed from both, when FOOD_SICKNESS is above its minimum, the item's value is negative and the edible-buff timer has expired [#0025] |
| Iron Gut | the edible-buff timer | re-armed to `Rand.Next(80, 150)` [#0026] |
| Weak Stomach | the edible-buff timer | re-armed to `Rand.Next(200, 280)` [#0027] |
| neither stomach trait | the edible-buff timer | re-armed to `Rand.Next(120, 230)` [#0028] |
| cooked | `getHungerChange` | times 1.3, and the cooked branch takes precedence over burnt and rot; one item measured, -0.16 to -0.208 [#0029/M/one-fixture] |
| burnt | `getHungerChange` | `max(abs(h)/3.0, 0.01)` with the sign kept; one item measured, -0.0533 [#0030/M/one-fixture] |
| stale, that is `offAge <= age < offAgeMax` | `getHungerChange` | `max(abs(h)/1.3, 0.01)` with the sign kept [#0031] |
| rotten, that is `age >= offAgeMax` | `getHungerChange` | `max(abs(h)/2.2, 0.01)` with the sign kept; one item measured, -0.0727 [#0032/M/one-fixture] |
| burnt | `getThirstChange` | divided by 5.0, and the burnt branch takes precedence over cooked, the opposite order to hunger; two items measured [#0033/M/one-fixture] |
| cooked | `getThirstChange` | divided by 2.0; two items measured [#0034/M/one-fixture] |
| rotten | `getThirstChange` | nothing, because there is no rotten branch: a rotten apple still gave -0.07 and a rotten hot drink still gave -0.20 [#0035/M/one-fixture] |
| none | `getCalories`, `getCarbohydrates`, `getLipids`, `getProteins` | bare field reads with no cooked, burnt, rotten or frozen modifier anywhere; the cooked, rotten and frozen rows of a five-item matrix all delivered full values, rotten bread giving 532 kcal and 99 g of carbohydrate [#0036/M/one-fixture] |
| frozen | the six intake numbers | none of them: all five matrix items measured identical fresh against frozen, and frozen moves boredom and unhappiness only [#0037/M/one-fixture] |
| burnt / stale / cooked | `getEnduranceChange` | divided by 3 / divided by 2 / times 2 [#0038] |
| burnt / stale / rotten / cooked | `getStressChange` | divided by 4 / by 1.3 / by 2 / times 1.3 [#0039] |
| burnt / stale / rotten / cooked | `getFoodSicknessChange` | divided by 3 / by 1.3 / by 2.2 / times 1.3, truncated to int [#0040] |
| frozen | `getBoredomChange`, `getUnhappyChange` | plus 30 each, unless the type is `Icecream` or the item carries the `GOOD_FROZEN` tag [#0041] |
| burnt / stale / rotten | `getBoredomChange`, `getUnhappyChange` | plus 20 / plus 10 / plus 20 each [#0042] |
| bad-cold / good-hot | `getUnhappyChange` | plus 2 when bad-cold, cookable, cooked and below 1.3 heat; minus 2 when good-hot, cookable, cooked and above 1.3 heat [#0043] |
| fertilized | boredom, unhappiness, stress | every modifier bypassed and the raw field returned, and `isRotten()` forced false [#0044] |
| `RemoveNegativeEffectOnCooked` | `thirstChange`, `unhappyChange`, `boredomChange` | each set to 0 if positive on the cook transition, permanently and once, with nutrition untouched [#0045] |
| `removeUnhappinessWhenCooked` | `unhappyChange` | set to 0 on the cook transition [#0046] |
| utensil | BOREDOM | times 1.25 when `boredomChange * f` is negative, else times 0.75 [#0047] |
| utensil | UNHAPPINESS | times 1.25 when `unhappyChange * f` is negative, else times 0.75 [#0048] |
| HUNGER at its minimum | `healthFromFoodTimer` | plus `abs(getHungerChange()) * f * getHealthFromFoodTimeByHunger()`, doubled for a cooked item, capped at 11000.0 [#0054] |
| alcoholic | intoxication | routed to `JustDrankBooze(food, f)` [#0055] |
| Tutorial game mode | the sickness rolls | `JustAteFood` returns early, after the mood writes and before them [#0056] |
| none | `Nutrition.weight` | `Eat` never writes it: its nutrition block writes the four nutrient setters and nothing else, and the weight delta was 0.0000 on every row of the matrix [#0061/M/one-fixture] |

The ladder's shape matters more than any single constant.
Item state modifies hunger, thirst, endurance, stress, food sickness, boredom and unhappiness.
It does not modify the four nutrients at all, and the hunger and thirst ladders run their precedence in opposite orders.
A modifier that is absent is as load-bearing as one that is present, which is why the rows reading none are in the table at all.
A design that models cooking or rot through the nutrient columns is therefore modelling something vanilla leaves flat, and one that models it through hunger inherits a ladder it did not choose.

<a id="partial"></a>
### Partial eating

The eat menu offers the fractions 1, 0.5 and 0.25 [#0078].
Half is offered only when `abs(hungerChange * 100)` is at least 2 and at least half of `baseHunger`, and Quarter only when it is at least 4 and at least a quarter of `baseHunger` [#0079].

`baseHunger` is initialised equal to `hungChange` at instantiation and is deliberately not scaled by `multiplyFoodValues`, so it keeps the full-portion value while `hungChange` shrinks [#0080].
Because the fraction is a share of the whole item, eating a quarter of an already half-eaten item asks for half of what is left, and a leftover half-apple eaten at menu fraction 1.0 delivers 47.5 kcal rather than 95 — one item, measured on the server [#0081/M/one-fixture].
The same rescale arithmetic is duplicated in Lua twice, for the eat tooltip and for the utensil-scrape sound [#0082].
A mod that changes the rescale therefore has three sites to keep in step, not one.
Read live around three quarter eats of one item, the drop in raw hunger over `baseHunger` stayed at a quarter while the drop over the hunger before each eat ran a quarter, a third and a half — the fraction `Eat` applies to the live macros — so a share of the whole item and a fraction of what is left are two numbers on every eat after the first [#2831/M/n=1].
The rescale and the leftover scaling are complements, because what the fraction takes is what the multiply removes, and `baseHunger` is the one field that survives both untouched.
A partial eat lowers the item's stored calories, carbohydrates, proteins and lipids and its stored `hungChange` by one factor and never its `baseHunger`: `Eat` rescales the requested fraction to a share of what is left, adds `getCalories()` times that share to the nutrition store (divided by 5 when burnt), and then calls `multiplyFoodValues(1 - share)`, whose body holds no `setBaseHunger`; so the ratio of stored calories to `hungChange` survives every partial eat, and `getCalories() * getBaseHunger() / getHungChange()` read before an eat is the calories the instance held when `baseHunger` equalled `hungChange` [#3326/C/C-only].
The HUNGER an eat applies is the state-modified hunger times that fraction, added to the stat and clamped to its range, with the fraction taken as 1 whenever what would remain of the item's `hungChange` sits above -0.01; Eat Half and Eat Quarter request 0.5 and 0.25, and the eat action passes them to `Eat` unchanged [#3556/C/C-only].
The raw `hungChange` is the portion that three vanilla spending paths divide by — `Eat`'s fraction, a use-based `consumeHunger` and an evolved recipe's share of an ingredient — so a write to an instance's `hungChange` alone moves how much of the item each later portion takes, while a change to the HUNGER an eat already applied moves none of them [#3557/C/C-only].

The remainder is scaled by `multiplyFoodValues(1 - f)`, which multiplies fifteen stored fields including calories, carbohydrates, proteins and lipids, and truncates `fluReduction`, `foodSicknessChange` and `poisonPower` to int so those three erode faster than linearly; half an apple left `calories 47.5` and `hungChange -0.08` [#0057/M/one-fixture].

Three endings close the method.
At a fraction of exactly 1 the item's `hungChange` is set to 0 and `UseAndSync()` consumes it [#0058/M/one-fixture].
It does not stay 0: the consume step's use count is the hunger times 100, so the count it decrements is already 0, the setter clamps its argument at 0, the hunger it rescales by is a 0 over 0, and by the jar's reading the finished item's raw hunger and scaled fields are NaN, the raw hunger inferred from the NaN share a server-side wrapper computed after the eat and the item's own fields never read directly — a reader after the eat must treat a finishing eat as the whole remainder rather than divide by what the item says [#2832/M/n=1].
After the multiply, an item whose old `hungChange` was 0, whose old thirst was negative and whose new thirst is greater than -0.01 has its `hungChange` set to 0 and is consumed [#0059].
That is the crumb rule again, applied to what is left rather than to the fraction.
Otherwise a custom-weight item's weight becomes `(w - base) - f0 * (w - base) + base`, where `base` is the actual weight of its `replaceOnUse` item and 0 when it has none [#0060].

A cancelled eat is a partial eat too: it resolves on the server, and two guards there can make it apply nothing at all — no stats, no nutrition, no leftover scaling and no consumption ([#0112], [`../platform/mp-model.md#ownership`](../platform/mp-model.md#ownership)).
An item pass that rewrites hunger values across every food can land a value under that threshold and silently disable partial eating for it.
The guard sits on the cancel route only: a completed eat of an item whose hunger was driven under it, against a full-size base hunger, delivered the whole item, because the rescale clamps to 1 there [#2836/M/n=1].

<a id="fluid-path"></a>
### The drink path and the per-litre chain

A B42 drink is not a `Food` item: it is a `base:normal` item carrying a `component FluidContainer` joined to a `fluid` definition in `generated/fluids*.txt`, and `media/scripts/fluids/` does not exist — read from the script tree on the stamped build, not measured [#0603/C/snapshot].
Its numbers therefore come from the fluid, through the container, and they are per litre at the start of the chain and per container at the end of it.

The chain has five steps.
The loader stores a fluid's `Properties` as written: fifteen `equalsIgnoreCase` keys, each through `Float.parseFloat`, with no arithmetic [#0628].
Four of the fluid's getters then divide the stored value by 100 — `getHungerChange`, `getThirstChange`, `getStressChange` and `getFatigueChange` — while `getCalories` and the three macro getters do not [#0629].
The container multiplies the fluid's `Properties` by the litres it holds, so `getProperties()` is already litres-weighted and the whole per-litre convention lives in the container and never in the loader [#0630].
Those litres are a full container's: the initial amount defaults to `Capacity` when the script writes none, the `:share` suffix multiplies it and the add clamps to the capacity [#0632/C/snapshot].
Drinking then spends that litres-weighted aggregate times the fraction drunk [#0633].

The chain is measured and not only read: a full 0.3-litre can wrote 120.000031 calories, 31.200001 grams of carbohydrate, minus 0.036 hunger and minus 0.090 thirst — the per-container columns exactly, with the hundredfold division applied to the two stat columns on the way to the stats object — while the same can at half wrote 60.0 and 15.6 and was left holding 0.15 litres [#1892/M/n=1].
The fraction is a share of the container's current contents and not of its capacity, so on a full can a fraction of one empties it and a half halves it, but a second half takes half of what is left [#1733/C/C-only].

Some containers spawn part-filled rather than full.
`InitialPercentMin` and `InitialPercentMax` land in `initialAmountMin` and `initialAmountMax`, and the initial amount is the minimum when the two are equal and a uniform `Rand.Next(min, max)` otherwise, rolled once per container when it is read from its script [#0659].
Despite the key name the value is litres and not a percentage — nothing multiplies it by `Capacity` — which is why a water dish's 0.05 to 0.95 draw is clamped back to its 0.3-litre capacity and a cowboy canteen never spawns above 1 litre of its 1.8 [#0660].

The eat path and the drink path share no code at all, so a change made to one of them reaches the other only if it is made twice.
`DrinkFluid` is not `Eat` with a different argument.
It writes calories, carbohydrates, proteins and lipids from the container's `SealedFluidProperties` before any fluid is removed, with no burnt divisor and no other modifier [#0064/C/C-only].
It takes THIRST, HUNGER, ENDURANCE, STRESS, FATIGUE, BOREDOM and UNHAPPINESS from the `FluidConsume` that removing the fluid returns, and does not re-multiply them by the fraction [#0065/C/C-only].
It takes POISON from the container, multiplies it by 0.75 when the fluid is tainted, zeroes it with Iron Gut when tainted and otherwise halves it unless the primary fluid is bleach, and with Weak Stomach multiplies it by 1.2 when tainted or by 2 otherwise [#0066/C/C-only].
Four overloads funnel into the one method, which has no fraction clamp, no `baseHunger` rescale, no crumb rules, no `OnEat` hook, no `JustAteFood` and no eat packet, and never reads its boolean third argument [#0084/C/C-only].
Its Lua driver calls it incrementally during the action, consuming only the difference between the target ratio and what has already gone, so the call is idempotent; the update makes it when the process is not a client and the animation event when it is a server [#0085/C/C-only].
Drinking therefore completes on the server and sends only the player-stats sync, with no eat packet on this path, so a drink's calories reach a client only on the once-a-second player-stats packet [#0649].
When the removed `FluidConsume` carries alcohol, `DrinkFluid` hands it to `BodyDamage.JustDrankBoozeFluid` after its seven stat writes, and on a server its closing player-stats sync carries intoxication in its bitmask [#2925/C/C-only].
Beer's fluid carries 0.05 alcohol per litre, so a litre of beer drunk at hunger 0.6 or below adds 20 intoxication and half a litre 10 [#2926/C/arith.]; the writer and the decay are [the stat's](character-stats.md#tick-order).

What one call moves can be read off the container on either side of it.
One `DrinkFluid(FluidContainer, f, useUtensil)` call writes the four macros before any fluid is removed and takes its stats from what removing the container's amount times `f` returns, and its whole body holds no modData reference and no Lua call [#0064/C/C-only, #0065/C/C-only, #2687/C/C-only].
`FluidConsume`, the object the removal returns, extends `SealedFluidProperties` and declares only an amount and a poison effect of its own, so it carries the removed aggregate's nutrition with no per-fluid breakdown and the mix has to be sampled before the removal [#2688/C/C-only].
`ISDrinkFluidAction:updateEat` holds the drink action's one `DrinkFluid` call, `complete` reaches it unguarded, and it calls `syncItemFields()` right after each `DrinkFluid`; the gap it consumes and the `update` and animation-event gates are the incremental driver above [#0085/C/C-only, #2689/C/C-only].
Drinking straight from a world water source takes a second `DrinkFluid` route: `ISTakeWaterAction`, queued with no item, moves the litres into a temporary container and calls `DrinkFluid` on it with a fraction of 1 before disposing of the container [#2690/C/C-only].
A wrapper of the drink action's `updateEat` that samples the container's litres and mix before calling through and its litres after sees each sip once, and never sees a drink from a world source [#2689/C/C-only] [#2690/C/C-only].
The world-source route drinks in steps rather than in one transfer: its `new` sets the litres to drink to twice THIRST, capped by the source, and records twice THIRST as its start, and each `updateUse` transfers the target share less what it counts as drunk, which it reads back from THIRST itself [#2930/C/C-only].
Each step's litres pass through `transferFluid(_amount)`, which moves `_amount` litres into a temporary container of that capacity and drinks all of it, and which is reached from `update` off a client, from the `takeFluid` animation event on a server and from `complete` [#2931/C/C-only].
On a server the action is built by calling the type's `new` with the client's arguments, so the THIRST it starts from is the server's [#2932/C/C-only].
Measured live, the world-source drink runs on the server: queued from the client on a source 5.7 tiles away it dropped the server's THIRST from 0.4099 to 0.0012 within 7.3 s, and no drink wrapper sees it [#2942/M/n=1].
The auto-drink is a third route, a direct `DrinkFluid` call that no action wrapper sees [#2827/M/n=1].
It takes its water from the first water-only item in the top-level inventory list, every fluid in the `Water` category, skipping a tainted one only while the tainted-water text is on and taking one under 0.12 litres unless it is a bag [#2927/C/C-only].
The only `Water`-category fluids are water, tainted water and carbonated water, each worth 0.5 thirst per litre, so its `min(amount, 2 × thirst)` litres lower THIRST by half their volume and a THIRST drop across the call is twice that drop in litres [#2928/C/arith.].
It keeps no timer or cooldown, so a caller that restores THIRST between calls gets a drink on every call [#2929/C/C-only].
That route is measured on a live server: when a client queued the game's own drink action on a full 0.3-litre cola can, a wrapper of `updateEat` and of `complete` counted 29 `updateEat` calls and one `complete` on the server while the client's counters stayed at 0 (only the server install was read, so the client's install is not witnessed), and a half juice box added 32 more calls and one more completion, none of them on the client [#2825/M/n=1].
The timed action delivered what the direct call delivers, a full can 120.48 kcal after a drift correction and the half juice box 40.12, so the incremental calls sum to the container [#0148/M/n=1].
The shipped direct `DrinkFluid` call moved the store by the same 120 kcal and neither wrapper counted it, so a drink-action wrapper sees the action route and nothing else [#2827/M/n=1].
The auto-drink is measured live under a `CalculateStats` handler's call: THIRST held just under 0.1 drank nothing, crossing 0.1 drank 0.2001 litres, and THIRST written to 0.3 emptied the canteen's remaining 0.4289 litres by the next server tick and read 0.08608 at the first probe after the write, both branches of `min(amount, 2 × thirst)` [#2939/M/n=1].
No action wrapper saw any of the 0.9 litres it drank: a wrapper of `ISDrinkFluidAction:updateEat` counts none of it [#2940/M/n=1].
Under zeroed rise rates and a once-a-minute THIRST write the auto-drink still fires and its drop survives to the next write: measured live, a write of THIRST 0.3 to a player carrying a 0.9-litre canteen was followed within two server ticks by a 0.6-litre drink and THIRST 0, which held at all 36 per-tick samples until the next write, whose pre-write read was 0, and that write's 0.3 drank the remaining 0.3 litres within two ticks and left THIRST 0.15, which held at all 36 samples to the next write, whose pre-write read was 0.15 [#3382/M/n=1].
The server's `autoDrink` flag does not hold a Lua write: `setAutoDrink(false)` read back false and was true again 13.8 s later, so `setAutoDrink(false)` on the server cannot keep a player from auto-drinking, and the `AutoDrink` hook is unmeasured [#2941/M/n=1, #2769/C/C-only].
A drink action on a container the server has never seen raises in the server's `ISDrinkFluidAction.new` and drinks nothing [#2943/M/n=1].
How a container's mix is read from Lua, and why a per-fluid mod value cannot ride the fluid block, are [`../facts/food-item-model.md#fluid-blocks`](../facts/food-item-model.md#fluid-blocks)'s.
That packet's own field contract is [`../facts/wire-packets.md#player-stats-packet`](../facts/wire-packets.md#player-stats-packet).

Five traps sit on this path, and four of them are asymmetries with the eat path.
An endurance change is divided by 100 for an item but not for a fluid, and no shipped fluid writes a non-zero one, so a modded fluid's endurance value would be off by a hundredfold — read from the script tree on the stamped build, not measured [#0666/C/snapshot].
A fluid's `unhappyChange` is applied twice when the container is drunk, once to BOREDOM and once to UNHAPPINESS, so one drink moves both moodles by the container's whole aggregate: minus 3 on a full 0.3-litre cola can and minus 10 on a 0.2-litre juice box, the doubling being in the application rather than in the number [#0667/M/n=2].
`foodSicknessChange` has the opposite sign convention on the two paths, the drink path requiring a value above 0 and the eat path one below 0, and all 61 fluids write 0 [#0668/C/snapshot].
The fraction is unclamped in `DrinkFluid`, and the nutrition block multiplies before any clamp, so a fraction outside the range 0 to 1 would deliver nutrition the container never gave up [#0669].
`ISDrinkFromBottle` does not call `DrinkFluid` at all: it hardcodes a thirst change of -0.1 per use and delivers zero nutrition, and its only caller chain starts at a function with no caller anywhere in the shipped Lua, so it is dead code on this build [#0670/C/snapshot].

One identifier trap belongs with them.
`FluidDefinitionScript.Load` sets the enum fluid type and leaves the type string null when the fluid's name matches a built-in constant, and sets the modded type plus the string otherwise, the two routes being mutually exclusive, so the string names only 34 of the 61 definitions [#0654/M/n=2].
A census of fluids therefore pairs the string with the enum, or it silently loses the built-in half.

<a id="pill-path"></a>
### The pill path

For a `PillsVitamins` item `JustTookPill` adds the item's fatigue change to FATIGUE, halved when INTOXICATION is above 10, and then its stress change to STRESS [#2954/C/C-only].
It ends by calling the pill item's `OnEat` Lua function, when the drainable names one, with the item and the character, and then uses the item up one step [#2955/C/C-only].
Measured live, the action runs on the server: a `Base.PillsVitamins`, the caffeine-pill item with `fatigueChange = -4.0`, taken through the game's pill action lost one use on the server's copy, 1.0 to 0.8, and raised STRESS to 0.0077 and 0.0071 on two boots; with sleep allowed and needed FATIGUE fell from 0.6040 to 0.5641, and with sleep disabled the reset left no trace of it [#2952/M/n=1].
What a mod's eat and drink wrappers see of a pill is a reading of the mod, [testing-your-mod.md](../areas/testing-your-mod.md#scenario-inputs).

<a id="eat-type"></a>
### `EatType` and what the eat action does with it

`EatType` has no Java consumer and never touches hunger, thirst or nutrition: a jar-wide scan on 2026-09-10 found no site for it, only script generators [#0096/C/snapshot].
What it drives is presentation and one timing rule.
It picks the eat animation's food type and the second-hand utensil model, and the two pot types override the hand models with the item itself [#0097].
A two-hand bowl takes the spoon on its own early-return branch, while a can, a can drink, a two-hand item and a plate take the fork-or-spoon branch, and both branches feed the utensil flag [#0098].
A can or can drink eaten with a utensil plays the canned-scrape sound once the action passes 0.7 of its duration, and only when this eat finishes the item [#0099].
The key itself, and every other script key the loader reads, is [`../facts/food-item-model.md#script-keys`](../facts/food-item-model.md#script-keys).
Nothing on this list changes what an item delivers, so an item pass may set it for presentation alone.

<a id="duration"></a>
### The eat duration

The eat action sets its budget to 232 times the eating loop for food and 171 times the loop for a drink-type item, with the loop stepping to 2 and 3 at a hunger consumed of 30 and 80 for food or a thirst of 3 and 6 for a drink; one whole fresh apple reported a budget of 232.24, which is 232 times a loop of 1 times a body-temperature modifier of about 1.001 [#0071/M/one-fixture].
Four overrides sit after that arithmetic.
An item that consumes no hunger gets 460 [#0072].
A positive `EatTime` on the item hard-overrides the computed value [#0073].
A pop-can eat type gets 160 [#0074].
A character with the instant-timed-action cheat gets 1 [#0076].

Two adjustments frame it.
Eating with a utensil subtracts 1 from the eating loop when it is at least 2, which the drink branch undoes for drink-type items by reassigning the loop [#0049].
The base timed action then multiplies the whole budget by `(1 + UNHAPPY/4) x (1 + DRUNK/4) x (1 + handPain/300) x getTimedActionTimeModifier()`, with the hand-pain term skipped because the eat action ignores hand wounds [#0075].
The lines that compute a budget before all of this are dead, because they are unconditionally overwritten by the loop arithmetic [#0101].
Upstream of everything, the action refuses to start at a food-eaten moodle level of 3 or higher, and the menu shows a cannot-eat-more tooltip instead [#0077].

The real multiplayer path lands about 5.5 s after the action is queued — one session on a dedicated server with one client [#1189/M/n=1].
No duration term changes what a completed eat delivers, because the intake is fixed by the fraction the action was built with.
That budget is a tick count whose behaviour under an accelerated clock has never been measured.
A measurement that needs a known quantity of intake therefore drives the store on the server rather than queuing timed eats, because the intake is then exact and the timing is not in the reading at all.

<a id="overeating"></a>
### Eating when full

`IsoGameCharacter.Eat` refuses only an item that is not `Food`: it has no branch on the eater's HUNGER, and the only character stat it reads is FOOD_SICKNESS, for the sickness cure [#3596/C/C-only].
An eat at HUNGER 0 therefore still adds every macro in full, while the stat clamp discards the hunger it would have removed [#0021/M/one-fixture].
`JustAteFood` reads HUNGER once, at the health-from-food timer's gate, and its other stat writes are poison, pain, boredom and unhappiness [#3597/C/C-only], beside an alcoholic item's intoxication through `JustDrankBooze` [#2924/C/C-only].
Neither method names DISCOMFORT, so vanilla adds no sickness, discomfort or other stat for eating while full [#3597/C/C-only].
`Eat` adds the item's hunger change before it calls `JustAteFood`, so the gate reads the HUNGER the eat leaves behind [#3598/C/inference].
An eat fills the timer, and so can raise the FOOD_EATEN moodle, only when `abs(getHungerChange() * f)` is at least the HUNGER it found, whatever wrote that HUNGER last [#3598/C/inference].
A mod that writes HUNGER on the server therefore decides which eats raise the moodle, because HUNGER left above an item's hunger change keeps that item from filling the timer at all [#3598/C/inference].
The refusal at FOOD_EATEN level 3 lives in client Lua alone: the inventory menus hide the eat [#0522/C/C-only] and the action queue refuses a queued one [#3599/C/C-only].
The eat and drink actions' `isValidStart` is called only by the client's action queue when it starts the next queued action, an action queued into an empty queue begins without it, and no class in the jar names `isValidStart` [#3599/C/C-only].
A server-side `Eat`, whether another mod's or one a mod drives directly, meets no cap [#3599/C/C-only].

<a id="script-scale"></a>
### The script-to-instance scale

`Item.InstanceItem` divides the script's `HungerChange`, `ThirstChange` and `EnduranceChange` by 100 at instantiation, while `Calories`, `Carbohydrates`, `Lipids` and `Proteins` are stored unscaled [#0011/M/one-fixture].
The division exists because the two stats those keys feed run on a clamped unit range, which the ladder above records, while the nutrient stores do not and keep the script's own units.

The page's one worked value shows both halves at once: `Base.Apple` carries `hungChange -0.16`, `thirstChange -0.07`, `calories 95.0` and `carbohydrates 25.13` on an instantiated item, from script values `HungerChange -16`, `ThirstChange -7`, `Calories 95.0` and `Carbohydrates 25.13` [#0012/M/one-fixture].
Read it as the unit rule rather than as a fact about apples.
A value quoted from a script file and a value read off an instantiated item are therefore never directly comparable until it is said which of the two it is.
An item pass writes script units, an eat reads instance units, and the two differ by a hundredfold on three keys and not at all on four.
Every other per-food and per-fluid value is in the dataset rather than here ([`../reference/datasets.md`](../reference/datasets.md)).

<a id="sandbox"></a>
### The `Nutrition` sandbox option

The option is the only vanilla switch anywhere near this page, and it is narrower than its name suggests, because it gates the update tick and never the intake.

| Question | What is the case |
|---|---|
| what it gates | only `Nutrition.update()` — one early return skips the macro drain, the calorie update and the weight update, leaving the `Eat` and `DrinkFluid` store writes untouched [#0067] |
| what reads it | a whole-jar scan on 2026-09-10 returns exactly two sites, the constructor that creates the option and `Nutrition.update` [#0088/C/snapshot] |
| its default | registered with a Java default of false, while every shipped preset sets it true [#0086] |
| what the fixture reads | `Nutrition = true` [#0087/M/one-fixture] |
| what happens with it off | the stores keep filling to their clamps and nothing burns them, weight freezes, and the save file and the multiplayer packets still carry the values — read off the absence of any sandbox guard on the store-writing path, not measured [#0089/C/inference] |
| what it froze, measured | all three arms: with the option off the carbohydrate, lipid and protein stores, calories and weight each read the same value at every one of 73 hourly samples over three accelerated game-days, fasting and dosed alike, while the same fasting run with the option on moved every one of them in its first game-hour; the dosed run held calories above the gain threshold for eleven game-hours with weight unmoved, so the weight arm froze on its own [#1277/M/n=1] |
| a calorie write with it off | a server-side `setCalories` still lands and still clamps at 3700, and the written value then holds to the last digit between writes, so the ceiling lives in the setter; the eat itself was not driven in that run [#2754/M/n=1] |
| a second gate above it | `Nutrition.update` is not called at all when `SystemDisabler.doCharacterStats` is false [#0068] |
| flipping it at runtime | a flip through `getSandboxOptions():set(name, value)` takes and reads back in both directions, on one client-local flip each way with no push, so what the flip did to the server-side drain is not established [#0090/M/n=1] |
| the Lua mirror | `SandboxVars.Nutrition` stays stale after a runtime flip of the Java option [#0091/M/n=1] |
| pushing a flip | the setter writes only the local `ConfigOption`, and pushing a changed option to the server needs `SandboxOptions.sendToServer()`, which is the route the admin panel takes [#0092] |
| what one session could read of the gates | two of the update's three gates were read on both sides and were false throughout, so neither was exercised in its blocking state, and the third — the sandbox switch ahead of them — has no bus reader and was not read, and the two sides' world clocks had not diverged [#1501/M/n=1] |

The drain, the calorie burn and the weight model the option gates are [`../facts/body-and-weight.md#passive-burn`](../facts/body-and-weight.md#passive-burn) and [`../facts/nutrition-core.md#weight-model`](../facts/nutrition-core.md#weight-model), and their numbers are stated there rather than here.
The one thing the option cannot do is stop a store from filling, which is why a mod that wants to own the macro model turns the tick off and runs its own.

## Walls and bounds
<a id="walls"></a>

Every measured number on this page comes from the dedicated-server path with one client attached, on the fixture's defaults.
The eat matrix is one fixture across five items and five states, the partial-eat arms are one item each, the direct drink probe read the server only and the timed-action drink is one can of each of two fluids in one session [#0102/M/one-fixture, #0018/M/one-fixture, #0081/M/one-fixture, #2825/M/n=1].
Single player is never claimed anywhere on this page.
Where a row rests on one item or one session, its line says so, and widening it takes another run rather than another reading.
The nutrition mirror's gain and loss formulas and its calorie and macro ceilings match the jar and the measured clamps, so the mirror corroborates those two points and nothing else, its page being nine minors stale [#0132/M/one-fixture].

- The mirror says that as food begins to rot its effects become more negative, read as a blanket statement; rot leaves all four nutrients untouched and moves neither thirst nor endurance, and only hunger divided by 2.2, stress divided by 2, boredom and unhappiness at plus 20 and the sickness roll degrade, the measured arm being rotten bread, which delivered its full 532 kcal and 99 g of carbohydrate [#0133/M/one-fixture].
- The mirror says burnt food loses most of its positive effects and never quantifies it; burnt is the one real nutrition modifier in the game, `Eat` dividing all four nutrients by 5 for a burnt item while thirst is divided by 5 and hunger by 3, measured on four items [#0134/M/one-fixture].
- The mirror's nutritional-values rows are state-free; that holds for the macros but not for hunger, which is scaled by 1.3 cooked, a third burnt, 1.3 stale and 2.2 rotten, and the mirror's hunger column is the raw script value rather than an arithmetic one [#0135/M/one-fixture].
- The mirror says the weight simulation is always on and never mentions the sandbox option; the option gates the update tick — drain, burn and weight — while intake continues unguarded [#0136].
- Protein does reach one vanilla consumer on this build, the Strength experience grant, stated at [perks-and-strength.md#xp-grants](perks-and-strength.md#xp-grants); its only other reader outside the weight model is the recovery modifier, stated at [nutrition-core.md#macro-effects](nutrition-core.md#macro-effects).
- `Eat` has no skill term on the intake path; the Cooking skill raises an evolved dish's macros at build time through the summation's skill bonus and leaves its hunger unchanged, so the mirror's claim that cooking increases the nutrition of evolved recipes holds for the macros and not for hunger, as [cooking-and-recipes.md](cooking-and-recipes.md#evolved) measures [#2691/M/n=1].

The walls these mechanisms close are stated once each on the wall map.
A mod can run its intake math where `Eat` runs, which is the server ([#1128/M/n=1]).
Intercepting an eat before vanilla's numbers land needs a server-side Lua wrapper of the eat action's completion step ([#1129/M/n=1], [`../platform/lua-platform.md#script-hooks`](../platform/lua-platform.md#script-hooks)).
Correcting intake afterwards from `OnEat` is a workaround rather than a hook that runs first ([#1130/M/n=1]).
A partial or cancelled eat is handled, with the two cancel guards above as the catch ([#1132/C/C-only]).
A direct `Eat` still moves the macro stores [#0006] [#0067].
The drink path can be hooked the way the eat path is, through a server-side wrapper of the drink action rather than a named hook ([#1133/M/n=1], [#1279/M/n=1]).
Turning vanilla nutrition off and owning the macro model is the sandbox option's one lever ([#1127/C/C-only], [#1136/C/C-only]).
Not covered: the food-to-health loop and the sickness rolls beyond their call sites, the fluid container's own save and sync routines, and single player — no reading on this page was taken outside the dedicated-server path; what a cooked or crafted item carries into the eat is [cooking-and-recipes.md](cooking-and-recipes.md#evolved)'s.

## Open
<a id="open"></a>

- Whether a timed action's tick budget scales with an accelerated clock — settled by one queued eat at a raised time speed against the pair already taken at normal speed; both existing measurements ran at normal speed, the observed 42 or more ticks per wall second is consistent with a per-frame budget rather than a game-clock interval, and no accelerated run exists; no `X` id [#0141/M/n=2/open].
- How far weight and hunger drift apart on a part-eaten custom-weight item, and whether the `f0` write is intentional — settled by eating a canned food a quarter at a time and logging its weight, `hungChange` and `baseHunger` at each step; no `X` id [#0142/C/open].
- Which items ever set `baseHunger` different from `hungChange` at spawn — a split scales both fields of its input by one ratio, so a part-eaten input's unequal pair carries onto the output, the butcher paths and the Java craft summation set the two from one value, and `RecipeCodeOnCreate.makeCoffee` and `ItemStatsPacket.applyItemStats` are unread; settled by reading those two writers and whether an `InheritFood` input can be part-eaten; no `X` id [#0143/C/open].
- What `getHealthFromFoodTimeByHunger()` returns — settled by a jar dump of the method, which scales the food-to-health loop rather than intake; no `X` id [#0146/C/open].
- Whether any vanilla item sets `DaysFresh` equal to `DaysTotallyRotten`, the shape that makes the rot-roll denominator take the hundred-per-cent branch — settled by scanning the food script for that pair; no `X` id [#0147/C/open].
- Two drink corners are unmeasured, cancel semantics and the 100 ms animation-event cadence under an accelerated clock, and the client's arrival is bounded only to a poll — settled by a drink cancelled partway and a drink at a raised time speed, each read on both sides; no `X` id [#2829/M/n=1/open].
- Decision: whether the mod's intake math runs in a server-side wrapper of the eat action's completion step or in `OnEat` — by the time `OnEat` fires, `Eat` has already written every stat and every nutrient [#0008].
- Decision: whether a rebalanced hunger value is allowed to land under the magnitude the cancel guard tests — a cancelled eat of such an item applies nothing at all ([#0112], [`../platform/mp-model.md#ownership`](../platform/mp-model.md#ownership)).
- Decision: whether the mod ships expecting the sandbox `Nutrition` option on or off — with it off the stores keep filling to their clamps and nothing burns them [#0089/C/inference].
- Decision: whether the mod's own nutrient numbers for a container are per litre or per container — a fluid's properties are per litre and the container multiplies them by the litres it holds [#0630].
- Decision: whether the mod's drink accounting wraps the drink action's `updateEat` alone or also the world-water route, since drinking from a world source never passes through the drink action [#2690/C/C-only].
- Whether a script `OnEat` given to the vitamin pill by a mod's item block runs on the server when the pill is taken — settled by a pill taken with one assigned, counting its calls on both sides; -> [X59](../areas/open-questions.md#x59) [#2960/C/C-only/open].

## See also

- [`../platform/lua-platform.md#script-hooks`](../platform/lua-platform.md#script-hooks) — how `OnEat` resolves, which side calls it, what the client-side twin does not apply, and where a server-side wrapper of a timed action sits.
- [`../platform/mp-model.md#ownership`](../platform/mp-model.md#ownership) — which side owns the stores, and where a cancelled eat resolves.
- [`../facts/wire-packets.md#eat-food-packet`](../facts/wire-packets.md#eat-food-packet) — what the eat packet carries and what its handlers do not apply.
- [`../facts/nutrition-core.md#clamps`](../facts/nutrition-core.md#clamps) — the store clamps every intake on this page ends against.
- [`../facts/body-and-weight.md#passive-burn`](../facts/body-and-weight.md#passive-burn) — the drain and the burn the sandbox option gates.
- [`../facts/food-item-model.md#script-keys`](../facts/food-item-model.md#script-keys) — the script keys the loader reads, and [`#poison`](../facts/food-item-model.md#poison) for the poison and sickness rolls the eat path runs.
- [`../reference/datasets.md`](../reference/datasets.md) — every per-food and per-fluid number this page does not state.
- [`../reference/experiments.md`](../reference/experiments.md) — the named experiments the open rows point at.
