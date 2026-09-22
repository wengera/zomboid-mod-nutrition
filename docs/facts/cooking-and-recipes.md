# Cooking and recipes
Verified against 42.20.4 (b0bbce05d5) · 2026-09-22 · scope: the cook and burn transitions, what a craft recipe's inputs really cost, the evolved-recipe summation and the join that feeds it, the nutrition delta of a type change, and how far the two recipe datasets were checked against the running game; the script grammar is handed to `platform/loader-and-scripts.md`, the eat-time ladders to `facts/eating-pipeline.md` and rot to `facts/spoilage.md`.

## Key facts

- The cooking block ticks once per distinct game minute and each tick adds `heat` divided by 1.5 to `cookingTime` [#0260, #0261/M/n=1].
- A cooking tick is multiplied by 0.05 when the container's own temperature is 1.6 or below, so a hot item in a cool container cooks at a twentieth of the rate [#0262/M/n=1].
- `cookingTime` above `minutesToCook` flips the item cooked, and above `minutesToBurn` sets `burnt` and clears `cooked` [#0263/M/n=1, #0264/M/n=1].
- Cooking and burning leave an item's stored nutrition untouched: 220 kcal before and after and a raw `hungChange` still -0.4, while the read-time `getHungerChange` drops to -0.133333 on the burnt item [#0277/M/n=1].
- One recipe input use is one raw `HungerChange` point, so an input of N on a food row whose `HungerChange` magnitude exceeds 1 costs N divided by that magnitude of one item [#0701/M/n=3].
- Spending 10 of `Base.Icecream`'s 30 uses scaled every macro by one minus used over current uses, taking calories 1680 to 1120 [#0709/M/n=1].
- An evolved recipe consumes 1 less 0.03 times the Cooking level of each ingredient, so 70 per cent of it is spent at Cooking 10 [#0290/M/n=1].
- The evolved skill bonus is 1 plus the Cooking level over 15, which is 1.0 at Cooking 0 and 1.6667 at Cooking 10 [#0292/M/n=1].
- Macros per unit of dish hunger scale by 1.0 at Cooking 0 and 1.1667 at Cooking 10 while the share is below 1 [#0293/M/n=1].
- 68 kcal of ingredients produce 68.0 kcal of outputs at Cooking 0 and 79.667 kcal at Cooking 10, a gain the summation creates from nothing [#0304/M/n=1].
- The game's own `ScriptManager` answers 969 craft recipes, 63 evolved recipes and 0 legacy recipes [#0679/M/n=1].
- Cooking as such moves no calories anywhere in the recipe data: every non-zero craft delta is a recipe that changes what the item is [#0742/C/snapshot].
- 15 of the 31 resolvable craft rows are non-zero in calories, and everything else reading 0 is conservation [#0750/C/snapshot].
- The template arm does the evolved join's work: `resolvedVia` is `template` on 4 748 rows, `both` on 2 133 and `name` on 0 [#0720/C/snapshot].
- The Cooking perk level that scales the summation is server-owned, so `skillBonus` and `share` are the server's whatever the client UI shows [#0759/M/n=1].

## How it works

<a id="cook-block"></a>
### The cook block

Everything the game does about heat and food is one branch of one method, so a mod that wants different cooking behaviour changes the item's own script values, the container it sits in, or the replacement it turns into.

The game has no separate oven or campfire class: `Food.update()` is the only cooking driver and an appliance contributes only through `ItemContainer.getTemprature()` [#0256].

`Food.update` recalculates the time multiplier, forces `cooked` for the already-cooked tag, updates temperature, ages the item when it is the server, and then, once per game minute while the item is cookable, unfrozen and above the heat gate, accumulates `cookingTime`, flips `cooked` and then `burnt`, rolls for a kitchen fire, and finally calls `updateRotting` [#0257]:

```java
void Food.update() {                                                     // L359
    calculateTimeMultiplier();                                           // @0  L359
    if (hasTag(ALREADY_COOKED)) setCooked(true);                         // @4  L361-362
    updateTemperature(); checkEggHatch(null);                            // @19 L364-365
    ItemContainer c = getOutermostContainer();                           // @29 L367
    if (c != null) {
        if (GameServer.server) updateAge(false);                         // @38 L369-370
        if (isCookable && !isFrozen()) {
            if (heat <= 1.6f) goto ROT;                                  // @63 L373   HEAT GATE
            int minute = GameTime.getInstance().getMinutes();
            if (minute != lastCookMinute) {                              // @86 L377   ONE TICK / GAME MINUTE
                lastCookMinute = minute;
                float d = heat / 1.5f;                                   // @109 L382
                if (c.getTemprature() <= 1.6f) d *= 0.05f;               // @118 L384-385  residual heat
                cookingTime += d;                                        // @135 L387
                if (isTainted && cookingTime > min(minutesToCook, 10f)) isTainted = false;  // @156 L393-394
                if (!isCooked() && !burnt
                    && (cookingTime > minutesToCook || cookingTime > minutesToBurn)) {      // @186 L397
                    if (getReplaceOnCooked() != null && !isRotten()) { …replace…; return; } // @224 L398–421
                    setCooked(true);                                     // @413 L423
                    …removeUnhappinessWhenCooked, rice/pasta clock reset,
                      RemoveNegativeEffectOnCooked, OnCooked hook, microwave penalty…
                    if (chef != null && !hasTag(NO_COOKING_XP) && !isRotten()) award 10 Cooking XP;
                }
                if (cookingTime > minutesToBurn) { burnt = true; setCooked(false); }        // @894 L494–496
                …kitchen-fire roll…
            }
        } else if (isTainted && heat > 1.6f && !isFrozen()) { …boil tainted water… }        // @1155 L523
    }
ROT: updateRotting(c);                                                   // @1255 L543
}
```

The whole cooking block is gated on the item being cookable and not frozen [#0258].

It needs the item's own `heat` above 1.6, and the container must also be above 1.6 for the full rate [#0259/M/n=1].

The block ticks once per distinct game minute [#0260].

Each tick adds `heat` divided by 1.5 to `cookingTime`, multiplied by 0.05 when the container's own temperature is 1.6 or below, so a hot item in a cool container cooks at a twentieth of the rate [#0261/M/n=1, #0262/M/n=1, #1209/C/C-only].

Both arms were measured on one item on one fixture in a player inventory at container temperature 1.0, which is the residual arm only: the cook tick added 0.059658 against 0.059660 predicted at heat 1.78979, and the burn tick 0.061172 against 0.061171 at heat 1.83512 [#0259/M/n=1, #0261/M/n=1, #0262/M/n=1].

`cookingTime` above `minutesToCook` flips the item cooked, measured on one `Base.Steak` with `MinutesToCook 50` primed to 51 and ticked once with no appliance [#0263/M/n=1].

`cookingTime` above `minutesToBurn` sets `burnt` and clears `cooked`, measured on the same steak with `MinutesToBurn 70` primed to 71 [#0264/M/n=1].

`setCooked(true)` and `setBurnt(true)` are ungated and sticky, and each also raises `cookingTime` to its own threshold when it is below, which is why an item that is not cookable can still be cooked [#0265].

On the cook transition and only when the item is not rotten, `ReplaceOnCooked` adds each named item with the condition states copied over, removes the original and returns from `Food.update`, so the item is replaced and never flagged cooked [#0266].

For ten named rice, pasta, water-pot and bowl types the cook transition rewrites the age axis to `age` 0, `offAge` 1 and `offAgeMax` 2 [#0268].

On the cook transition in a microwave container a `BadInMicrowave` item gets `unhappyChange` 5, `boredomChange` 5 and `cookedInMicrowave` 1 [#0269].

A cookable item loses its tainted flag once `cookingTime` passes the smaller of `minutesToCook` and 10, while a non-cookable container boils taint off at 1.0 per minute, or 0.2 with the residual factor, past 10.0 [#0270].

The cook transition awards 10.0 Cooking experience, skipped for the no-cooking-experience tag or a rotten item [#0271].

That grant lands on the server: the credited delta was 2.5 with a chef set and 0 with it unset, because a default character's empty experience-boost map puts the 10.0 on the quarter arm, a ladder read from the code rather than measured [#1413/M/n=1].

The scripted last-cook-minute flip is not a precondition of the transition: across two sessions the cooking block had already been entered twice 1.33 to 1.67 game minutes apart on one and the transition fired 907 ms before the flip reached the server on the other, so heat above the gate plus a cooking time past minutes-to-cook suffice and the minute gate reopens by itself within one game minute; the write is sent after the transition on the second run, so the pair proves the flip unnecessary and nothing else [#1418/M/n=2].

A kitchen fire needs the item burnt with `cookingTime` at least 50 and at least twice `minutesToCook` plus half `minutesToBurn`, then rolls a framerate-adjusted 1 in 200 per minute on a powered non-campfire grid, starting a fire of strength 500000 and clearing the item's cookable flag [#0272].

`getHeat()` returns the raw `Food.heat`, on which 1.0 is ambient and 0.2 a powered fridge, while the inventory remap is half of heat less one above 1 and one less heat less 0.2 over 0.8 below it; the source gives no bytecode offset for either getter [#0274/C/C-only].

`IsoStove.getCurrentTemperature()` returns the stove temperature plus 100 over 100, so an item needs a stove above 60 to pass the heat gate, while a microwave jumps straight to its maximum temperature; the 60 is derived from the ramp formula rather than measured [#0275/C/arith.].

The carrier for a cooking item's client copy is that same block's `sendItemStats`, gated on `isCookable && !isFrozen() && heat > 1.6f` and fired once per game minute, read from the code on this build [#1206/C/C-only].

<a id="uses"></a>
### Recipe IO and the uses-not-items rule

The `craftRecipe` block, its IO line grammar and the keys a mod may set are general to any mod and live in [the loader page](../platform/loader-and-scripts.md#craft-recipe-grammar); what follows is only what an input line costs a food item and what an output carries away.

Of the flags a line can carry, only `ItemCount`, `InheritFoodAge` and `InheritFood` change what an input line costs or what an output carries; the others do not [#0689].

The recipe input count is not the number of input lines: a leading minus or plus marks a fluid sub-line that the loader attaches to the preceding input instead of adding it to `inputs`, and the count is that list's size, so a recipe written with a fluid sub-line answers one less than its script has lines [#0695/M/n=10, #1737/C/C-only].

The dataset nests those 55 sub-lines under the input above them and publishes `inputCount` as the loader's own `inputs.size()`, the same number the game's counter answered over ten recipes on one boot [#0695/M/n=10, #1737/C/C-only].

An input line is consumed unless it is `mode:keep`: both no `mode:` and `mode:destroy` consume, because the reduction is skipped only when keep is true [#0694].

A `mode:keep` line costs nothing: it selects and reserves an item, rolls its `MayDegrade*` check and is never reduced [#0699].

A line flagged `ItemCount` costs N whole items: the consumption takes 1f per item and the destroy pass spends each item's whole remaining uses [#0700].

Everything else is charged in uses, and one use is one raw `HungerChange` point: `getMaxUses` is the integer of `abs(baseHunger × 100)` and the reduction runs `setCurrentUses` into `consumeHunger` into `multiplyFoodValues(1 − consumed / abs(hungChange))` [#0701/M/n=3].

So an input of N on a food row whose `HungerChange` magnitude exceeds 1 costs N divided by that magnitude of one item, measured on three items on one boot and read server-side [#0701/M/n=3].

A food row with no usable `HungerChange` costs N whole items, because `getMaxUses` returns 1 when `baseHunger` is 0, and the row's `delta.notes` names the case rather than silently scaling it [#0702].

A drainable input is charged no macros, with a note: a drainable's uses are `UseDelta` steps of a bar rather than nutrition [#0703].

A `mode:destroy` line that is not flagged `ItemCount` is charged up to the whole items `RemoveItem` deletes, and the annihilated remainder is published as `delta.destroyWaste` so that both hunger points moved and food removed from the world stay recoverable [#0704].

An input flagged `InheritFood` makes the craft a split — the output takes one over the output count of the consumed instance's macros — so that input and every output drop out of the sum and the delta is 0 by construction; on the 2026-09-10 scan 17 recipes carry the flag, 8 of them resolvable and all 8 zero in all six macros [#0706/C/snapshot].

`InheritFoodAge` is not a split: it copies age only, which is why `ScoopIceCream` carries it and still costs 560 kcal of ice cream [#0707].

An output line is always an item count: the output builder loops N times and each result carries its own script macros [#0708].

A craft's outputs are built before the inputs are reduced [#0740].

Spending 10 of `Base.Icecream`'s 30 uses scaled every macro by one minus used over current uses: `hungChange` −0.30 to −0.20, calories 1680 to 1120, carbohydrates 180 to 120, lipids 84 to 56 and proteins 26 to 17.333334 [#0709/M/n=1].

That single item is the whole measured base of the fractional half of the rule, read server-side inside one Lua call on one boot [#0709/M/n=1].

Spending all 40 of `Base.MincedMeat`'s uses took `hungChange` −0.40 to 0, calories 300 to 0, lipids 30 to 0 and proteins 46 to 0, with carbohydrates already 0 [#0710/M/n=1].

Spending all 15 of `Base.Cheese`'s uses took `hungChange` −0.15 to 0, calories 113 to 0, carbohydrates 0.87 to 0, lipids 9.33 to 0 and proteins 6.4 to 0 [#0711/M/n=1].

Across those three items the probe matched 96 of 96 compared fields with an empty mismatch list [#0712/M/n=3].

`getMaxUses()` and `baseHunger` did not move across the reduction, so the denominator of the scaling is `currentUses`, equal to `maxUses` only while the item is whole [#0713/M/n=3].

<a id="evolved"></a>
### The evolved summation

An evolved recipe is the only place in the game where nutrition is moved between item instances rather than read off a script, and the whole of it is one Java method.

`EvolvedRecipe.addItem` turns the base into the result item with zeroed macros, re-seeds them from the base food, carries the base's age across proportionally, and then per ingredient computes the hunger it spends, clamps it to the ingredient, shrinks it by 3 per cent per Cooking level, derives a share, adds the ingredient's macros times the skill bonus times that share to the dish, and removes the macros times that share from the ingredient [#0283]:

```java
float hunger           = itemRecipe.use / 100.0f;                        // @518 L333
if (ingredient.isRotten())   hunger = 0.05 or 0.10 × |baseHunger|;       // @800–@915 L366–369  (Cooking 7-8 / 9-10)
if (|ing.getHungerChange()| < hunger) hunger = |DECIMAL_FORMAT(ing.getHungerChange())|;  // @934 L374–376
float hungerAfterSkill = hunger - (3f * cookLvl / 100f) * hunger;        // @1142 L401   −3 %/level
float share            = min(|hungerAfterSkill / ing.getHungChange()|, 1f);              // @1159 L402–404
float skillBonus       = 1f + cookLvl / 15f;                             // @1217 L411   +6.67 %/level

dish.calories      += ing.getCalories()      * skillBonus * share;       // @1228 L412
dish.proteins      += ing.getProteins()      * skillBonus * share;       // @1250 L413
dish.carbohydrates += ing.getCarbohydrates() * skillBonus * share;       // @1272 L414
dish.lipids        += ing.getLipids()        * skillBonus * share;       // @1294 L415
float thirst = ing.getThirstChangeUnmodified() * skillBonus * share;     // @1316 L416  (skipped for tag DRIED_FOOD)

dish.hungChange -= hunger;  dish.baseHunger -= hunger;                   // @990/@1003 L380-381
if (ing.isCooked()) hungerAfterSkill /= 1.3;                             // @1353 L420-421
ing.hungChange  += hungerAfterSkill;   ing.baseHunger += hungerAfterSkill;// @1371 L424-425
ing.calories    -= ing.calories * share;  … same for the other three …   // @1429–@1486 L428–431
```

Phase A zeroes the result item's macros and then re-seeds them from the base food itself, so a pot of water contributes its own values [#0284].

The dish's age is carried across proportionally as the new `offAgeMax` times the old `age` over the old `offAgeMax`, and only when both items have real thresholds [#0285].

An ingredient's `Name:use` points are hunger points: the summation divides `use` by 100 to get the hunger that ingredient spends, measured across two ingredients in one dish at two Cooking levels on one fixture [#0286/M/n=1].

A rotten ingredient spends 0.05 of the base's hunger at Cooking 7 or 8 and 0.10 at Cooking 9 or 10, and is refused below Cooking 7 [#0287].

The hunger an ingredient spends is clamped to the absolute value of its own `getHungerChange()` before the Cooking reduction, so a key that asks for more hunger than the ingredient carries can only ever spend the whole ingredient [#0288].

An evolved recipe consumes 1 less 0.03 times the Cooking level of an ingredient and banks its macros at the skill bonus times that same factor, measured on one dish across two perk levels in one session as a consumption share of 0.33333 falling to 0.23333, exactly 0.70 of it [#0290/M/n=1, #1210/M/n=1].

The share an ingredient gives up is the smaller of 1 and the absolute ratio of the skill-shrunk hunger to the ingredient's own stored hunger, so it is capped at the whole ingredient, and it stayed below 1 in every measured arm [#0291/M/n=1].

The skill bonus is 1 plus the Cooking level over 15, so 1.0 at Cooking 0 and 1.6667 at Cooking 10 [#0292/M/n=1].

Macros per unit of dish hunger therefore scale by the skill bonus times one less 0.03 times the Cooking level while the share is below 1, which is 1.0 at Cooking 0 and 1.1667 at Cooking 10 [#0293/M/n=1].

That same factor is 1.168 at Cooking 9, so Cooking 10 lands fractionally below Cooking 9 at 1.16667; the level-9 value is computed from the two expressions and not measured at that level [#0294/C/arith., #1211/M/n=1].

The dish gains an ingredient's macros times the skill bonus times the share while the ingredient loses only the macros times the share, so the gain-to-loss ratio is the skill bonus, up to 1.6667 at Cooking 10 [#0295/M/n=1].

A `Spice` ingredient takes the spice branch: no hunger and no macro transfer, it does not count against `MaxItems`, and it may be added once per dish [#0296].

A herbal-tea ingredient additionally sums `foodSicknessChange` capped at 12, `painReduction`, `fluReduction`, `stressChange` and `reduceInfectionPower` onto the dish [#0297].

A dish's `unhappyChange` is the unmodified value less five less five per duplicate, clamped at plus 25, with a further over-stuffing term once the extra-item count less two exceeds the chef's Cooking level [#0298].

A dish's `boredomChange` is zeroed once in phase A and never touched again [#0299].

A Salad built from a bowl, a lettuce and a tomato banks 24.999998 kcal, 5.193333 carbohydrates, 0.28 lipids and 2.283333 proteins at Cooking 0, and 29.166666, 6.058888, 0.326667 and 2.663889 at Cooking 10 [#0301/M/n=1].

Every one of those cells matches the summation to six decimal places, on one fixture with fresh ingredients per round and the perk pinned on the server [#0301/M/n=1].

Cooking skill does not change a dish's hunger: the same Salad reads a stored hunger of -0.11 at Cooking 0 and at Cooking 10 [#0302/M/n=1].

A dish's `thirstChange` scales with the skill bonus times the share, measured at -0.063333 at Cooking 0 and -0.073889 at Cooking 10, and the transfer is skipped for the dried-food tag [#0303/M/n=1].

68 kcal of ingredients produce 68.0 kcal of outputs at Cooking 0 and 79.667 kcal at Cooking 10, a 17.2 per cent gain the summation creates from nothing [#0304/M/n=1].

Those totals are summed from the measured per-item values of that one dish with its two ingredients at two Cooking levels [#0304/M/n=1].

The timed action's call of the recipe's add-item method is the only Lua-to-Java bridge into the summation [#0325].

The Cooking perk level that scales it is server-owned, so a client-side perk write silently runs the recipe at the server's level and both `skillBonus` and `share` are the server's whatever the client UI shows [#0759/M/n=1].

`data/evolved-recipes.json` applies the whole non-rotten path of that block per recipe-and-ingredient row at Cooking 0 and Cooking 10, carrying every term of the hunger, `hungerAfterSkill`, `share`, `skillBonus`, four-macro and thirst arithmetic in `at0` and `at10` rather than only the results [#0728].

The hunger clamp bites on 59 of the 6 881 rows from 17 over-asking keys on the 2026-09-10 scan, so `Base.Cherry`'s `Oatmeal:5` against a hunger of 3 is a `share` of 0.7 at Cooking 10 rather than 1.0 [#0729/C/snapshot].

A `DRIED_FOOD`-tagged ingredient adds no thirst, and the skip bites on 27 rows — `Base.Ramen`, `Base.Macaroni` and `Base.Pasta` across nine recipes each — while the tag is on 577 rows in all, the other 550 having a thirst term already 0 [#0730/C/snapshot].

A `Spice = true` ingredient returns before the hunger lines, so `share`, hunger, `hungerAfterSkill` and every macro are 0 on all 2 522 spice rows — measured zeroes named by the row's note, not absences [#0731/C/snapshot].

A non-`per_item` ingredient row would carry null macros with a reason and still emit the hunger arithmetic, and it never fires on vanilla because all 374 carriers are `per_item` [#0733/C/snapshot].

The generated Salad rows reproduce the measured dish: lettuce `share` 0.333333 and 0.233333, tomato 0.5 and 0.35, `skillBonus` 1.0 and 1.6667, and a dish of 25.0 kcal at Cooking 0 and 29.1667 at Cooking 10, the dataset side being arithmetic on code constants against the one measured dish [#0734/M/arith.].

<a id="evolved-join"></a>
### How an item reaches an evolved recipe

No recipe lists its own ingredients: the carrier item names the recipe, and the loader builds the ingredient list from those keys at script-load time.

`Item.OnScriptsLoaded` attaches an item's `EvolvedRecipe = <Name>:<use>` key, optionally suffixed `Cooked`, through two arms, with the five parse-time aliases applied first in `Item.DoParam` [#0718].

It attaches the key to the recipe whose name matches and to every recipe whose `Template` equals that key [#0280].

The first arm is an exact, case-sensitive map lookup through `ScriptManager.getEvolvedRecipe(key)` [#0719].

The second arm takes every recipe whose `Template` matches the key case-insensitively and does the work: on the 2026-09-10 scan `resolvedVia` is `template` on 4 748 rows, `both` on 2 133 and `name` on 0 [#0720/C/snapshot].

Five key parts do match by name alone — `Waffles:8` on `Base.DriedApricots` and `Stir fry Griddle Pan` on the three pumpkins and `Base.Soybeans` — but each of those items also writes another key that reaches the same recipe by template, so every row merges to `both` [#0721/C/snapshot].

The five parse-time aliases are really used on 5 key parts — `RicePan` three times, `RicePot` once and `Roasted Vegetables` once — and unaliased, `RicePan:1` would reach 1 recipe instead of 4; none of the run's five evolved probes is an alias target, so this is a code reading only [#0722/C/C-only].

`item Cinnamon` writes `ConeIceCream:1` against a recipe and template spelled `ConeIcecream` — the only miscased key in the install — so it resolves through the template arm, and a case-sensitive expansion loses exactly that pair and reports a false unmatched key [#0723/M/n=1].

An `EvolvedRecipe` key that matches no recipe name and no template throws `InvalidParameterException` [#0281].

The `evolvedrecipe` block takes twelve keys: `BaseItem`, `Name`, `ResultItem`, `Cookable` on 44 blocks, `MaxItems`, `AddIngredientIfCooked` on 37, `AddIngredientSound` on 11, `CanAddSpicesEmpty` on 42, `Template`, and `MinimumWater` on 20 [#0282/C/snapshot].

The remaining two, `IsHidden` and `AllowFrozenItem`, are recognised by the loader and used by no block, counted over the 62 blocks on the 2026-09-10 scan — the 62 in `evolvedrecipes.txt` plus `AddBaitToChum`, written in a fishing recipe file, being the 63 evolved recipes the game loads [#0282/C/snapshot, #0679/M/n=1].

An ingredient is refused when its `use` is -1, when it is burnt, when it is rotten and the chef is below Cooking 7, when it is frozen and the recipe does not set `AllowFrozenItem`, when it is dangerous uncooked and uncooked and the result is not cookable, when it is not a spice and the extra-item list has reached `MaxItems`, or when `MinimumWater` exceeds the water in the base's fluid container [#0300].

`AllowFrozenItem` is never set in vanilla, and the source gives no bytecode offset for the usability check itself [#0300].

189 items write a `Salad:` key — 187 in `items/food.txt` and 2 in `items/drainable.txt`, `Base.Vinegar2` and `Base.Vinegar_Jug`, both `Spice = true` — and the live ingredient count is 189 for both `Salad` and `SaladClay` [#0763/M/n=2].

`isCookable()` is set by the presence of the `Cookable` key and never reads the parsed value: `AddBaitToChum` writes `Cookable = false` and the game answers true, the only one of the 63 evolved recipes where a faithful text read and the game disagree, which is why the dataset carries the script value [#0766/M/n=1].

`getResultItem()` strips the module, so a live `Salad` has to be compared against the dataset's `Base.Salad`, while `getBaseItem` is unstripped [#0767/M/n=5].

The evolved-recipe context menu is three sites in the inventory pane's context menu: the probe that asks whether any evolved recipe applies, the submenu build, and the action queue that starts the add [#0326].

<a id="type-change"></a>
### What a type change moves

A craft or a cook transition can change an item's nutrition only by replacing the item with one whose script declares different values, so every delta on this page is a difference between two script blocks weighed by what the inputs cost.

Cooking and burning leave an item's stored nutrition untouched: 220 kcal before and after and a raw `hungChange` still -0.4, while the read-time `getHungerChange` drops to -0.133333 on the burnt item, measured over one cook and one burn transition on one item [#0277/M/n=1].

`MakeToast` moves no macro either: `Base.BreadSlices` and `Base.Toast` both declare 177 kcal, 33 g carbohydrates, 2.22 g lipids and 5.9 g proteins, and differ only in `HungerChange`, −10 against −8 [#0741/C/arith.].

Its delta is therefore 0 in all four macros with `hungerChange` +2.0, and `absentMacros` names the two thirst lines neither block writes [#0741/C/arith.].

Cooking as such moves no calories anywhere in the recipe data: every non-zero craft delta is a recipe that changes what the item is [#0742/C/snapshot].

The 31 resolvable craft deltas, largest absolute calorie change first, with each recipe's consumed inputs, produced outputs, calorie delta and hunger delta, on the 2026-09-10 scan; `[IC]` marks an input the script flags `ItemCount`, so that N is whole items [#0743/C/snapshot]:

| Recipe | Consumed | Produced | Δ kcal | Δ hunger |
|---|---|---|---:|---:|
| `open_mac_and_cheese` | 1 × Macandcheese | 1 × Macaroni + 1 × cheese_powdered | 2800 | −74 |
| `CutTurkey` | 1 × TurkeyWhole [IC] | 2 × TurkeyLegs + 2 × TurkeyWings + 2 × TurkeyFillet | −501 | −20 |
| `GrindCornflour` | 20 × CornSeed [IC] | 1 × Cornflour2 | −496 | 20 |
| `GrindCornmeal` | 20 × CornSeed [IC] | 1 × Cornmeal2 | −496 | 60 |
| `MillCornflour` | 20 × CornSeed [IC] | 1 × Cornflour2 | −496 | 20 |
| `MillCornmeal` | 20 × CornSeed [IC] | 1 × Cornmeal2 | −496 | 60 |
| `MakeMeatPatty` | 40 × MincedMeat (= one whole tub) | 1 × MeatPatty | **+312** | 0 |
| `CutChicken` | 1 × ChickenWhole [IC] | 2 × Chicken + 2 × ChickenWings + 2 × ChickenFillet | −195 | −4 |
| `MakeHotDog` | 1 × BunsHotdog_single [IC] + 1 × Hotdog_single [IC] | 1 × Hotdog | −142 | 0 |
| `MakeTortillaChips` | 1 × Tortilla (= 1/5 of one) | 1 × TortillaChipsBaked | +112 | −14 |
| `ScoopIceCream` | 1 × Cone [IC] + 10 × Icecream (= 1/3 of a tub) | 1 × ConeIcecream | **−105** | 0 |
| `MillSunflowerSeeds` | 6 × SunflowerSeeds [IC] | 1 × SeedPaste | −10 | 0 |
| `OpenHotdogPack` | 1 × HotdogPack | 4 × Hotdog_single | −10 | −40 |
| `MakeSquidCalamari` | 1 × Squid [IC] | 2 × SquidCalamari | +5 | 10 |
| `SmashPumpkin` | 1 × Pumpkin [IC] | 5 × PumpkinSmashed | −4 | 0 |
| `GetBaconBits` | 1 × BaconRashers [IC] | 4 × BaconBits | 0 | 0 |
| `GetBaconRashers` | 1 × Bacon [IC] | 4 × BaconRashers | 0 | −4 |
| `HalveFillet` † | 1 × FishFillet [IC] | 2 × FishFillet | 0 | 0 |
| `HarvestRoe` † | 1 × FishRoeSac [IC] | 1 × FishRoe | 0 | 0 |
| `MakeHalloweenPumpkin` † | 1 × Pumpkin [IC] | 1 × HalloweenPumpkin | 0 | 0 |
| `MakeToast` | 1 × BreadSlices [IC] | 1 × Toast | 0 | +2 |
| `OpenCandyPackage` | 1 × CandyPackage | 5 × Lollipop + 5 × MintCandy | 0 | −35 |
| `PackCigarettes` ‡ | 20 × CigaretteSingle | 1 × CigarettePack | 0 | 0 |
| `SliceBaloney` † | 1 × Baloney [IC] | 6 × BaloneySlice | 0 | 0 |
| `SliceHam` † | 1 × Ham [IC] | 6 × HamSlice | 0 | 0 |
| `SlicePumpkin` † | 1 × Pumpkin [IC] | 10 × PumpkinSliced | 0 | 0 |
| `SliceSalami` † | 1 × Salami [IC] | 4 × SalamiSlice | 0 | 0 |
| `SliceWatermelon` † | 1 × Watermelon [IC] | 10 × WatermelonSliced | 0 | 0 |
| `SmashWatermelon` | 1 × Watermelon [IC] | 5 × WatermelonSmashed | 0 | 0 |
| `TakeACigarette` ‡ | 1 × CigarettePack | 1 × CigaretteSingle | 0 | 0 |
| `UnpackCigarettes` ‡ | 1 × CigarettePack | 20 × CigaretteSingle | 0 | 0 |

`open_mac_and_cheese` creates 2 800 kcal out of nothing: 1 Macandcheese becomes 1 Macaroni plus 1 cheese_powdered at a hunger delta of −74 [#0744/C/arith.].

`MakeMeatPatty` creates 312 kcal out of nothing: 40 uses of `Base.MincedMeat`, one whole tub, become 1 MeatPatty at a hunger delta of 0, the input weight resting on the measured per-use rule [#0745/M/arith.].

The four corn mills — `GrindCornflour`, `GrindCornmeal`, `MillCornflour` and `MillCornmeal` — each destroy 496 kcal because neither `Base.Cornflour2` nor `Base.Cornmeal2` declares a macro key at all, so every one of those calories is an `absentMacros` substitution [#0746/C/arith.].

`ScoopIceCream` destroys 105 kcal: 1 Cone as a whole item plus 10 uses of `Base.Icecream`, a third of a tub, become 1 ConeIcecream at a hunger delta of 0, again on the measured per-use rule [#0747/M/arith.].

The 8 `InheritFood` splits among the 31, marked † above, read 0 by construction rather than by conservation, and each has exactly one consumed input [#0748/C/snapshot].

The 3 rows counted as calories-absent-on-every-side, marked ‡, are cigarette recipes: neither cigarette row writes a `Calories` line, so their 0 is the `absentMacros` substitution, and `TakeACigarette` and `UnpackCigarettes` additionally charge a drainable input at 0 macros [#0749/C/snapshot].

15 of the 31 resolvable rows are non-zero in calories, and everything else reading 0 is conservation — 1 Watermelon at 1 355 kcal equals 10 WatermelonSliced at 135.5 [#0750/C/snapshot].

Ten of the 31 depend on the uses-not-items rule for their delta — seven of them exact `InheritFood` splits that read 0 under it; the eighth split reads 0 either way and is among the 21 that do not [#0773/C/snapshot].

None of the three `ReplaceOnCooked` links moves a macro: `Base.BaguetteDough` to `Base.Baguette` at a hunger delta of −8.0, `Base.BreadSlices` to `Base.Toast` at +2.0 and `Base.PancakesCraft` to `Base.Pancakes` at +4.0, each firing on the cook transition and only if the item is not rotten [#0752/C/arith.].

Baking a baguette does move −15.0 of thirst, because `Base.BaguetteDough` writes `ThirstChange = 15` and `Base.Baguette` writes no thirst line at all — an absent-against-written substitution named in that row's `absentMacros`, while the other two cooked links' thirst 0 is a both-sides-absent zero [#0753/C/arith.].

The cook transition, and with it every `ReplaceOnCooked` swap, is driven by server-owned state: `Food.update` gates the age update on the server and both item-stats sends in the cooking block are server-gated [#0758].

The `ReplaceOnRotten` melts and the `ReplaceOnUse` and `ReplaceOnDeplete` links are [facts/spoilage.md](spoilage.md#sealed)'s, and their counts and deltas are not repeated here.

<a id="dataset-fidelity"></a>
### The datasets against the running game

Both datasets are built by reading the shipped scripts, so the measured layer is a cross-check against what the game itself loaded, not a source of new numbers.

The game's own `ScriptManager` answered 969 craft recipes, 63 evolved recipes and 0 legacy recipes, each equal to the scan, on one boot of the default fixture with no world change [#0679/M/n=1].

Ten craft recipes were compared field for field: 77 raw rows of which 10 are the live-against-live output-list check, leaving 67 dataset fields with 65 matched at run time and 67 of 67 once replayed against the fixed scanner [#0680/M/n=10].

The two run-time misses are one field: the scanner now reads `inputCount` as the loader does — 9 for `MakePizza` and 2 for `MakeMilkFromPowderBucket` — so the same comparison replayed offline against the committed artifact is 10 of 10 recipes and 77 of 77 raw rows [#0762/C/arith.].

`getPossibleItems()` returned 189, 189, 56, 193 and 42 items for `Salad`, `SaladClay`, `ConeIcecream`, `Soup` and `AddBaitToChum` on that same boot [#0726/M/n=5].

Each of those five live ingredient lists is set-equal to the dataset's ingredient list for that recipe, with 0 extra and 0 missing in both directions, an offline computation against the committed artifact rather than a verdict the run itself carried [#0727/C/arith.].

## Walls and bounds
<a id="walls"></a>

Both cooking transitions were reproduced with no appliance at all, on one steak in a player's inventory primed server-side with heat 2.0, a reset cook minute and a `cookingTime` one minute past the threshold, in one live session at container temperature 1.0 throughout [#0276/M/one-fixture].

An item's `heat` cannot be held at a requested value: `Food.update` runs the temperature update and the aging call before the cooking block and the game's own tick does the same between commands, so a requested 2.0 read back as 1.84703 and fell to 1.78979 inside one explicit update, and a longer cooking experiment needs a real appliance [#0278/M/n=1].

The measured evolved-recipe arithmetic is a client-side reading: the summation's item replacement is server-gated, so the server still held the base and the untouched ingredients, and what a multiplayer server stores after a real add-item action was not measured, the summation itself being pure Java arithmetic that both sides run identically [#0360/M/one-side].

The item removal on depletion is a jar reading only: `ItemUser` is not exposed to Kahlua, so the probe ran the exact setter the spend line executes and nothing after it, and reaching the removal needs a real `ISHandcraftAction` craft rather than an item command [#0714/C/C-only].

The rotten branch — 0.05 times base hunger at Cooking 7 to 8, 0.10 times at Cooking 9 to 10 and refused below Cooking 7 — is the one arm of `addItem` the dataset leaves out: it publishes the fresh-ingredient contribution only, because the gate needs the instance's rotten flag, which is not script data [#0732].

That a recipe whose IO is a drink completes server-side is an inference read from the code, not a reading of the path: the citation behind it is about drinking, and nothing has read the craft completion path for a fluid IO line, whose nutrition is excluded from these deltas anyway [#0760/C/inference].

The mirror says every ingredient adds minus five boredom and unhappiness the first time and that three of the same negates the bonus; the code zeroes an evolved dish's boredom once in phase A and never touches it again, moves only its unhappiness as the unmodified value less five less five per duplicate clamped at plus 25 with an over-stuffing term, and stops the bonus on the second identical copy with the penalty starting on the third [#0365/C/C-only].

The mirror gives a roster of about 35 rows with no template mechanism; 42.20.4 loads 62 evolved-recipe blocks and an item's recipe key attaches both to the matching recipe and to every recipe whose template equals that key [#0366/C/C-only].

The mirror says an evolved recipe inherits the age of its base ingredient only; the age is proportional instead, phase A setting the new age to the new `offAgeMax` times the old age over the old `offAgeMax` and only when both items have real thresholds, with ingredients contributing no age at all [#0367/C/C-only].

A mod cannot change vanilla's cooking gates, timers or evolved-recipe perk scaling, all of which are Java [#1155/M/n=1].

A mod can set per-item cook times through the script keys instead [#1156/M/n=1].

A mod can rewrite a crafted instance from `OnCooked`, whose registration and firing are read rather than driven end to end [#1154/M/n=1].

A mod can control spice behaviour through the `Spice` script bool, whose effect beyond the herbal-tea sums is unread [#1157/C/C-only].

A cooked food's `thirstChange` cannot be trusted client-side; the per-hop arithmetic is [facts/wire-packets.md](wire-packets.md#cooked-thirst)'s [#1147/M/n=1].

Not covered: the cooking UI and the right-click path that reaches it, the crafting timed action end to end, cooking XP beyond the single grant in `Food.update`, `component CraftRecipe` blocks that build entities rather than items, and fluid nutrition, which is per litre and excluded from every delta on this page.

## Open
<a id="open"></a>

- No reader for `AddIngredientIfCooked`, which 37 recipe blocks use, was traced beyond the ingredient-usability check — settled by dumping the readers of that key from the jar [#0380/C/C-only/open].
- Reaching `ItemUser.UseItem`'s removal branch needs a real `ISHandcraftAction` craft rather than an item command, so everything the dataset says about a `mode:destroy` line annihilating the rest of an item is still open to measurement — settled by a live craft on the named harness command; -> X31 [#0778/C/C-only/open].
- The 33 drying recipes write a `variable` range on both sides while a separate jar reading puts `isVariableAmount` as never firing in vanilla and pins the variable input ratio at 1.0; both cannot be right, though nothing in the dataset depends on the answer, every one of the 33 being refused with a variable-amount reason — settled by one live craft probe reading the input count and the input's amount and maximum amount [#0779/C/snapshot/open].
- The rotten branch of the evolved summation is not computed per row, and a mod that cares about cooking with rotten stock needs it plus the instance's rotten flag, which is not script data — settled by computing the arm per row and reading the flag off the instance [#0780/C/open].
- A second partial-use row would widen the measured base of the per-use rule, which rests on `Base.Icecream` alone — settled by `Base.Salt` at 1 of 10 uses, a two-minute probe on the existing command [#0782/C/n=1/open].
- What the `OnCreate` hooks of the 37 output-less recipes do to nutrition, if anything, is unread: the dataset records the hook name and refuses the delta — settled by executing one of them on the game's own craft path; -> X31 [#0784/C/snapshot/open].
- The five parse-time `EvolvedRecipe` aliases were never live-checked — settled by one probe, on which the aliased reading has `RicePot` resolve to nothing as a recipe name while the four `Rice`-templated recipes must list the items whose keys are written `RicePot` or `RicePan` [#0785/C/C-only/open].
- Decision: whether a rebalanced model keeps the calories the evolved summation creates, given that 68 kcal of ingredients produce 79.667 kcal of outputs at Cooking 10 [#0304/M/n=1, #0295/M/n=1].
- Decision: whether the mod flattens the perk curve, given that macros per unit of dish hunger are 1.168 at Cooking 9 against 1.16667 at Cooking 10, so a rebalance that assumes monotonic perk scaling is wrong [#0294/C/arith., #1211/M/n=1].
- Decision: whether the mod corrects the three vanilla script inconsistencies among the 31 resolvable rows, given `open_mac_and_cheese` at 2 800 kcal created, `MakeMeatPatty` at 312 created and the four corn mills at 496 destroyed apiece [#0744/C/arith., #0745/M/arith., #0746/C/arith.].
- Decision: whether the mod declares macro keys on the targets that carry none, given that the corn mills' 496 kcal loss is an absent-macro substitution rather than a measured zero [#0746/C/arith.].

## See also

- [platform/loader-and-scripts.md](../platform/loader-and-scripts.md#craft-recipe-grammar) — the `craftRecipe` block and its IO line grammar, general to any mod.
- [facts/food-item-model.md](food-item-model.md#script-keys) — the script keys the cook block and the recipe loader read, and the state axes they write.
- [facts/spoilage.md](spoilage.md#sealed) — the `ReplaceOnRotten`, `ReplaceOnUse` and `ReplaceOnDeplete` links, home canning's age rewrite, and what rot does to an item.
- [facts/eating-pipeline.md](eating-pipeline.md#modifiers) — the cooked, burnt and stale ladders that read `cooked` and `burnt` at eat time.
- [facts/wire-packets.md](wire-packets.md#item-stats-packet) — which cooking fields cross the wire, which are absent, and the cooked-thirst halving.
- [platform/mp-model.md](../platform/mp-model.md#ownership) — which side owns the item instance, the Cooking perk and the item-stats sends.
- [facts/other-mods/autocook.md](other-mods/autocook.md#architecture) and [facts/other-mods/longtermpreservation.md](other-mods/longtermpreservation.md#mp) — two mods that drive this pipeline from Lua.
- [reference/datasets.md](../reference/datasets.md) — the column authority for `data/recipes.*` and `data/evolved-recipes.*`.
