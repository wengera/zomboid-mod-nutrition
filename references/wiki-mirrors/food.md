# Wiki mirror — Food

**Source:** https://pzwiki.net/wiki/Food
**Fetched:** 2026-09-09
**Wiki page version:** 42.20.0
**License:** CC BY-NC-SA 3.0 — attribution: PZwiki contributors

## Digest

- Overview of edible items — perishable vs non-perishable, the rot and cook state machines — followed by bot-generated tables of every food's encumbrance, hunger, thirst, unhappiness, boredom, food sickness, fresh/rotten days, cook/burn minutes, spice flag and item ID. Stamped 42.20.0.
- Preservation numbers we use: refrigeration multiplies spoil time by 5, full freezing stops decay entirely, freshness is not carried over when the food is crafted into another dish, and cooking level 7 unlocks rotten ingredients in evolved recipes.
- State machine it asserts: fresh -> stale -> rotten degrades effects (less hunger relief, more boredom/unhappiness) and rotten carries a sickness roll; uncooked -> cooked improves effects and usually extends shelf life; overcooked -> burnt "loses most of its positive effects".
- The rotten claim to distrust: "effects will become more negative" reads as blanket, but 01-notes.md Q2 shows the four nutrients are untouched by rot — rotten food gives full calories and full macros. Only hunger (/2.2), stress, endurance, boredom/unhappiness (+20) and the sickness roll (chance scales with days past `offAgeMax`) degrade. Verify against `zombie.inventory.types.Food`.
- Burnt is the mirror image: the page's vague "loses most of its positive effects" is the only hint at the one real nutrition modifier in the game, `Eat`'s /5 divisor on all four nutrients for `isBurnt()` items (`IsoGameCharacter.Eat`), which the page never states.
- Repeats the Nutrition page's line that the macros "only have an impact on the player's weight" — true on this jar per 01-notes.md — but gives no thresholds; go to the Nutrition mirror for those.

## Wikitext

```wikitext
{{LangSwitch}}
{{Navbar items}}
{{Page version|42.20.0}}
{{toc|right}}
{{About|items that can be eaten|drinks|Fluid|nutritional values for all foods|Nutritional values}}
'''Food''' refers to any item that can be consumed by the [[player]] to regain [[hunger]] and occasionally [[thirst]]. Some foods can boost or reduce certain player [[moodles]], such as [[unhappiness]], [[Bored|boredom]], and [[Tired|fatigue]]. The player is required to eat and drink to regain [[health]] and prevent starving to [[death]].

Most readily available foods are from prior to the [[Knox Event]], being either [[#Perishable|perishable]] or [[#Non-perishable|non-perishable]]. Many foods can even be grown and harvested through [[foraging]], [[agriculture]], [[trapping]], and [[fishing]].

== Types of food ==
Many foods become rotten after a period of time, while others can remain unrefrigerated indefinitely. Many foods can be combined or [[Cooking|cooked]] to boost their properties and, in many cases to remove/reduce any negative effects attached to them.

=== Perishable ===
Perishable foods have an expiration date and will rot over time. These food types begin as ''fresh'' (nothing added to the name), before becoming ''(stale)'' and then ''(rotten)''. As food begins to rot, its effects will become more negative, by reducing its hunger, increasing boredom or unhappiness. Consuming rotten food has a high chance of making the player [[sick]], which can be reduced by consuming [[Lemon Grass|lemon grass]] or having the [[Traits#Iron Gut|iron gut trait]].

This process of rotting can be slowed by [[Refrigerator|refrigerating]] the food, as indicated by a blue overlay that increases spoil time by 5 times, or freezing it will completely stop decay when the food is fully frozen (the food name must say "frozen"). Example: Fish fillet takes 2 days to go stale, refrigerating it will take it 10 days, and as soon as it is fully frozen, it will last forever (as long as it will not thaw in between).

If the player has a level 7 [[cooking]] skill, parts of the rotten perishables can be safely added to a dish as an ingredient in a [[Evolved recipes|cooking recipe]].

Rotten food can also be used in the [[composter]] to create [[Compost Bag|compost bags]].

Freshness value is not carried over when using the food to [[Crafting|craft]] some other dish.

=== Non-perishable ===
Non-perishable foods have no expiration date and will therefore never become rotten. Examples of these include [[chocolate]], [[pop]], [[Beef Jerky|beef jerky]] and [[butter]]. Their effects will remain unchanged over time, and many can even be used as an ingredient in recipes, making them very useful to stockpile.

Canned foods will remain non-perishable until they are opened, with many requiring a [[Can Opener|can opener]]. Canned foods can be eaten uncooked, but some gain bonuses from being heated up, such as [[Bowl of Beans|beans]]. Many [[Evolved recipes|cooking recipes]] also benefit from the addition of canned food.

== Cooking ==
{{Main|Cooking}}
Many raw foods can be cooked in an [[Heat source|oven]] to produce a more fulfilling meal. After a short period, the item will begin to glow red, starting the cooking process. Once the item has turned from 'uncooked' to 'cooked', its effects will become more positive and will often increase the time before it becomes rotten (depending on the food). If left in an active oven for too long, the food will eventually become 'burnt', losing most of its positive effects and gaining negative effects, including a chance to make the player sick.

Some food items have a chance to make the player sick if eaten raw. This is displayed when hovered over with the cursor.

== Nutrition ==
{{Main|Nutrition}}
Each item of food has a quality known as [[Nutritional values|''nutritional value'']] which is defined by four variables: [[Nutrition#Carbohydrates|carbohydrates]], [[Nutrition#Proteins|proteins]], [[Nutrition#Lipids|lipids]], and [[Nutrition#Calories|calories]]. Each of these variables currently only have an impact on the player's [[Nutrition#Weight|weight]], which can affect [[fitness]] experience gain, [[endurance]], [[Skills#Agility|movement speed]] and [[Health|fragility]].

== Items ==
{{Legend food}}

=== Evolved recipes ===
{{Main|Evolved recipes}}

==== Base items ====
<!-- Bot_flag|type=food_item_list|id=evolved_recipes --><div class="scroll-x">
{| class="wikitable theme-red sortable sticky-column" style="text-align: center;"
! Icon
! Name
! [[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Hunger_32.png|link=|Hunger]]
! [[File:Status_Hunger_32.png|link=|Hunger]]/[[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Thirst_32.png|link=|Thirst]]
! [[File:Mood_Sad_32.png|link=|Unhappiness]]
! [[File:Mood_Bored_32.png|link=|Boredom]]
! [[File:Mood_Nauseous_32.png|link=|Food Sickness]]
! [[File:UI_Fresh_Time.png|32px|link=|Fresh (days)]]
! [[File:UI_Rotten_Time.png|32px|link=|Rotten (days)]]
! [[File:UI_Cook_Time.png|32px|link=|Cooked (mins)]]
! [[File:UI_Burn_Time.png|32px|link=|Burned (mins)]]
! [[File:Pepper.png|24px|link=|Spice]]
! Item ID
|-
| [[File:BagelPlain.png|32x32px|link=Bagel|Bagel]]
| [[Bagel]]
| 0.1
| -10
| -100
| -
| -
| -
| -
| 1
| 6
| 5
| 10
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BagelPlain
|-
| [[File:FruitSalad.png|32x32px|link=Salad|Base.FruitSaladClay]]
| [[Salad]]
| 0.7
| -60
| -86
| -
| -
| -
| -
| 2
| 3
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.FruitSaladClay
|-
| [[File:Mug_Copper_Coffee.png|32x32px|link=Beverage (mug)|Base.HotDrinkCopper]]
| [[Beverage (mug)|Hot drink - Copper]]
| 0.5
| -
| -
| -20
| -10
| -
| -
| ∞
| ∞
| 10
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.HotDrinkCopper
|-
| [[File:Mug_Gold_Coffee.png|32x32px|link=Beverage (mug)|Base.HotDrinkGold]]
| [[Beverage (mug)|Hot drink - Gold]]
| 0.5
| -
| -
| -20
| -10
| -
| -
| ∞
| ∞
| 10
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.HotDrinkGold
|-
| [[File:Mug_Forged_Coffee.png|32x32px|link=Beverage (mug)|Base.HotDrinkMetal]]
| [[Beverage (mug)|Hot drink - Metal]]
| 0.5
| -
| -
| -20
| -10
| -
| -
| ∞
| ∞
| 10
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.HotDrinkMetal
|-
| [[File:Mug_Metal_Coffee.png|32x32px|link=Beverage (mug)|Base.HotDrinkSilver]]
| [[Beverage (mug)|Hot drink - Silver]]
| 0.5
| -
| -
| -20
| -10
| -
| -
| ∞
| ∞
| 10
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.HotDrinkSilver
|-
| [[File:GlassTumbler_Coffee.png|32x32px|link=Beverage (tumbler)|Base.HotDrinkTumbler]]
| [[Beverage (tumbler)|Hot drink - Tumbler]]
| 0.5
| -
| -
| -20
| -10
| -
| -
| ∞
| ∞
| 10
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.HotDrinkTumbler
|-
| [[File:Oatmeal.png|32x32px|link=Bowl of Oatmeal|Bowl of Oatmeal]]
| [[Bowl of Oatmeal]]
| 0.8
| -10
| -12
| -
| -
| -
| -
| 1
| 2
| 5
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Oatmeal
|-
| <span class="cycle-img">[[File:Dough.png|32x32px|link=Bread (dough)|Bread]][[File:DoughRotten.png|32x32px|link=Bread (dough)|Bread]][[File:DoughCooked.png|32x32px|link=Bread (dough)|Bread]][[File:DoughBurnt.png|32x32px|link=Bread (dough)|Bread]]</span>
| [[Bread (dough)|Bread]]
| 0.3
| -24
| -80
| 15
| 10
| -
| -
| 3
| 6
| 20
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BreadDough
|-
| [[File:MetalBucket_Soup.png|32x32px|link=Bucket of Soup|Bucket of Soup]]
| [[Bucket of Soup]]
| 3
| -40
| -13
| -40
| -20
| -
| -
| 3
| 5
| 50
| 100
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BucketOfSoup
|-
| [[File:MetalBucket_Soup.png|32x32px|link=Bucket of Stew|Bucket of Stew]]
| [[Bucket of Stew]]
| 3
| -40
| -13
| -40
| -20
| -
| -
| 3
| 5
| 50
| 100
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BucketOfStew
|-
| [[File:Burger.png|32x32px|link=Burger|Burger]]
| [[Burger]]
| 0.3
| -25
| -83
| -
| -10
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Burger
|-
| [[File:Burger.png|32x32px|link=Burger|Burger]]
| [[Burger]]
| 0.3
| -20
| -67
| -
| -10
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BurgerRecipe
|-
| [[File:Burrito.png|32x32px|link=Burrito|Burrito]]
| [[Burrito]]
| 0.3
| -25
| -83
| -
| -10
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Burrito
|-
| [[File:Burrito.png|32x32px|link=Burrito|Burrito]]
| [[Burrito]]
| 0.1
| -5
| -50
| -
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BurritoRecipe
|-
| <span class="cycle-img">[[File:Cake.png|32x32px|link=Cake (crafted)|Cake]][[File:CakeCooked.png|32x32px|link=Cake (crafted)|Cake]][[File:CakeOverdone.png|32x32px|link=Cake (crafted)|Cake]]</span>
| [[Cake (crafted)|Cake]]
| 0.5
| -15
| -30
| -
| -10
| -
| -
| 4
| 9
| 40
| 110
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CakeRaw
|-
| [[File:chumball.png|32x32px|link=Chum|Chum]]
| [[Chum]]
| 0.5
| -
| -
| -
| 20
| -
| ?
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Chum
|-
| [[File:HotdogCrafted.png|32x32px|link=Hot Dog|Hot Dog]]
| [[Hot Dog]]
| 0.3
| -20
| -67
| -
| -
| -
| -
| 3
| 6
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Hotdog
|-
| [[File:Teacup.png|32x32px|link=Cup of Tea|Hot Drink]]
| [[Cup of Tea|Hot Drink]]
| 0.5
| -
| -
| -20
| -10
| -
| -
| ∞
| ∞
| 10
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.HotDrinkTea
|-
| [[File:Ceramic_Teacup_Fired.png|32x32px|link=Hot Teacup (ceramic)|Hot Drink]]
| [[Hot Teacup (ceramic)|Hot Drink]]
| 0.5
| -
| -
| -20
| -10
| -
| -
| ∞
| ∞
| 10
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.HotDrinkTeaCeramic
|-
| <span class="cycle-img">[[File:MugFulll.png|32x32px|link=Beverage (mug)|Hot Drink]][[File:MugRedFull.png|32x32px|link=Beverage (mug)|Hot Drink]][[File:MugWhite_Full.png|32x32px|link=Beverage (mug)|Hot Drink]][[File:MugBlue_Full.png|32x32px|link=Beverage (mug)|Hot Drink]][[File:MugYellow_Full.png|32x32px|link=Beverage (mug)|Hot Drink]]</span>
| [[Beverage (mug)|Hot Drink]]
| 0.5
| -
| -
| -20
| -10
| -
| -
| ∞
| ∞
| 10
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.HotDrink
|-
| [[File:Ceramic_Mug_Unfired.png|32x32px|link=Beverage (mug)|Hot Drink]]
| [[Beverage (mug)|Hot Drink]]
| 0.5
| -
| -
| -20
| -10
| -
| -
| ∞
| ∞
| 10
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.HotDrinkClay
|-
| [[File:MugSpiffoFull.png|32x32px|link=Beverage (mug)|Hot Drink]]
| [[Beverage (mug)|Hot Drink]]
| 0.5
| -
| -
| -20
| -10
| -
| -
| ∞
| ∞
| 10
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.HotDrinkSpiffo
|-
| [[File:MugWhite_Full.png|32x32px|link=Beverage (mug)|Hot Drink]]
| [[Beverage (mug)|Hot Drink]]
| 0.5
| -
| -
| -20
| -10
| -
| -
| ∞
| ∞
| 10
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.HotDrinkWhite
|-
| [[File:ConeIceCreamTopped.png|32x32px|link=Ice Cream Cone|Ice Cream Cone]]
| [[Ice Cream Cone]]
| 0.2
| -15
| -75
| -
| -10
| -
| -
| 1
| 2
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.ConeIcecreamToppings
|-
| [[File:PanFull.png|32x32px|link=Omelette|Omelette]]
| [[Omelette]]
| 0.5
| -14
| -28
| -
| -
| -
| ?
| 3
| 6
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.OmeletteRecipe
|-
| <span class="cycle-img">[[File:FryingPan_Forged_Eggs.png|32x32px|link=Omelette|Omelette]][[File:FryingPan_Forged_EggsRotten.png|32x32px|link=Omelette|Omelette]][[File:FryingPan_Forged_EggsCooked.png|32x32px|link=Omelette|Omelette]][[File:FryingPan_Forged_EggsBurnt.png|32x32px|link=Omelette|Omelette]]</span>
| [[Omelette]]
| 0.5
| -14
| -28
| -
| -
| -
| ?
| 3
| 6
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.OmeletteRecipeForged
|-
| [[File:PancakesFruit.png|32x32px|link=Pancakes|Pancakes]]
| [[Pancakes]]
| 0.3
| -20
| -67
| -
| -10
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PancakesRecipe
|-
| [[File:SaucepanFilled.png|32x32px|link=Pasta (crafted pan)|Pasta]]
| [[Pasta (crafted pan)|Pasta]]
| 3
| -10
| -3
| -
| 20
| -
| -
| 4
| 7
| 20
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PastaPan
|-
| [[File:CopperPot_Pasta.png|32x32px|link=Pasta|Pasta]]
| [[Pasta]]
| 3
| -10
| -3
| -
| 20
| -
| -
| 4
| 7
| 20
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PastaPanCopper
|-
| [[File:PotFull.png|32x32px|link=Pasta (crafted pot)|Pasta]]
| [[Pasta (crafted pot)|Pasta]]
| 3
| -10
| -3
| -
| 20
| -
| -
| 3
| 6
| 20
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PastaPot
|-
| <span class="cycle-img">[[File:Pot_Forged_Pasta.png|32x32px|link=Pasta|Pasta]][[File:Pot_Forged_PastaRotten.png|32x32px|link=Pasta|Pasta]]</span>
| [[Pasta]]
| 3
| -10
| -3
| -
| 20
| -
| -
| 3
| 6
| 20
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PastaPotForged
|-
| <span class="cycle-img">[[File:PieWhole.png|32x32px|link=Pie (savory)|Pie]][[File:PieWholeCooked.png|32x32px|link=Pie (savory)|Pie]][[File:PieWholeOverdone.png|32x32px|link=Pie (savory)|Pie]]</span>
| [[Pie (savory)|Pie]]
| 0.5
| -15
| -30
| -
| 10
| -
| -
| 4
| 9
| 40
| 110
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PieWholeRaw
|-
| <span class="cycle-img">[[File:PieWhole.png|32x32px|link=Pie (sweet)|Pie]][[File:PieWholeCooked.png|32x32px|link=Pie (sweet)|Pie]][[File:PieWholeOverdone.png|32x32px|link=Pie (sweet)|Pie]]</span>
| [[Pie (sweet)|Pie]]
| 0.5
| -15
| -30
| -
| 10
| -
| -
| 4
| 9
| 40
| 110
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PieWholeRawSweet
|-
| [[File:PizzaWhole.png|32x32px|link=Pizza|Pizza]]
| [[Pizza]]
| 1.5
| -80
| -53
| -
| 10
| -
| -
| 3
| 5
| 20
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PizzaRecipe
|-
| [[File:PizzaWhole.png|32x32px|link=Pizza|Pizza]]
| [[Pizza]]
| 1.8
| -150
| -83
| -
| -10
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PizzaWhole
|-
| [[File:Muffintray_Batter.png|32x32px|link=Plain Muffins|Plain Muffins]]
| [[Plain Muffins]]
| 1.5
| -30
| -20
| -
| -
| -
| -
| 3
| 10
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BakingTray_Muffin_Recipe
|-
| [[File:BagelPoppy.png|32x32px|link=Poppy Bagel|Poppy Bagel]]
| [[Poppy Bagel]]
| 0.1
| -10
| -100
| -
| -
| -
| -
| 1
| 6
| 5
| 10
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BagelPoppy
|-
| [[File:PotFull.png|32x32px|link=Soup|Pot of Soup]]
| [[Soup|Pot of Soup]]
| 3
| -30
| -10
| -30
| -20
| -
| -
| 3
| 5
| 50
| 100
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PotOfSoup
|-
| [[File:PotFull.png|32x32px|link=Soup|Pot of Soup]]
| [[Soup|Pot of Soup]]
| 3
| -40
| -13
| -40
| -20
| -
| -
| 3
| 5
| 50
| 100
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PotOfSoupRecipe
|-
| <span class="cycle-img">[[File:Pot_Forged_Soup.png|32x32px|link=Soup|Pot of Soup]][[File:Pot_Forged_SoupRotten.png|32x32px|link=Soup|Pot of Soup]]</span>
| [[Soup|Pot of Soup]]
| 3
| -40
| -13
| -40
| -20
| -
| -
| 3
| 5
| 50
| 100
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PotForgedSoupRecipe
|-
| [[File:PotFull.png|32x32px|link=Stew|Pot of Stew]]
| [[Stew|Pot of Stew]]
| 3
| -40
| -13
| -40
| -20
| -
| -
| 3
| 5
| 70
| 140
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PotOfStew
|-
| <span class="cycle-img">[[File:Pot_Forged_Stew.png|32x32px|link=Stew|Pot of Stew]][[File:Pot_Forged_StewRotten.png|32x32px|link=Stew|Pot of Stew]]</span>
| [[Stew|Pot of Stew]]
| 3
| -40
| -13
| -40
| -20
| -
| -
| 3
| 5
| 70
| 140
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PotForgedStew
|-
| [[File:SaucepanFilled.png|32x32px|link=Rice (crafted pan)|Rice]]
| [[Rice (crafted pan)|Rice]]
| 3
| -10
| -3
| -
| 20
| -
| -
| 4
| 7
| 20
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.RicePan
|-
| [[File:CopperPot_Pasta.png|32x32px|link=Rice (crafted pan)|Rice]]
| [[Rice (crafted pan)|Rice]]
| 3
| -10
| -3
| -
| 20
| -
| -
| 4
| 7
| 20
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.RicePanCopper
|-
| [[File:PotFull.png|32x32px|link=Rice (crafted pot)|Rice]]
| [[Rice (crafted pot)|Rice]]
| 3
| -10
| -3
| -
| 20
| -
| -
| 3
| 6
| 20
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.RicePot
|-
| <span class="cycle-img">[[File:Pot_Forged_Rice.png|32x32px|link=Rice (crafted pot)|Rice]][[File:Pot_Forged_RiceRotten.png|32x32px|link=Rice (crafted pot)|Rice]]</span>
| [[Rice (crafted pot)|Rice]]
| 3
| -10
| -3
| -
| 20
| -
| -
| 3
| 6
| 20
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.RicePotForged
|-
| [[File:RoastingpanFull.png|32x32px|link=Roasted Vegetables|Roast]]
| [[Roasted Vegetables|Roast]]
| 1.3
| -10
| -8
| -
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PanFriedVegetables2
|-
| [[File:FruitSalad.png|32x32px|link=Fruit Salad|Salad]]
| [[Fruit Salad|Salad]]
| 0.7
| -60
| -86
| -
| -
| -
| -
| 2
| 3
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.FruitSalad
|-
| <span class="cycle-img">[[File:TZ_CraftSalat.png|32x32px|link=Salad|Salad]][[File:TZ_CraftSalatRotten.png|32x32px|link=Salad|Salad]]</span>
| [[Salad]]
| 0.5
| -60
| -120
| -
| -
| -5
| -
| 2
| 3
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Salad
|-
| <span class="cycle-img">[[File:TZ_CraftSalat.png|32x32px|link=Salad|Salad]][[File:TZ_CraftSalatRotten.png|32x32px|link=Salad|Salad]]</span>
| [[Salad]]
| 0.5
| -60
| -120
| -
| -
| -5
| -
| 2
| 3
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SaladClay
|-
| [[File:BaguetteSandwich.png|32x32px|link=Sandwich (baguette)|Sandwich]]
| [[Sandwich (baguette)|Sandwich]]
| 0.2
| -10
| -50
| -
| -
| -
| -
| 3
| 6
| 5
| 20
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BaguetteSandwich
|-
| [[File:Sandwich.png|32x32px|link=Sandwich (bread)|Sandwich]]
| [[Sandwich (bread)|Sandwich]]
| 0.2
| -10
| -50
| -
| -
| -
| -
| 3
| 6
| 5
| 20
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Sandwich
|-
| [[File:BagelSesame.png|32x32px|link=Sesame Bagel|Sesame Bagel]]
| [[Sesame Bagel]]
| 0.1
| -10
| -100
| -
| -
| -
| -
| 1
| 6
| 5
| 10
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BagelSesame
|-
| <span class="cycle-img">[[File:FryingPan_Forged_Stirfry.png|32x32px|link=Stir Fry (pan)|Stir Fry]][[File:FryingPan_Forged_StirfryRotten.png|32x32px|link=Stir Fry (pan)|Stir Fry]][[File:FryingPan_Forged_StirfryBurnt.png|32x32px|link=Stir Fry (pan)|Stir Fry]]</span>
| [[Stir Fry (pan)|Stir Fry]]
| 1
| -10
| -10
| -
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PanFriedVegetablesForged
|-
| [[File:PanFull.png|32x32px|link=Stir Fry (griddle)|Stir Fry]]
| [[Stir Fry (griddle)|Stir Fry]]
| 1.5
| -10
| -7
| -
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.GriddlePanFriedVegetables
|-
| [[File:PanFull.png|32x32px|link=Stir Fry (pan)|Stir Fry]]
| [[Stir Fry (pan)|Stir Fry]]
| 1.5
| -10
| -7
| -
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PanFriedVegetables
|-
| [[File:Taco.png|32x32px|link=Taco|Taco]]
| [[Taco]]
| 0.3
| -25
| -83
| -
| -10
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Taco
|-
| [[File:Taco.png|32x32px|link=Taco|Taco]]
| [[Taco]]
| 0.1
| -5
| -50
| -
| -
| -
| -
| 15
| 20
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.TacoRecipe
|-
| [[File:Toast.png|32x32px|link=Toast|Toast]]
| [[Toast]]
| 0.1
| -8
| -80
| -
| -
| -
| -
| 3
| 6
| -
| 20
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Toast
|-
| [[File:SafflesFruit.png|32x32px|link=Waffles|Waffles]]
| [[Waffles]]
| 0.3
| -15
| -50
| -
| -10
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.WafflesRecipe
|}
</div><!-- Bot_flag_end|type=food_item_list|id=evolved_recipes -->

=== Prepared food ===
<!-- Bot_flag|type=food_item_list|id=prepared --><div class="scroll-x">
{| class="wikitable theme-red sortable sticky-column" style="text-align: center;"
! Icon
! Name
! [[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Hunger_32.png|link=|Hunger]]
! [[File:Status_Hunger_32.png|link=|Hunger]]/[[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Thirst_32.png|link=|Thirst]]
! [[File:Mood_Sad_32.png|link=|Unhappiness]]
! [[File:UI_Fresh_Time.png|32px|link=|Fresh (days)]]
! [[File:UI_Rotten_Time.png|32px|link=|Rotten (days)]]
! [[File:UI_Cook_Time.png|32px|link=|Cooked (mins)]]
! [[File:UI_Burn_Time.png|32px|link=|Burned (mins)]]
! [[File:Pepper.png|24px|link=|Spice]]
! Item ID
|-
| [[File:Doughnut_Baguette.png|32x32px|link=Baguette|Baguette]]
| [[Baguette]]
| 0.3
| -15
| -50
| 15
| 10
| 3
| 6
| 20
| 120
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BaguetteDough
|-
| [[File:BakingTray_CookiesBaked.png|32x32px|link=Chocolate Chip Cookie|Baking Tray with Chocolate Chip Cookies]]
| [[Chocolate Chip Cookie|Baking Tray with Chocolate Chip Cookies]]
| 1.9
| -23
| -12
| -
| -30
| 7
| 30
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CookieChocolateChipDough
|-
| [[File:BakingTray_CookiesBaked.png|32x32px|link=Chocolate Cookie|Baking Tray with Chocolate Cookies]]
| [[Chocolate Cookie|Baking Tray with Chocolate Cookies]]
| 1.9
| -23
| -12
| -
| -30
| 7
| 30
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CookiesChocolateDough
|-
| [[File:BakingTray_CookiesBaked.png|32x32px|link=Oatmeal Cookie|Baking Tray with Oatmeal Cookies]]
| [[Oatmeal Cookie|Baking Tray with Oatmeal Cookies]]
| 1.9
| -23
| -12
| -
| -
| 7
| 30
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CookiesOatmealDough
|-
| [[File:BakingTray_CookiesBaked.png|32x32px|link=Shortbread Cookie|Baking Tray with Shortbread Cookies]]
| [[Shortbread Cookie|Baking Tray with Shortbread Cookies]]
| 1.9
| -23
| -12
| -
| -30
| 7
| 30
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CookiesShortbreadDough
|-
| [[File:BakingTray_CookiesBaked.png|32x32px|link=Sugar Cookie|Baking Tray with Sugar Cookies]]
| [[Sugar Cookie|Baking Tray with Sugar Cookies]]
| 1.9
| -23
| -12
| -
| -30
| 7
| 30
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CookiesSugarDough
|-
| [[File:Biscuit.png|32x32px|link=Biscuit|Biscuit]]
| [[Biscuit]]
| 0.1
| -5
| -50
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Biscuit
|-
| [[File:Muffintray_Batter.png|32x32px|link=Muffin Tray with Biscuits|Biscuits]]
| [[Muffin Tray with Biscuits|Biscuits]]
| 1.5
| -23
| -15
| -
| -
| 3
| 5
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Muffintray_Biscuit
|-
| [[File:Oatmeal.png|32x32px|link=Bowl of Cereal|Bowl of Cereal]]
| [[Bowl of Cereal]]
| 0.8
| -20
| -25
| -15
| -
| 4
| 7
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CerealBowl
|-
| [[File:FriedRice.png|32x32px|link=Pasta (crafted pot)|Bowl of Pasta]]
| [[Pasta (crafted pot)|Bowl of Pasta]]
| 1
| -12
| -12
| -
| -
| 3
| 6
| 10
| 40
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PastaBowl
|-
| [[File:FriedRice.png|32x32px|link=Pasta (crafted pot)|Bowl of Pasta]]
| [[Pasta (crafted pot)|Bowl of Pasta]]
| 1
| -12
| -12
| -
| -
| 3
| 6
| 10
| 40
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PastaBowlClay
|-
| [[File:FriedRice.png|32x32px|link=Rice (crafted pot)|Bowl of Rice]]
| [[Rice (crafted pot)|Bowl of Rice]]
| 1
| -12
| -12
| -
| -
| 3
| 6
| 10
| 40
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.RiceBowl
|-
| [[File:FriedRice.png|32x32px|link=Rice (crafted pot)|Bowl of Rice]]
| [[Rice (crafted pot)|Bowl of Rice]]
| 1
| -12
| -12
| -
| -
| 3
| 6
| 10
| 40
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.RiceBowlClay
|-
| [[File:BowlFull.png|32x32px|link=Bowl of Soup|Bowl of Soup]]
| [[Bowl of Soup]]
| 1
| -15
| -15
| -15
| -20
| 1
| 3
| 15
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SoupBowl
|-
| [[File:BowlFull.png|32x32px|link=Bowl of Soup|Bowl of Soup]]
| [[Bowl of Soup]]
| 1
| -15
| -15
| -15
| -20
| 1
| 3
| 15
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SoupBowlClay
|-
| [[File:BowlFull.png|32x32px|link=Stew|Bowl of Stew]]
| [[Stew|Bowl of Stew]]
| 1
| -15
| -15
| -
| -20
| 2
| 4
| 15
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.StewBowl
|-
| [[File:BowlFull.png|32x32px|link=Stew|Bowl of Stew]]
| [[Stew|Bowl of Stew]]
| 1
| -15
| -15
| -
| -20
| 2
| 4
| 15
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.StewBowlClay
|-
| [[File:CabbageRoll.png|32x32px|link=Cabbage Roll|Cabbage Roll]]
| [[Cabbage Roll]]
| 0.3
| -20
| -67
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CabbageRoll
|-
| [[File:CakeSlice.png|32x32px|link=Cake Slice|Cake Slice]]
| [[Cake Slice]]
| 0.2
| -7
| -35
| -
| -10
| 3
| 5
| 20
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CakeSlice
|-
| [[File:CheesePowdered.png|32x32px|link=Cheese Powder|Cheese Powder]]
| [[Cheese Powder]]
| 0.1
| -14
| -140
| 14
| 14
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.cheese_powdered
|-
| [[File:Pie.png|32x32px|link=Cherry Pie Slice|Cherry Pie Slice]]
| [[Cherry Pie Slice]]
| 0.5
| -30
| -60
| -
| -10
| 5
| 8
| 20
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Pie
|-
| [[File:CookieChocolateChip.png|32x32px|link=Chocolate Chip Cookie|Chocolate Chip Cookie]]
| [[Chocolate Chip Cookie]]
| 0.1
| -5
| -50
| -
| -10
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CookieChocolateChip
|-
| [[File:CookiesChocolate.png|32x32px|link=Chocolate Cookie|Chocolate Cookie]]
| [[Chocolate Cookie]]
| 0.1
| -5
| -50
| -
| -10
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CookiesChocolate
|-
| [[File:Gravy.png|32x32px|link=Gravy|Gravy]]
| [[Gravy]]
| 0.2
| -8
| -40
| -
| -
| 4
| 7
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Gravy
|-
| [[File:Guacamole.png|32x32px|link=Guacamole|Guacamole]]
| [[Guacamole]]
| 0.1
| -8
| -80
| -
| -
| 4
| 8
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Guacamole
|-
| [[File:Jackolantern.png|32x32px|link=Jack-o'-lantern|Jack-o'-lantern]]
| [[Jack-o'-lantern]]
| 1
| -40
| -40
| -
| 10*
| 14
| 28
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.HalloweenPumpkin
|-
| <span class="cycle-img">[[File:Macaroni.png|32x32px|link=Macaroni|Macaroni]][[File:MacaroniCooked.png|32x32px|link=Macaroni|Macaroni]]</span>
| [[Macaroni]]
| 2
| -60
| -30
| 60
| 40
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Macaroni
|-
| [[File:Maki.png|32x32px|link=Maki|Maki]]
| [[Maki]]
| 0.1
| -10
| -100
| -
| -20
| 2
| 4
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Maki
|-
| [[File:MuffinGeneric.png|32x32px|link=Muffin|Muffin]]
| [[Muffin]]
| 0.1
| -7
| -70
| -
| -10
| 5
| 8
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.MuffinGeneric
|-
| [[File:CookiesOatmeal.png|32x32px|link=Oatmeal Cookie|Oatmeal Cookie]]
| [[Oatmeal Cookie]]
| 0.1
| -5
| -50
| -
| -10
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CookiesOatmeal
|-
| [[File:Onigiri.png|32x32px|link=Onigiri|Onigiri]]
| [[Onigiri]]
| 0.1
| -12
| -120
| -
| -20
| 2
| 4
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Onigiri
|-
| [[File:Pancakes.png|32x32px|link=Pancakes|Pancakes]]
| [[Pancakes]]
| 0.3
| -20
| -67
| -
| 10
| 3
| 5
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PancakesCraft
|-
| [[File:Pizza.png|32x32px|link=Pizza Slice|Pizza Slice]]
| [[Pizza Slice]]
| 0.3
| -25
| -83
| -
| -10
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Pizza
|-
| [[File:CookiesShortbread.png|32x32px|link=Shortbread Cookie|Shortbread Cookie]]
| [[Shortbread Cookie]]
| 0.1
| -5
| -50
| -
| -10
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CookiesShortbread
|-
| [[File:CookiesSugar.png|32x32px|link=Sugar Cookie|Sugar Cookie]]
| [[Sugar Cookie]]
| 0.1
| -5
| -50
| -
| -10
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CookiesSugar
|-
| [[File:TortillaChips.png|32x32px|link=Tortilla Chips|Tortilla Chips]]
| [[Tortilla Chips]]
| 0.2
| -15
| -75
| -
| -
| 3
| 5
| 5
| 10
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.TortillaChipsBaked
|}
</div><!-- Bot_flag_end|type=food_item_list|id=prepared -->

=== Canned food ===
<!-- Bot_flag|type=food_item_list|id=canned --><div class="scroll-x">
{| class="wikitable theme-red sortable sticky-column" style="text-align: center;"
! Icon
! Name
! [[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Hunger_32.png|link=|Hunger]]
! [[File:Status_Hunger_32.png|link=|Hunger]]/[[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Thirst_32.png|link=|Thirst]]
! [[File:Mood_Sad_32.png|link=|Unhappiness]]
! [[File:UI_Fresh_Time.png|32px|link=|Fresh (days)]]
! [[File:UI_Rotten_Time.png|32px|link=|Rotten (days)]]
! [[File:UI_Cook_Time.png|32px|link=|Cooked (mins)]]
! [[File:UI_Burn_Time.png|32px|link=|Burned (mins)]]
! [[File:Pepper.png|24px|link=|Spice]]
! Item ID
|-
| [[File:Beans.png|32x32px|link=Canned Beans|Canned Beans]]
| [[Canned Beans]]
| 0.8
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.TinnedBeans
|-
| [[File:BeansOpen.png|32x32px|link=Canned Beans|Canned Beans (Open)]]
| [[Canned Beans|Canned Beans (Open)]]
| 0.8
| -24
| -30
| -
| 10*
| 2
| 4
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.OpenBeans
|-
| [[File:CannedCarrots.png|32x32px|link=Canned Carrots|Canned Carrots]]
| [[Canned Carrots]]
| 0.8
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedCarrots2
|-
| [[File:CannedCarrotsOpen.png|32x32px|link=Canned Carrots|Canned Carrots (Open)]]
| [[Canned Carrots|Canned Carrots (Open)]]
| 0.8
| -12
| -15
| -4
| -
| 2
| 4
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedCarrotsOpen
|-
| [[File:CannedChili.png|32x32px|link=Canned Chili|Canned Chili]]
| [[Canned Chili]]
| 0.8
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedChili
|-
| [[File:CannedChiliOpen.png|32x32px|link=Canned Chili|Canned Chili (Open)]]
| [[Canned Chili|Canned Chili (Open)]]
| 0.8
| -16
| -20
| -
| -
| 3
| 5
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedChiliOpen
|-
| [[File:CannedCorn.png|32x32px|link=Canned Corn|Canned Corn]]
| [[Canned Corn]]
| 0.8
| -
| -
| -
| -
| ∞
| ∞
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedCorn
|-
| [[File:CannedCornOpen.png|32x32px|link=Canned Corn|Canned Corn (Open)]]
| [[Canned Corn|Canned Corn (Open)]]
| 0.8
| -16
| -20
| -4
| -
| 2
| 4
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedCornOpen
|-
| [[File:CannedCornedBeef.png|32x32px|link=Canned Corned Beef|Canned Corned Beef]]
| [[Canned Corned Beef]]
| 0.8
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedCornedBeef
|-
| [[File:CannedCornedBeefOpen.png|32x32px|link=Canned Corned Beef|Canned Corned Beef (Open)]]
| [[Canned Corned Beef|Canned Corned Beef (Open)]]
| 0.8
| -24
| -30
| -
| -
| 2
| 4
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedCornedBeefOpen
|-
| [[File:Dogfood.png|32x32px|link=Canned Dog Food|Canned Dog Food]]
| [[Canned Dog Food]]
| 0.8
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Dogfood
|-
| [[File:DogfoodOpen.png|32x32px|link=Canned Dog Food|Canned Dog Food (Open)]]
| [[Canned Dog Food|Canned Dog Food (Open)]]
| 0.8
| -30
| -38
| -
| 50
| 5
| 7
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DogfoodOpen
|-
| [[File:CannedCondensedMilk.png|32x32px|link=Canned Evaporated Milk|Canned Evaporated Milk]]
| [[Canned Evaporated Milk]]
| 0.8
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedMilk
|-
| [[File:CannedCondensedMilk_Open.png|32x32px|link=Canned Evaporated Milk|Canned Evaporated Milk (Open)]]
| [[Canned Evaporated Milk|Canned Evaporated Milk (Open)]]
| 0.8
| -10
| -12
| -10
| -
| 4
| 7
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedMilkOpen
|-
| [[File:CannedJuice.png|32x32px|link=Canned Fruit Beverage|Canned Fruit Beverage]]
| [[Canned Fruit Beverage]]
| 0.8
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedFruitBeverage
|-
| [[File:CannedJuice_Open.png|32x32px|link=Canned Fruit Beverage|Canned Fruit Beverage (Open)]]
| [[Canned Fruit Beverage|Canned Fruit Beverage (Open)]]
| 0.8
| -15
| -19
| -85
| -10
| 5
| 7
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedFruitBeverageOpen
|-
| [[File:CannedFruitCocktail.png|32x32px|link=Canned Fruit Cocktail|Canned Fruit Cocktail]]
| [[Canned Fruit Cocktail]]
| 0.8
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedFruitCocktail
|-
| [[File:CannedFruitCocktailOpen.png|32x32px|link=Canned Fruit Cocktail|Canned Fruit Cocktail (Open)]]
| [[Canned Fruit Cocktail|Canned Fruit Cocktail (Open)]]
| 0.8
| -15
| -19
| -
| -10
| 5
| 7
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedFruitCocktailOpen
|-
| [[File:CannedMushroomSoup.png|32x32px|link=Canned Mushroom Soup|Canned Mushroom Soup]]
| [[Canned Mushroom Soup]]
| 0.8
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedMushroomSoup
|-
| [[File:CannedMushroomSoupOpen.png|32x32px|link=Canned Mushroom Soup|Canned Mushroom Soup (Open)]]
| [[Canned Mushroom Soup|Canned Mushroom Soup (Open)]]
| 0.8
| -10
| -12
| -4
| -
| 2
| 4
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedMushroomSoupOpen
|-
| [[File:CannedPeaches.png|32x32px|link=Canned Peaches|Canned Peaches]]
| [[Canned Peaches]]
| 0.8
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedPeaches
|-
| [[File:CannedPeachesOpen.png|32x32px|link=Canned Peaches|Canned Peaches (Open)]]
| [[Canned Peaches|Canned Peaches (Open)]]
| 0.8
| -15
| -19
| -
| -10
| 5
| 7
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedPeachesOpen
|-
| [[File:CannedPeas.png|32x32px|link=Canned Peas|Canned Peas]]
| [[Canned Peas]]
| 0.8
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedPeas
|-
| [[File:CannedPeasOpen.png|32x32px|link=Canned Peas|Canned Peas (Open)]]
| [[Canned Peas|Canned Peas (Open)]]
| 0.8
| -16
| -20
| -3
| -
| 2
| 4
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedPeasOpen
|-
| [[File:CannedPineapple.png|32x32px|link=Canned Pineapple|Canned Pineapple]]
| [[Canned Pineapple]]
| 0.8
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedPineapple
|-
| [[File:CannedPineappleOpen.png|32x32px|link=Canned Pineapple|Canned Pineapple (Open)]]
| [[Canned Pineapple|Canned Pineapple (Open)]]
| 0.8
| -15
| -19
| -
| -10
| 5
| 7
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedPineappleOpen
|-
| [[File:CannedPotato.png|32x32px|link=Canned Potato|Canned Potato]]
| [[Canned Potato]]
| 0.8
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedPotato2
|-
| [[File:CannedPotatoOpen.png|32x32px|link=Canned Potato|Canned Potato (Open)]]
| [[Canned Potato|Canned Potato (Open)]]
| 0.8
| -18
| -22
| -7
| -
| 2
| 4
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedPotatoOpen
|-
| [[File:CannedSardines.png|32x32px|link=Canned Sardines|Canned Sardines]]
| [[Canned Sardines]]
| 0.3
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedSardines
|-
| [[File:CannedSardinesOpen.png|32x32px|link=Canned Sardines|Canned Sardines (Open)]]
| [[Canned Sardines|Canned Sardines (Open)]]
| 0.3
| -14
| -47
| -
| -
| 2
| 4
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedSardinesOpen
|-
| [[File:CannedBolognese.png|32x32px|link=Canned Spaghetti Bolognese|Canned Spaghetti Bolognese]]
| [[Canned Spaghetti Bolognese]]
| 0.8
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedBolognese
|-
| [[File:CannedBologneseOpen.png|32x32px|link=Canned Spaghetti Bolognese|Canned Spaghetti Bolognese (Open)]]
| [[Canned Spaghetti Bolognese|Canned Spaghetti Bolognese (Open)]]
| 0.8
| -24
| -30
| -
| -
| 3
| 5
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedBologneseOpen
|-
| [[File:CannedTomato.png|32x32px|link=Canned Tomato|Canned Tomato]]
| [[Canned Tomato]]
| 0.8
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedTomato2
|-
| [[File:CannedTomatoOpen.png|32x32px|link=Canned Tomato|Canned Tomato (Open)]]
| [[Canned Tomato|Canned Tomato (Open)]]
| 0.8
| -12
| -15
| -8
| -
| 2
| 4
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedTomatoOpen
|-
| [[File:Tuna.png|32x32px|link=Canned Tuna|Canned Tuna]]
| [[Canned Tuna]]
| 0.3
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.TunaTin
|-
| [[File:TunaOpen.png|32x32px|link=Canned Tuna|Canned Tuna (Open)]]
| [[Canned Tuna|Canned Tuna (Open)]]
| 0.3
| -18
| -60
| -
| -
| 2
| 4
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.TunaTinOpen
|-
| [[File:Soup.png|32x32px|link=Canned Vegetable Soup|Canned Vegetable Soup]]
| [[Canned Vegetable Soup]]
| 0.8
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.TinnedSoup
|-
| [[File:SoupOpen.png|32x32px|link=Canned Vegetable Soup|Canned Vegetable Soup (Open)]]
| [[Canned Vegetable Soup|Canned Vegetable Soup (Open)]]
| 0.8
| -25
| -31
| -4
| -
| 2
| 4
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.TinnedSoupOpen
|-
| [[File:CannedUnlabeled_Gross.png|32x32px|link=Dented Unlabeled Can of Food|Dented Unlabeled Can of Food]]
| [[Dented Unlabeled Can of Food]]
| 0.8
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DentedCan
|-
| [[File:CannedUnlabeled.png|32x32px|link=Unlabeled Can of Food|Unlabeled Can of Food]]
| [[Unlabeled Can of Food]]
| 0.8
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.MysteryCan
|}
</div><!-- Bot_flag_end|type=food_item_list|id=canned -->

=== Protein ===

==== Meat ====
<!-- Bot_flag|type=food_item_list|id=meat --><div class="scroll-x">
{| class="wikitable theme-red sortable sticky-column" style="text-align: center;"
! Icon
! Name
! [[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Hunger_32.png|link=|Hunger]]
! [[File:Status_Hunger_32.png|link=|Hunger]]/[[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Mood_Nauseous_32.png|link=|Food Sickness]]
! [[File:UI_Fresh_Time.png|32px|link=|Fresh (days)]]
! [[File:UI_Rotten_Time.png|32px|link=|Rotten (days)]]
! [[File:UI_Cook_Time.png|32px|link=|Cooked (mins)]]
! [[File:UI_Burn_Time.png|32px|link=|Burned (mins)]]
! [[File:Pepper.png|24px|link=|Spice]]
! Item ID
|-
| <span class="cycle-img">[[File:Bacon.png|32x32px|link=Bacon|Bacon]][[File:BaconRotten.png|32x32px|link=Bacon|Bacon]][[File:BaconCooked.png|32x32px|link=Bacon|Bacon]][[File:BaconBurnt.png|32x32px|link=Bacon|Bacon]]</span>
| [[Bacon]]
| 0.3
| -12
| -40
| ?
| 3
| 5
| 20
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Bacon
|-
| <span class="cycle-img">[[File:TZ_BaconBits.png|32x32px|link=Bacon Bits|Bacon Bits]][[File:TZ_BaconBitsRotten.png|32x32px|link=Bacon Bits|Bacon Bits]][[File:TZ_BaconBitsCooked.png|32x32px|link=Bacon Bits|Bacon Bits]][[File:TZ_BaconBitsOverdone.png|32x32px|link=Bacon Bits|Bacon Bits]]</span>
| [[Bacon Bits]]
| 0.025
| -1
| -40
| ?
| 3
| 5
| 15
| 30
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.BaconBits
|-
| <span class="cycle-img">[[File:TZ_BaconRashers.png|32x32px|link=Bacon Strip|Bacon Strip]][[File:TZ_BaconRashersRotten.png|32x32px|link=Bacon Strip|Bacon Strip]][[File:TZ_BaconRashersCooked.png|32x32px|link=Bacon Strip|Bacon Strip]][[File:TZ_BaconRashersOverdone.png|32x32px|link=Bacon Strip|Bacon Strip]]</span>
| [[Bacon Strip]]
| 0.1
| -4
| -40
| ?
| 3
| 5
| 15
| 35
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BaconRashers
|-
| [[File:Baloney.png|32x32px|link=Baloney|Baloney]]
| [[Baloney]]
| 0.2
| -30
| -150
| -
| 2
| 4
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Baloney
|-
| [[File:BaloneySlices.png|32x32px|link=Baloney Slices|Baloney Slices]]
| [[Baloney Slices]]
| 0.04
| -5
| -125
| -
| 2
| 4
| 5
| 20
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BaloneySlice
|-
| <span class="cycle-img">[[File:BeefLoin.png|32x32px|link=Beef|Beef]][[File:BeefLoinRotten.png|32x32px|link=Beef|Beef]][[File:BeefLoinCooked.png|32x32px|link=Beef|Beef]][[File:BeefLoinOverdone.png|32x32px|link=Beef|Beef]]</span>
| [[Beef]]
| 0.5
| -80
| -160
| ?
| 2
| 4
| 50
| 70
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Beef
|-
| [[File:BeefJerky.png|32x32px|link=Beef Jerky|Beef Jerky]]
| [[Beef Jerky]]
| 0.2
| -20
| -100
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BeefJerky
|-
| <span class="cycle-img">[[File:MeatPatty.png|32x32px|link=Beef Patty|Beef Patty]][[File:MeatPattyRotten.png|32x32px|link=Beef Patty|Beef Patty]][[File:MeatPattyCooked.png|32x32px|link=Beef Patty|Beef Patty]][[File:MeatPattyBurnt.png|32x32px|link=Beef Patty|Beef Patty]]</span>
| [[Beef Patty]]
| 0.3
| -40
| -133
| ?
| 2
| 4
| 50
| 70
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.MeatPatty
|-
| <span class="cycle-img">[[File:ChickenWhole.png|32x32px|link=Chicken (Whole)|Chicken (Whole)]][[File:ChickenWholeRotten.png|32x32px|link=Chicken (Whole)|Chicken (Whole)]][[File:ChickenWholeCooked.png|32x32px|link=Chicken (Whole)|Chicken (Whole)]][[File:ChickenWholeOverdone.png|32x32px|link=Chicken (Whole)|Chicken (Whole)]]</span>
| [[Chicken (Whole)]]
| 1.2
| -160
| -133
| ?
| 2
| 4
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.ChickenWhole
|-
| <span class="cycle-img">[[File:ChickenFilet.png|32x32px|link=Chicken Fillet|Chicken Fillet]][[File:ChickenFiletRotten.png|32x32px|link=Chicken Fillet|Chicken Fillet]][[File:ChickenFiletCooked.png|32x32px|link=Chicken Fillet|Chicken Fillet]][[File:ChickenFiletOverdone.png|32x32px|link=Chicken Fillet|Chicken Fillet]]</span>
| [[Chicken Fillet]]
| 0.3
| -30
| -100
| ?
| 2
| 4
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.ChickenFillet
|-
| <span class="cycle-img">[[File:Chicken.png|32x32px|link=Chicken Leg|Chicken Leg]][[File:ChickenRotten.png|32x32px|link=Chicken Leg|Chicken Leg]][[File:ChickenCooked.png|32x32px|link=Chicken Leg|Chicken Leg]][[File:ChickenOverdone.png|32x32px|link=Chicken Leg|Chicken Leg]]</span>
| [[Chicken Leg]]
| 0.3
| -33
| -110
| ?
| 2
| 4
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Chicken
|-
| [[File:ChickenNuggets.png|32x32px|link=Chicken Nuggets|Chicken Nuggets]]
| [[Chicken Nuggets]]
| 0.2
| -10
| -50
| -
| 3
| 5
| 20
| 40
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.ChickenNuggets
|-
| <span class="cycle-img">[[File:ChickenWing.png|32x32px|link=Chicken Wing|Chicken Wing]][[File:ChickenWingRotten.png|32x32px|link=Chicken Wing|Chicken Wing]][[File:ChickenWingCooked.png|32x32px|link=Chicken Wing|Chicken Wing]][[File:ChickenWingOverdone.png|32x32px|link=Chicken Wing|Chicken Wing]]</span>
| [[Chicken Wing]]
| 0.3
| -19
| -63
| ?
| 2
| 4
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.ChickenWings
|-
| <span class="cycle-img">[[File:MincedMeat.png|32x32px|link=Ground Beef|Ground Beef]][[File:MincedMeatRotten.png|32x32px|link=Ground Beef|Ground Beef]][[File:MincedMeatCooked.png|32x32px|link=Ground Beef|Ground Beef]][[File:MincedMeatBurnt.png|32x32px|link=Ground Beef|Ground Beef]]</span>
| [[Ground Beef]]
| 0.3
| -40
| -133
| ?
| 2
| 4
| 50
| 70
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.MincedMeat
|-
| <span class="cycle-img">[[File:Ham.png|32x32px|link=Ham|Ham]][[File:HamRotten.png|32x32px|link=Ham|Ham]]</span>
| [[Ham]]
| 1
| -60
| -60
| -
| 5
| 10
| 20
| 40
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Ham
|-
| [[File:HamSlices.png|32x32px|link=Ham Slice|Ham Slice]]
| [[Ham Slice]]
| 0.2
| -10
| -50
| -
| 3
| 6
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.HamSlice
|-
| [[File:Hotdog_single.png|32x32px|link=Hotdog Wiener|Hotdog Wiener]]
| [[Hotdog Wiener]]
| 0.15
| -10
| -67
| -
| 3
| 6
| 20
| 40
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Hotdog_single
|-
| [[File:MeatDumpling.png|32x32px|link=Meat Dumpling|Meat Dumpling]]
| [[Meat Dumpling]]
| 0.1
| -10
| -100
| -
| 2
| 4
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.MeatDumpling
|-
| <span class="cycle-img">[[File:Mutton.png|32x32px|link=Mutton Chop|Mutton Chop]][[File:MuttonRotten.png|32x32px|link=Mutton Chop|Mutton Chop]][[File:MuttonCooked.png|32x32px|link=Mutton Chop|Mutton Chop]][[File:MuttonOverdone.png|32x32px|link=Mutton Chop|Mutton Chop]]</span>
| [[Mutton Chop]]
| 0.3
| -30
| -100
| ?
| 2
| 4
| 50
| 70
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.MuttonChop
|-
| [[File:Hotdog.png|32x32px|link=Pack of Hotdogs|Pack of Hotdogs]]
| [[Pack of Hotdogs]]
| 0.6
| -
| -
| -
| 3
| 6
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.HotdogPack
|-
| [[File:Pepperoni.png|32x32px|link=Pepperoni|Pepperoni]]
| [[Pepperoni]]
| 0.1
| -20
| -200
| -
| 15
| 30
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Pepperoni
|-
| <span class="cycle-img">[[File:PorkLoin.png|32x32px|link=Pork|Pork]][[File:PorkLoinRotten.png|32x32px|link=Pork|Pork]][[File:PorkLoinCooked.png|32x32px|link=Pork|Pork]][[File:PorkLoinOverdone.png|32x32px|link=Pork|Pork]]</span>
| [[Pork]]
| 0.5
| -60
| -120
| ?
| 2
| 4
| 50
| 70
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Pork
|-
| <span class="cycle-img">[[File:Porkchop.png|32x32px|link=Pork Chop|Pork Chop]][[File:PorkchopRotten.png|32x32px|link=Pork Chop|Pork Chop]][[File:PorkchopCooked.png|32x32px|link=Pork Chop|Pork Chop]][[File:PorkchopOverdone.png|32x32px|link=Pork Chop|Pork Chop]]</span>
| [[Pork Chop]]
| 0.3
| -30
| -100
| ?
| 2
| 4
| 50
| 70
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PorkChop
|-
| [[File:Salami.png|32x32px|link=Salami|Salami]]
| [[Salami]]
| 0.1
| -20
| -200
| -
| 10
| 15
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Salami
|-
| [[File:SalamiSlices.png|32x32px|link=Salami Slices|Salami Slices]]
| [[Salami Slices]]
| 0.02
| -4
| -200
| -
| 10
| 15
| 5
| 20
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SalamiSlice
|-
| <span class="cycle-img">[[File:Sausage.png|32x32px|link=Sausage|Sausage]][[File:SausageCooked.png|32x32px|link=Sausage|Sausage]][[File:SausageBurnt.png|32x32px|link=Sausage|Sausage]]</span>
| [[Sausage]]
| 0.1
| -20
| -200
| ?
| 2
| 4
| 50
| 70
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Sausage
|-
| <span class="cycle-img">[[File:Steak.png|32x32px|link=Steak|Steak]][[File:SteakRotten.png|32x32px|link=Steak|Steak]][[File:SteakCooked.png|32x32px|link=Steak|Steak]][[File:SteakOverdone.png|32x32px|link=Steak|Steak]]</span>
| [[Steak]]
| 0.3
| -40
| -133
| ?
| 2
| 4
| 50
| 70
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Steak
|-
| <span class="cycle-img">[[File:TurkeyWhole.png|32x32px|link=Turkey (Whole)|Turkey (Whole)]][[File:TurkeyWholeRotten.png|32x32px|link=Turkey (Whole)|Turkey (Whole)]][[File:TurkeyWholeCooked.png|32x32px|link=Turkey (Whole)|Turkey (Whole)]][[File:TurkeyWholeOverdone.png|32x32px|link=Turkey (Whole)|Turkey (Whole)]]</span>
| [[Turkey (Whole)]]
| 1.3
| -224
| -172
| ?
| 2
| 4
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.TurkeyWhole
|-
| <span class="cycle-img">[[File:TurkeyFilet.png|32x32px|link=Turkey Fillet|Turkey Fillet]][[File:TurkeyFiletRotten.png|32x32px|link=Turkey Fillet|Turkey Fillet]][[File:TurkeyFiletCooked.png|32x32px|link=Turkey Fillet|Turkey Fillet]][[File:TurkeyFiletOverdone.png|32x32px|link=Turkey Fillet|Turkey Fillet]]</span>
| [[Turkey Fillet]]
| 0.3
| -50
| -167
| ?
| 2
| 4
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.TurkeyFillet
|-
| <span class="cycle-img">[[File:TurkeyLeg.png|32x32px|link=Turkey Leg|Turkey Leg]][[File:TurkeyLegRotten.png|32x32px|link=Turkey Leg|Turkey Leg]][[File:TurkeyLegCooked.png|32x32px|link=Turkey Leg|Turkey Leg]][[File:TurkeyLegOverdone.png|32x32px|link=Turkey Leg|Turkey Leg]]</span>
| [[Turkey Leg]]
| 0.3
| -42
| -140
| ?
| 2
| 4
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.TurkeyLegs
|-
| <span class="cycle-img">[[File:TurkeyWing.png|32x32px|link=Turkey Wing|Turkey Wing]][[File:TurkeyWingRotten.png|32x32px|link=Turkey Wing|Turkey Wing]][[File:TurkeyWingCooked.png|32x32px|link=Turkey Wing|Turkey Wing]][[File:TurkeyWingOverdone.png|32x32px|link=Turkey Wing|Turkey Wing]]</span>
| [[Turkey Wing]]
| 0.3
| -30
| -100
| ?
| 2
| 4
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.TurkeyWings
|-
| <span class="cycle-img">[[File:Venison.png|32x32px|link=Venison|Venison]][[File:VenisonRotten.png|32x32px|link=Venison|Venison]][[File:VenisonCooked.png|32x32px|link=Venison|Venison]][[File:VenisonOverdone.png|32x32px|link=Venison|Venison]]</span>
| [[Venison]]
| 0.5
| -80
| -160
| ?
| 2
| 4
| 50
| 70
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Venison
|}
</div><!-- Bot_flag_end|type=food_item_list|id=meat -->

==== Game ====
<!-- Bot_flag|type=food_item_list|id=game --><div class="scroll-x">
{| class="wikitable theme-red sortable sticky-column" style="text-align: center;"
! Icon
! Name
! [[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Hunger_32.png|link=|Hunger]]
! [[File:Status_Hunger_32.png|link=|Hunger]]/[[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Mood_Sad_32.png|link=|Unhappiness]]
! [[File:Mood_Nauseous_32.png|link=|Food Sickness]]
! [[File:UI_Fresh_Time.png|32px|link=|Fresh (days)]]
! [[File:UI_Rotten_Time.png|32px|link=|Rotten (days)]]
! [[File:UI_Cook_Time.png|32px|link=|Cooked (mins)]]
! [[File:UI_Burn_Time.png|32px|link=|Burned (mins)]]
! [[File:Pepper.png|24px|link=|Spice]]
! Item ID
|-
| <span class="cycle-img">[[File:BirdDead.png|32x32px|link=Dead Bird|Dead Bird]][[File:BirdDeadRotten.png|32x32px|link=Dead Bird|Dead Bird]]</span>
| [[Dead Bird]]
| 0.1
| -15
| -150
| 20*
| ?
| 8
| 12
| 25
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DeadBird
|-
| <span class="cycle-img">[[File:MouseDead.png|32x32px|link=Dead Mouse|Dead Mouse]][[File:MouseDeadRotten.png|32x32px|link=Dead Mouse|Dead Mouse]]</span>
| [[Dead Mouse]]
| 0.05
| -10
| -200
| 30
| ?
| 6
| 10
| 15
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DeadMouse
|-
| [[File:RabbitDead.png|32x32px|link=Dead Rabbit|Dead Rabbit]]
| [[Dead Rabbit]]
| 1
| -45
| -45
| 20*
| ?
| 8
| 12
| 25
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DeadRabbit
|-
| <span class="cycle-img">[[File:DeadRat.png|32x32px|link=Dead Rat|Dead Rat]][[File:DeadRatRotten.png|32x32px|link=Dead Rat|Dead Rat]][[File:DeadRatCooked.png|32x32px|link=Dead Rat|Dead Rat]]</span>
| [[Dead Rat]]
| 0.2
| -22
| -110
| 30
| ?
| 6
| 10
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DeadRat
|-
| [[File:SquirrelDead.png|32x32px|link=Dead Squirrel|Dead Squirrel]]
| [[Dead Squirrel]]
| 0.4
| -32
| -80
| 20*
| ?
| 8
| 12
| 25
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DeadSquirrel
|-
| <span class="cycle-img">[[File:Frogmeat.png|32x32px|link=Frog Meat|Frog Meat]][[File:FrogmeatRotten.png|32x32px|link=Frog Meat|Frog Meat]][[File:FrogmeatCooked.png|32x32px|link=Frog Meat|Frog Meat]][[File:FrogmeatOverdone.png|32x32px|link=Frog Meat|Frog Meat]]</span>
| [[Frog Meat]]
| 0.2
| -10
| -50
| -
| ?
| 4
| 8
| 10
| 40
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.FrogMeat
|-
| <span class="cycle-img">[[File:MouseDead.png|32x32px|link=Mouse Pups (Dead)|Mouse Pups (Dead)]][[File:MouseDeadRotten.png|32x32px|link=Mouse Pups (Dead)|Mouse Pups (Dead)]]</span>
| [[Mouse Pups (Dead)]]
| 0.03
| -5
| -167
| 30
| ?
| 6
| 10
| 15
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DeadMousePups
|-
| <span class="cycle-img">[[File:Rabbitmeat.png|32x32px|link=Rabbit Meat|Rabbit Meat]][[File:RabbitmeatRotten.png|32x32px|link=Rabbit Meat|Rabbit Meat]][[File:RabbitmeatCooked.png|32x32px|link=Rabbit Meat|Rabbit Meat]][[File:RabbitmeatOverdone.png|32x32px|link=Rabbit Meat|Rabbit Meat]]</span>
| [[Rabbit Meat]]
| 0.3
| -30
| -100
| -
| ?
| 2
| 4
| 25
| 70
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Rabbitmeat
|-
| <span class="cycle-img">[[File:DeadRat.png|32x32px|link=Rat Baby (Dead)|Rat Baby (Dead)]][[File:DeadRatRotten.png|32x32px|link=Rat Baby (Dead)|Rat Baby (Dead)]][[File:DeadRatCooked.png|32x32px|link=Rat Baby (Dead)|Rat Baby (Dead)]]</span>
| [[Rat Baby (Dead)]]
| 0.12
| -12
| -100
| 30
| ?
| 6
| 10
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DeadRatBaby
|-
| [[File:RatKing.png|32x32px|link=Rat King (Dead)|Rat King (Dead)]]
| [[Rat King (Dead)]]
| 1
| -110
| -110
| 150
| ?
| ∞
| ∞
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.RatKing
|-
| <span class="cycle-img">[[File:Smallanimalmeat.png|32x32px|link=Rodent Meat|Rodent Meat]][[File:SmallanimalmeatRotten.png|32x32px|link=Rodent Meat|Rodent Meat]][[File:SmallanimalmeatCooked.png|32x32px|link=Rodent Meat|Rodent Meat]][[File:SmallanimalmeatOverdone.png|32x32px|link=Rodent Meat|Rodent Meat]]</span>
| [[Rodent Meat]]
| 0.3
| -15
| -50
| -
| ?
| 2
| 4
| 20
| 70
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Smallanimalmeat
|-
| [[File:MouseSkinned.png|32x32px|link=Skinned Mouse (Dead)|Skinned Mouse (Dead)]]
| [[Skinned Mouse (Dead)]]
| 0.05
| -10
| -200
| 30
| ?
| 6
| 10
| 15
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DeadMouseSkinned
|-
| [[File:MouseSkinned.png|32x32px|link=Skinned Mouse Pups (Dead)|Skinned Mouse Pups (Dead)]]
| [[Skinned Mouse Pups (Dead)]]
| 0.03
| -5
| -167
| 30
| ?
| 6
| 10
| 15
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DeadMousePupsSkinned
|-
| [[File:RatSkinned.png|32x32px|link=Skinned Rat (Dead)|Skinned Rat (Dead)]]
| [[Skinned Rat (Dead)]]
| 0.2
| -22
| -110
| 30
| ?
| 6
| 10
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DeadRatSkinned
|-
| [[File:RatSkinned.png|32x32px|link=Skinned Rat Baby (Dead)|Skinned Rat Baby (Dead)]]
| [[Skinned Rat Baby (Dead)]]
| 0.12
| -12
| -100
| 30
| ?
| 6
| 10
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DeadRatBabySkinned
|-
| <span class="cycle-img">[[File:Smallbirdmeat.png|32x32px|link=Small Bird Meat|Small Bird Meat]][[File:SmallbirdmeatRotten.png|32x32px|link=Small Bird Meat|Small Bird Meat]][[File:SmallbirdmeatCooked.png|32x32px|link=Small Bird Meat|Small Bird Meat]][[File:SmallbirdmeatOverdone.png|32x32px|link=Small Bird Meat|Small Bird Meat]]</span>
| [[Small Bird Meat]]
| 0.3
| -15
| -50
| -
| ?
| 2
| 4
| 20
| 70
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Smallbirdmeat
|}
</div><!-- Bot_flag_end|type=food_item_list|id=game -->

==== Seafood ====
<!-- Bot_flag|type=food_item_list|id=seafood --><div class="scroll-x">
{| class="wikitable theme-red sortable sticky-column" style="text-align: center;"
! Icon
! Name
! [[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Hunger_32.png|link=|Hunger]]
! [[File:Status_Hunger_32.png|link=|Hunger]]/[[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Mood_Sad_32.png|link=|Unhappiness]]
! [[File:Mood_Nauseous_32.png|link=|Food Sickness]]
! [[File:UI_Fresh_Time.png|32px|link=|Fresh (days)]]
! [[File:UI_Rotten_Time.png|32px|link=|Rotten (days)]]
! [[File:UI_Cook_Time.png|32px|link=|Cooked (mins)]]
! [[File:UI_Burn_Time.png|32px|link=|Burned (mins)]]
! [[File:Pepper.png|24px|link=|Spice]]
! Item ID
|-
| [[File:Fish_GarAlligator.png|32x32px|link=Alligator Gar|Alligator Gar]]
| [[Alligator Gar]]
| 0.4
| -15
| -38
| 20*
| ?
| 4
| 8
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.AligatorGar
|-
| [[File:Frozen_FishFingers.png|32x32px|link=Bag of Fish Fingers|Bag of Fish Fingers]]
| [[Bag of Fish Fingers]]
| 1
| -
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Frozen_FishFingers
|-
| [[File:Fish_CrappieBlack.png|32x32px|link=Black Crappie|Black Crappie]]
| [[Black Crappie]]
| 0.4
| -15
| -38
| 20*
| ?
| 4
| 8
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BlackCrappie
|-
| [[File:Fish_CatfishBlue.png|32x32px|link=Blue Catfish|Blue Catfish]]
| [[Blue Catfish]]
| 0.4
| -15
| -38
| 20*
| ?
| 4
| 8
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BlueCatfish
|-
| [[File:Fish_Bluegill.png|32x32px|link=Bluegill|Bluegill]]
| [[Bluegill]]
| 0.4
| -15
| -38
| 20*
| ?
| 4
| 8
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Bluegill
|-
| [[File:Fish_CatfishChannel.png|32x32px|link=Channel Catfish|Channel Catfish]]
| [[Channel Catfish]]
| 0.4
| -15
| -38
| 20*
| ?
| 4
| 8
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.ChannelCatfish
|-
| <span class="cycle-img">[[File:Crayfish.png|32x32px|link=Crayfish|Crayfish]][[File:CrayfishRotten.png|32x32px|link=Crayfish|Crayfish]][[File:CrayfishCooked.png|32x32px|link=Crayfish|Crayfish]]</span>
| [[Crayfish]]
| 0.2
| -10
| -50
| -
| ?
| 2
| 4
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Crayfish
|-
| [[File:FishFried.png|32x32px|link=Fish (Fried)|Fish (Fried)]]
| [[Fish (Fried)]]
| 0.2
| -30
| -150
| -
| -
| 4
| 7
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.FishFried
|-
| <span class="cycle-img">[[File:FishFillet.png|32x32px|link=Fish Fillet|Fish Fillet]][[File:FishFilletRotten.png|32x32px|link=Fish Fillet|Fish Fillet]][[File:FishFilletCooked.png|32x32px|link=Fish Fillet|Fish Fillet]][[File:FishFilletOverdone.png|32x32px|link=Fish Fillet|Fish Fillet]]</span>
| [[Fish Fillet]]
| 0.2
| -25
| -125
| -
| ?
| 2
| 4
| 20
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.FishFillet
|-
| [[File:FishFingers.png|32x32px|link=Fish Fingers|Fish Fingers]]
| [[Fish Fingers]]
| 0.2
| -10
| -50
| -
| -
| 3
| 5
| 20
| 40
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.FishFingers
|-
| [[File:Fish_Guts.png|32x32px|link=Fish Guts|Fish Guts]]
| [[Fish Guts]]
| 0.1
| -5
| -50
| 20
| ?
| 4
| 8
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.FishGuts
|-
| [[File:FishRoe.png|32x32px|link=Fish Roe|Fish Roe]]
| [[Fish Roe]]
| 0.1
| -10
| -100
| -
| -
| 14
| 21
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.FishRoe
|-
| [[File:Fish_EggSack.png|32x32px|link=Fish Roe Sac|Fish Roe Sac]]
| [[Fish Roe Sac]]
| 0.1
| -5
| -50
| 20
| ?
| 4
| 8
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.FishRoeSac
|-
| [[File:SushiFish.png|32x32px|link=Fish Sushi|Fish Sushi]]
| [[Fish Sushi]]
| 0.1
| -8
| -80
| -10
| -
| 2
| 4
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SushiFish
|-
| [[File:Fish_CatfishFlathead.png|32x32px|link=Flathead Catfish|Flathead Catfish]]
| [[Flathead Catfish]]
| 0.4
| -15
| -38
| 20*
| ?
| 4
| 8
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.FlatheadCatfish
|-
| [[File:Fish_DrumFreshwater.png|32x32px|link=Freshwater Drum|Freshwater Drum]]
| [[Freshwater Drum]]
| 0.4
| -15
| -38
| 20*
| ?
| 4
| 8
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.FreshwaterDrum
|-
| [[File:ShrimpFried.png|32x32px|link=Fried Shrimp|Fried Shrimp]]
| [[Fried Shrimp]]
| 0.1
| -15
| -150
| -
| -
| 2
| 4
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.ShrimpFried
|-
| [[File:ShrimpFried.png|32x32px|link=Fried Shrimp|Fried Shrimp]]
| [[Fried Shrimp]]
| 0.1
| -15
| -150
| -
| -
| 2
| 4
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.ShrimpFriedCraft
|-
| [[File:Fish_SunfishGreen.png|32x32px|link=Green Sunfish|Green Sunfish]]
| [[Green Sunfish]]
| 0.4
| -15
| -38
| 20*
| ?
| 4
| 8
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.GreenSunfish
|-
| [[File:Fish_BassLargemouth.png|32x32px|link=Largemouth Bass|Largemouth Bass]]
| [[Largemouth Bass]]
| 0.4
| -15
| -38
| 20*
| ?
| 4
| 8
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.LargemouthBass
|-
| [[File:FishMinnow.png|32x32px|link=Little Bait Fish|Little Bait Fish]]
| [[Little Bait Fish]]
| 0.1
| -3
| -30
| 20*
| ?
| 4
| 8
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BaitFish
|-
| <span class="cycle-img">[[File:Lobster.png|32x32px|link=Lobster|Lobster]][[File:LobsterRotten.png|32x32px|link=Lobster|Lobster]][[File:LobsterCooked.png|32x32px|link=Lobster|Lobster]][[File:LobsterBurnt.png|32x32px|link=Lobster|Lobster]]</span>
| [[Lobster]]
| 0.4
| -40
| -100
| -
| ?
| 2
| 4
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Lobster
|-
| [[File:Fish_Muskellunge.png|32x32px|link=Muskellunge|Muskellunge]]
| [[Muskellunge]]
| 0.4
| -15
| -38
| 20*
| ?
| 4
| 8
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Muskellunge
|-
| <span class="cycle-img">[[File:Mussels.png|32x32px|link=Mussels|Mussels]][[File:MusselsCooked.png|32x32px|link=Mussels|Mussels]]</span>
| [[Mussels]]
| 0.1
| -5
| -50
| -
| -
| 2
| 4
| 10
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Mussels
|-
| <span class="cycle-img">[[File:Oysters.png|32x32px|link=Oysters|Oysters]][[File:OystersCooked.png|32x32px|link=Oysters|Oysters]]</span>
| [[Oysters]]
| 0.1
| -5
| -50
| -
| -
| 2
| 4
| 10
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Oysters
|-
| [[File:OystersFried.png|32x32px|link=Oysters (Fried)|Oysters (Fried)]]
| [[Oysters (Fried)]]
| 0.1
| -6
| -60
| -
| -
| 4
| 7
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.OystersFried
|-
| [[File:Fish_Paddlefish.png|32x32px|link=Paddlefish|Paddlefish]]
| [[Paddlefish]]
| 0.4
| -15
| -38
| 20*
| ?
| 4
| 8
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Paddlefish
|-
| [[File:Fish_SunfishRedear.png|32x32px|link=Redear Sunfish|Redear Sunfish]]
| [[Redear Sunfish]]
| 0.4
| -15
| -38
| 20*
| ?
| 4
| 8
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.RedearSunfish
|-
| <span class="cycle-img">[[File:Salmon.png|32x32px|link=Salmon|Salmon]][[File:SalmonRotten.png|32x32px|link=Salmon|Salmon]][[File:SalmonCooked.png|32x32px|link=Salmon|Salmon]][[File:SalmonOverdone.png|32x32px|link=Salmon|Salmon]]</span>
| [[Salmon]]
| 0.3
| -30
| -100
| -
| ?
| 2
| 4
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Salmon
|-
| [[File:Fish_Sauger.png|32x32px|link=Sauger|Sauger]]
| [[Sauger]]
| 0.4
| -15
| -38
| 20*
| ?
| 4
| 8
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Sauger
|-
| <span class="cycle-img">[[File:Shrimp.png|32x32px|link=Shrimp|Shrimp]][[File:ShrimpRotten.png|32x32px|link=Shrimp|Shrimp]][[File:ShrimpCooked.png|32x32px|link=Shrimp|Shrimp]][[File:ShrimpBurnt.png|32x32px|link=Shrimp|Shrimp]]</span>
| [[Shrimp]]
| 0.1
| -10
| -100
| -
| ?
| 2
| 4
| 10
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Shrimp
|-
| [[File:ShrimpDumpling.png|32x32px|link=Shrimp Dumpling|Shrimp Dumpling]]
| [[Shrimp Dumpling]]
| 0.1
| -15
| -150
| -
| -
| 2
| 4
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.ShrimpDumpling
|-
| [[File:Fish_BassSmallmouth.png|32x32px|link=Smallmouth Bass|Smallmouth Bass]]
| [[Smallmouth Bass]]
| 0.4
| -15
| -38
| 20*
| ?
| 4
| 8
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SmallmouthBass
|-
| [[File:Fish_BassSpotted.png|32x32px|link=Spotted Bass|Spotted Bass]]
| [[Spotted Bass]]
| 0.4
| -15
| -38
| 20*
| ?
| 4
| 8
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SpottedBass
|-
| [[File:Squid.png|32x32px|link=Squid|Squid]]
| [[Squid]]
| 0.2
| -30
| -150
| -
| -
| 2
| 4
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Squid
|-
| [[File:SquidCalimari.png|32x32px|link=Squid Calamari|Squid Calamari]]
| [[Squid Calamari]]
| 0.1
| -10
| -100
| -
| -
| 2
| 4
| 10
| 20
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SquidCalamari
|-
| [[File:Fish_BassStriped.png|32x32px|link=Striped Bass|Striped Bass]]
| [[Striped Bass]]
| 0.4
| -15
| -38
| 20*
| ?
| 4
| 8
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.StripedBass
|-
| [[File:Caviar.png|32x32px|link=Tin of Caviar|Tin of Caviar]]
| [[Tin of Caviar]]
| 0.2
| -10
| -50
| -20
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Caviar
|-
| [[File:Fish_Walleye.png|32x32px|link=Walleye|Walleye]]
| [[Walleye]]
| 0.4
| -15
| -38
| 20*
| ?
| 4
| 8
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Walleye
|-
| [[File:Fish_BassWhite.png|32x32px|link=White Bass|White Bass]]
| [[White Bass]]
| 0.4
| -15
| -38
| 20*
| ?
| 4
| 8
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.WhiteBass
|-
| [[File:Fish_CrappieWhite.png|32x32px|link=White Crappie|White Crappie]]
| [[White Crappie]]
| 0.4
| -15
| -38
| 20*
| ?
| 4
| 8
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.WhiteCrappie
|-
| [[File:Fish_PerchYellow.png|32x32px|link=Yellow Perch|Yellow Perch]]
| [[Yellow Perch]]
| 0.4
| -15
| -38
| 20*
| ?
| 4
| 8
| 20
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.YellowPerch
|}
</div><!-- Bot_flag_end|type=food_item_list|id=seafood -->

==== Egg ====
<!-- Bot_flag|type=food_item_list|id=egg --><div class="scroll-x">
{| class="wikitable theme-red sortable sticky-column" style="text-align: center;"
! Icon
! Name
! [[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Hunger_32.png|link=|Hunger]]
! [[File:Status_Hunger_32.png|link=|Hunger]]/[[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Mood_Nauseous_32.png|link=|Food Sickness]]
! [[File:UI_Fresh_Time.png|32px|link=|Fresh (days)]]
! [[File:UI_Rotten_Time.png|32px|link=|Rotten (days)]]
! [[File:UI_Cook_Time.png|32px|link=|Cooked (mins)]]
! [[File:UI_Burn_Time.png|32px|link=|Burned (mins)]]
! [[File:Pepper.png|24px|link=|Spice]]
! Item ID
|-
| [[File:Egg.png|32x32px|link=Egg|Egg]]
| [[Egg]]
| 0.1
| -7
| -70
| ?
| 14
| 21
| 4
| 20
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Egg
|-
| [[File:EggBoiled.png|32x32px|link=Egg (Boiled)|Egg (Boiled)]]
| [[Egg (Boiled)]]
| 0.1
| -10
| -100
| -
| 3
| 6
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.EggBoiled
|-
| [[File:EggPoached.png|32x32px|link=Egg (Poached)|Egg (Poached)]]
| [[Egg (Poached)]]
| 0.1
| -10
| -100
| -
| 3
| 6
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.EggPoached
|-
| [[File:EggScrambled.png|32x32px|link=Egg (Scrambled)|Egg (Scrambled)]]
| [[Egg (Scrambled)]]
| 0.1
| -20
| -200
| -
| 3
| 6
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.EggScrambled
|-
| [[File:EggCarton.png|32x32px|link=Egg Carton|Egg Carton]]
| [[Egg Carton]]
| 1
| -
| -
| -
| 14
| 21
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.EggCarton
|-
| [[File:EggOmelette.png|32x32px|link=Omelette|Omelette]]
| [[Omelette]]
| 0.1
| -20
| -200
| -
| 3
| 6
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.EggOmelette
|-
| [[File:Egg_Turkey.png|32x32px|link=Turkey Egg|Turkey Egg]]
| [[Turkey Egg]]
| 0.1
| -10
| -100
| ?
| 14
| 21
| 4
| 20
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.TurkeyEgg
|-
| <span class="cycle-img">[[File:WildEggs.png|32x32px|link=Wild Eggs|Wild Eggs]][[File:WildEggsCooked.png|32x32px|link=Wild Eggs|Wild Eggs]]</span>
| [[Wild Eggs]]
| 0.1
| -7
| -70
| ?
| 14
| 21
| 4
| 20
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.WildEggs
|}
</div><!-- Bot_flag_end|type=food_item_list|id=egg -->

==== Insects ====
<!-- Bot_flag|type=food_item_list|id=insect --><div class="scroll-x">
{| class="wikitable theme-red sortable sticky-column" style="text-align: center;"
! Icon
! Name
! [[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Hunger_32.png|link=|Hunger]]
! [[File:Status_Hunger_32.png|link=|Hunger]]/[[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Mood_Sad_32.png|link=|Unhappiness]]
! [[File:Mood_Nauseous_32.png|link=|Food Sickness]]
! [[File:SkullPoison.png|link=|Poison]]
! [[File:UI_Fresh_Time.png|32px|link=|Fresh (days)]]
! [[File:UI_Rotten_Time.png|32px|link=|Rotten (days)]]
! [[File:UI_Cook_Time.png|32px|link=|Cooked (mins)]]
! [[File:UI_Burn_Time.png|32px|link=|Burned (mins)]]
! [[File:Pepper.png|24px|link=|Spice]]
! Item ID
|-
| [[File:Insect_AmericanLadyCaterpillar.png|32x32px|link=Caterpillar (American lady)|Caterpillar]]
| [[Caterpillar (American lady)|Caterpillar]]
| 0.1
| -1
| -10
| 20
| -
| -
| 14
| 21
| 5
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.AmericanLadyCaterpillar
|-
| [[File:Insect_BandedWoolyBearCaterpillar.png|32x32px|link=Caterpillar (banded woolly bear)|Caterpillar]]
| [[Caterpillar (banded woolly bear)|Caterpillar]]
| 0.1
| -1
| -10
| 20
| -
| -
| 14
| 21
| 5
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BandedWoolyBearCaterpillar
|-
| [[File:Insect_MonarchrCaterpillar.png|32x32px|link=Caterpillar (monarch)|Caterpillar]]
| [[Caterpillar (monarch)|Caterpillar]]
| 0.1
| -1
| -10
| 20
| -
| 1
| 14
| 21
| 5
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.MonarchCaterpillar
|-
| [[File:Insect_SawflyLarva.png|32x32px|link=Caterpillar (sawfly larva)|Caterpillar]]
| [[Caterpillar (sawfly larva)|Caterpillar]]
| 0.1
| -1
| -10
| 20
| -
| -
| 14
| 21
| 5
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SawflyLarva
|-
| [[File:Insect_SilkMothCaterpillar.png|32x32px|link=Caterpillar (silk moth)|Caterpillar]]
| [[Caterpillar (silk moth)|Caterpillar]]
| 0.1
| -1
| -10
| 20
| -
| -
| 14
| 21
| 5
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SilkMothCaterpillar
|-
| [[File:Insect_SwallowtailCaterpillar.png|32x32px|link=Caterpillar (swallowtail)|Caterpillar]]
| [[Caterpillar (swallowtail)|Caterpillar]]
| 0.1
| -1
| -10
| 20
| -
| 1
| 14
| 21
| 5
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SwallowtailCaterpillar
|-
| [[File:Insect_Centipede1.png|32x32px|link=Centipede|Centipede]]
| [[Centipede]]
| 0.1
| -1
| -10
| 20
| ?
| -
| 14
| 21
| 5
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Centipede
|-
| [[File:Insect_Centipede2.png|32x32px|link=Centipede|Centipede]]
| [[Centipede]]
| 0.1
| -1
| -10
| 20
| ?
| -
| 14
| 21
| 5
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Centipede2
|-
| <span class="cycle-img">[[File:Cockroach.png|32x32px|link=Cockroach|Cockroach]][[File:CockroachCooked.png|32x32px|link=Cockroach|Cockroach]]</span>
| [[Cockroach]]
| 0.1
| -1
| -10
| 20
| -
| -
| 14
| 21
| 5
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Cockroach
|-
| <span class="cycle-img">[[File:Cricket.png|32x32px|link=Cricket|Cricket]][[File:CricketCooked.png|32x32px|link=Cricket|Cricket]]</span>
| [[Cricket]]
| 0.1
| -1
| -10
| 20
| -
| -
| 14
| 21
| 5
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Cricket
|-
| <span class="cycle-img">[[File:Grasshopper.png|32x32px|link=Grasshopper|Grasshopper]][[File:GrasshopperCooked.png|32x32px|link=Grasshopper|Grasshopper]]</span>
| [[Grasshopper]]
| 0.1
| -1
| -10
| 20
| -
| -
| 14
| 21
| 5
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Grasshopper
|-
| [[File:Insect_Ladybug.png|32x32px|link=Ladybug|Ladybug]]
| [[Ladybug]]
| 0.01
| -1
| -100
| 20
| -
| -
| 14
| 21
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Ladybug
|-
| [[File:leech.png|32x32px|link=Leech|Leech]]
| [[Leech]]
| 0.1
| -1
| -10
| 20
| ?
| -
| 2
| 4
| 5
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Leech
|-
| [[File:Insect_Maggots.png|32x32px|link=Maggots|Maggots]]
| [[Maggots]]
| 0.01
| -1
| -100
| 20
| -
| -
| 14
| 21
| 5
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Maggots
|-
| [[File:Insect_Millipede1.png|32x32px|link=Millipede|Millipede]]
| [[Millipede]]
| 0.1
| -1
| -10
| 20
| ?
| 1
| 14
| 21
| 5
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Millipede
|-
| [[File:Insect_Millipede2.png|32x32px|link=Millipede|Millipede]]
| [[Millipede]]
| 0.1
| -1
| -10
| 20
| ?
| 1
| 14
| 21
| 5
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Millipede2
|-
| [[File:Insect_Pillbug.png|32x32px|link=Pillbug|Pillbug]]
| [[Pillbug]]
| 0.01
| -1
| -100
| 20
| -
| -
| 14
| 21
| 5
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Pillbug
|-
| [[File:Slug1.png|32x32px|link=Slug|Slug]]
| [[Slug]]
| 0.1
| -1
| -10
| 20
| ?
| -
| 4
| 8
| 5
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Slug
|-
| [[File:Slug2.png|32x32px|link=Slug|Slug]]
| [[Slug]]
| 0.1
| -1
| -10
| 20
| ?
| -
| 4
| 8
| 5
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Slug2
|-
| [[File:Snail.png|32x32px|link=Snail|Snail]]
| [[Snail]]
| 0.1
| -1
| -10
| 20
| ?
| -
| 4
| 8
| 5
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Snail
|-
| [[File:Insect_Termite.png|32x32px|link=Termites|Termites]]
| [[Termites]]
| 0.01
| -1
| -100
| 20
| -
| -
| 14
| 21
| 5
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Termites
|-
| [[File:Worm.png|32x32px|link=Worm|Worm]]
| [[Worm]]
| 0.01
| -1
| -100
| 20
| -
| -
| 4
| 8
| 5
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Worm
|}
</div><!-- Bot_flag_end|type=food_item_list|id=insect -->

=== Fruits ===
<!-- Bot_flag|type=food_item_list|id=fruit --><div class="scroll-x">
{| class="wikitable theme-red sortable sticky-column" style="text-align: center;"
! Icon
! Name
! [[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Hunger_32.png|link=|Hunger]]
! [[File:Status_Hunger_32.png|link=|Hunger]]/[[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Thirst_32.png|link=|Thirst]]
! [[File:Mood_Sad_32.png|link=|Unhappiness]]
! [[File:UI_Fresh_Time.png|32px|link=|Fresh (days)]]
! [[File:UI_Rotten_Time.png|32px|link=|Rotten (days)]]
! [[File:Pepper.png|24px|link=|Spice]]
! Item ID
|-
| <span class="cycle-img">[[File:Apple.png|32x32px|link=Apple|Apple]][[File:AppleRotten.png|32x32px|link=Apple|Apple]]</span>
| [[Apple]]
| 0.2
| -16
| -80
| -7
| -
| 5
| 8
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Apple
|-
| [[File:DriedApricots.png|32x32px|link=Apricots (Dried)|Apricots (Dried)]]
| [[Apricots (Dried)]]
| 0.2
| -16
| -80
| -
| -
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DriedApricots
|-
| <span class="cycle-img">[[File:Banana.png|32x32px|link=Banana|Banana]][[File:BananaRotten.png|32x32px|link=Banana|Banana]]</span>
| [[Banana]]
| 0.2
| -16
| -80
| -5
| -
| 5
| 7
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Banana
|-
| [[File:BeautyBerries.png|32x32px|link=Berries (beautyberry)|Berries]]
| [[Berries (beautyberry)|Berries]]
| 0.1
| -10
| -100
| -1
| -
| 6
| 10
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BeautyBerry
|-
| [[File:HollyBerries.png|32x32px|link=Berries (holly berry)|Berries]]
| [[Berries (holly berry)|Berries]]
| 0.1
| -10
| -100
| -1
| -
| 6
| 10
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.HollyBerry
|-
| [[File:Winterberries.png|32x32px|link=Berries (winterberry)|Berries]]
| [[Berries (winterberry)|Berries]]
| 0.1
| -10
| -100
| -1
| -
| 6
| 10
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.WinterBerry
|-
| <span class="cycle-img">[[File:BerryBlack.png|32x32px|link=Berries|Berries]][[File:BerryBlackRotten.png|32x32px|link=Berries|Berries]]</span>
| [[Berries]]
| 0.1
| -10
| -100
| -1
| -
| 6
| 10
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BerryBlack
|-
| <span class="cycle-img">[[File:BerryBlue.png|32x32px|link=Berries|Berries]][[File:BerryBlueRotten.png|32x32px|link=Berries|Berries]]</span>
| [[Berries]]
| 0.1
| -10
| -100
| -1
| -
| 6
| 10
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BerryBlue
|-
| <span class="cycle-img">[[File:BerryGeneric1.png|32x32px|link=Berries|Berries]][[File:BerryGeneric1Rotten.png|32x32px|link=Berries|Berries]]</span>
| [[Berries]]
| 0.1
| -5
| -50
| -1
| -
| 6
| 10
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BerryGeneric1
|-
| <span class="cycle-img">[[File:BerryGeneric2.png|32x32px|link=Berries|Berries]][[File:BerryGeneric2Rotten.png|32x32px|link=Berries|Berries]]</span>
| [[Berries]]
| 0.1
| -10
| -100
| -1
| -
| 6
| 10
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BerryGeneric2
|-
| <span class="cycle-img">[[File:BerryGeneric3.png|32x32px|link=Berries|Berries]][[File:BerryGeneric3Rotten.png|32x32px|link=Berries|Berries]]</span>
| [[Berries]]
| 0.1
| -5
| -50
| -1
| -
| 6
| 10
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BerryGeneric3
|-
| <span class="cycle-img">[[File:BerryGeneric4.png|32x32px|link=Berries|Berries]][[File:BerryGeneric4Rotten.png|32x32px|link=Berries|Berries]]</span>
| [[Berries]]
| 0.1
| -10
| -100
| -1
| -
| 6
| 10
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BerryGeneric4
|-
| <span class="cycle-img">[[File:BerryGeneric5.png|32x32px|link=Berries|Berries]][[File:BerryGeneric5Rotten.png|32x32px|link=Berries|Berries]]</span>
| [[Berries]]
| 0.1
| -10
| -100
| -1
| -
| 6
| 10
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BerryGeneric5
|-
| [[File:BerryPoisonIvy.png|32x32px|link=Berries|Berries]]
| [[Berries]]
| 0.1
| -5
| -50
| -1
| -
| 6
| 10
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BerryPoisonIvy
|-
| <span class="cycle-img">[[File:Cherry.png|32x32px|link=Cherry|Cherry]][[File:CherryRotten.png|32x32px|link=Cherry|Cherry]]</span>
| [[Cherry]]
| 0.1
| -3
| -30
| -1
| -
| 4
| 9
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Cherry
|-
| <span class="cycle-img">[[File:Grapefruit.png|32x32px|link=Grapefruit|Grapefruit]][[File:GrapefruitRotten.png|32x32px|link=Grapefruit|Grapefruit]]</span>
| [[Grapefruit]]
| 0.3
| -20
| -67
| -50
| -
| 6
| 8
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Grapefruit
|-
| <span class="cycle-img">[[File:Grapes.png|32x32px|link=Grapes|Grapes]][[File:GrapesRotten.png|32x32px|link=Grapes|Grapes]]</span>
| [[Grapes]]
| 0.2
| -15
| -75
| -5
| -
| 5
| 8
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Grapes
|-
| <span class="cycle-img">[[File:Lemon.png|32x32px|link=Lemon|Lemon]][[File:LemonRotten.png|32x32px|link=Lemon|Lemon]]</span>
| [[Lemon]]
| 0.2
| -10
| -50
| -5
| -
| 7
| 9
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Lemon
|-
| <span class="cycle-img">[[File:Lime.png|32x32px|link=Lime|Lime]][[File:LimeRotten.png|32x32px|link=Lime|Lime]]</span>
| [[Lime]]
| 0.2
| -10
| -50
| -5
| -
| 7
| 9
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Lime
|-
| <span class="cycle-img">[[File:Mango.png|32x32px|link=Mango|Mango]][[File:MangoRotten.png|32x32px|link=Mango|Mango]]</span>
| [[Mango]]
| 0.3
| -20
| -67
| -13
| -
| 6
| 14
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Mango
|-
| <span class="cycle-img">[[File:Orange.png|32x32px|link=Orange|Orange]][[File:OrangeRotten.png|32x32px|link=Orange|Orange]]</span>
| [[Orange]]
| 0.2
| -12
| -60
| -8
| -
| 6
| 9
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Orange
|-
| <span class="cycle-img">[[File:Peach.png|32x32px|link=Peach|Peach]][[File:PeachRotten.png|32x32px|link=Peach|Peach]]</span>
| [[Peach]]
| 0.2
| -12
| -60
| -5
| -
| 5
| 8
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Peach
|-
| <span class="cycle-img">[[File:Pear.png|32x32px|link=Pear|Pear]][[File:PearRotten.png|32x32px|link=Pear|Pear]]</span>
| [[Pear]]
| 0.2
| -16
| -80
| -7
| -
| 5
| 8
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Pear
|-
| <span class="cycle-img">[[File:Pineapple.png|32x32px|link=Pineapple|Pineapple]][[File:PineappleRotten.png|32x32px|link=Pineapple|Pineapple]]</span>
| [[Pineapple]]
| 0.3
| -24
| -80
| -13
| -
| 6
| 14
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Pineapple
|-
| [[File:Rosehips.png|32x32px|link=Rose Hips|Rose Hips]]
| [[Rose Hips]]
| 0.1
| -6
| -60
| -
| -
| 6
| 10
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Rosehips
|-
| <span class="cycle-img">[[File:BerryStraw.png|32x32px|link=Strawberries|Strawberries]][[File:BerryStrawRotten.png|32x32px|link=Strawberries|Strawberries]]</span>
| [[Strawberries]]
| 0.1
| -5
| -50
| -1
| -10
| 2
| 5
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Strewberrie
|-
| <span class="cycle-img">[[File:Watermelon.png|32x32px|link=Watermelon|Watermelon]][[File:WatermelonRotten.png|32x32px|link=Watermelon|Watermelon]]</span>
| [[Watermelon]]
| 3
| -60
| -20
| -140
| -
| 6
| 8
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Watermelon
|-
| [[File:WatermelonSmashed.png|32x32px|link=Watermelon Chunks|Watermelon Chunks]]
| [[Watermelon Chunks]]
| 0.6
| -12
| -20
| -25
| -
| 2
| 3
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.WatermelonSmashed
|-
| [[File:WatermelonSliced.png|32x32px|link=Watermelon Slice|Watermelon Slice]]
| [[Watermelon Slice]]
| 0.3
| -6
| -20
| -20
| -
| 3
| 4
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.WatermelonSliced
|}
</div><!-- Bot_flag_end|type=food_item_list|id=fruit -->

=== Vegetables ===
<!-- Bot_flag|type=food_item_list|id=vegetable --><div class="scroll-x">
{| class="wikitable theme-red sortable sticky-column" style="text-align: center;"
! Icon
! Name
! [[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Hunger_32.png|link=|Hunger]]
! [[File:Status_Hunger_32.png|link=|Hunger]]/[[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Thirst_32.png|link=|Thirst]]
! [[File:Mood_Sad_32.png|link=|Unhappiness]]
! [[File:UI_Fresh_Time.png|32px|link=|Fresh (days)]]
! [[File:UI_Rotten_Time.png|32px|link=|Rotten (days)]]
! [[File:UI_Cook_Time.png|32px|link=|Cooked (mins)]]
! [[File:UI_Burn_Time.png|32px|link=|Burned (mins)]]
! [[File:Pepper.png|24px|link=|Spice]]
! Item ID
|-
| <span class="cycle-img">[[File:Avocado.png|32x32px|link=Avocado|Avocado]][[File:AvocadoRotten.png|32x32px|link=Avocado|Avocado]]</span>
| [[Avocado]]
| 0.3
| -16
| -53
| -7
| -
| 6
| 14
| 20
| 40
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Avocado
|-
| <span class="cycle-img">[[File:BellPepper.png|32x32px|link=Bell Pepper|Bell Pepper]][[File:BellPepperRotten.png|32x32px|link=Bell Pepper|Bell Pepper]]</span>
| [[Bell Pepper]]
| 0.2
| -8
| -40
| -2
| -
| 5
| 8
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BellPepper
|-
| [[File:Blackbeans.png|32x32px|link=Black Beans|Black Beans]]
| [[Black Beans]]
| 0.1
| -10
| -100
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Blackbeans
|-
| [[File:DriedBlackBeans.png|32x32px|link=Black Beans (Dried)|Black Beans (Dried)]]
| [[Black Beans (Dried)]]
| 2
| -60
| -30
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DriedBlackBeans
|-
| [[File:BowlFull.png|32x32px|link=Bowl of Beans|Bowl of Beans]]
| [[Bowl of Beans]]
| 1.5
| -24
| -16
| -
| 10
| 2
| 4
| 20
| 40
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BeanBowl
|-
| <span class="cycle-img">[[File:Broccoli.png|32x32px|link=Broccoli|Broccoli]][[File:BroccoliRotten.png|32x32px|link=Broccoli|Broccoli]]</span>
| [[Broccoli]]
| 0.2
| -9
| -45
| -4
| -
| 4
| 6
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Broccoli
|-
| <span class="cycle-img">[[File:BrusselSprouts.png|32x32px|link=Brussels Sprouts|Brussels Sprouts]][[File:BrusselSproutsRotten.png|32x32px|link=Brussels Sprouts|Brussels Sprouts]]</span>
| [[Brussels Sprouts]]
| 0.6
| -20
| -33
| -5
| 10*
| 3
| 5
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BrusselSprouts
|-
| <span class="cycle-img">[[File:Cabbage.png|32x32px|link=Cabbage|Cabbage]][[File:CabbageRotten.png|32x32px|link=Cabbage|Cabbage]]</span>
| [[Cabbage]]
| 0.2
| -24
| -120
| -10
| -
| 2
| 4
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Cabbage
|-
| [[File:Capers.png|32x32px|link=Capers|Capers]]
| [[Capers]]
| 0.1
| -5
| -50
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Capers
|-
| <span class="cycle-img">[[File:Carrots.png|32x32px|link=Carrots|Carrots]][[File:CarrotsRotten.png|32x32px|link=Carrots|Carrots]]</span>
| [[Carrots]]
| 0.2
| -8
| -40
| -4
| -
| 6
| 8
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Carrots
|-
| <span class="cycle-img">[[File:Cauliflower.png|32x32px|link=Cauliflower|Cauliflower]][[File:CauliflowerRotten.png|32x32px|link=Cauliflower|Cauliflower]]</span>
| [[Cauliflower]]
| 0.2
| -9
| -45
| -4
| -
| 4
| 6
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Cauliflower
|-
| [[File:DriedChickpeas.png|32x32px|link=Chick Peas (Dried)|Chick Peas (Dried)]]
| [[Chick Peas (Dried)]]
| 2
| -60
| -30
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DriedChickpeas
|-
| <span class="cycle-img">[[File:Corn.png|32x32px|link=Corn|Corn]][[File:CornRotten.png|32x32px|link=Corn|Corn]]</span>
| [[Corn]]
| 0.2
| -14
| -70
| -4
| 5
| 5
| 8
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Corn
|-
| [[File:DriedCorn.png|32x32px|link=Corn (Dried)|Corn (Dried)]]
| [[Corn (Dried)]]
| 0.02
| -4
| -200
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CornSeed
|-
| <span class="cycle-img">[[File:Cucumber.png|32x32px|link=Cucumber|Cucumber]][[File:CucumberRotten.png|32x32px|link=Cucumber|Cucumber]]</span>
| [[Cucumber]]
| 0.3
| -10
| -33
| -10
| -
| 6
| 14
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Cucumber
|-
| <span class="cycle-img">[[File:Daikon.png|32x32px|link=Daikon|Daikon]][[File:DaikonRotten.png|32x32px|link=Daikon|Daikon]]</span>
| [[Daikon]]
| 0.2
| -12
| -60
| -5
| -
| 5
| 8
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Daikon
|-
| [[File:Dandelions.png|32x32px|link=Dandelions|Dandelions]]
| [[Dandelions]]
| 0.1
| -5
| -50
| -
| -
| 6
| 10
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Dandelions
|-
| [[File:Edamame.png|32x32px|link=Edamame|Edamame]]
| [[Edamame]]
| 0.1
| -5
| -50
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Edamame
|-
| <span class="cycle-img">[[File:Eggplant.png|32x32px|link=Eggplant|Eggplant]][[File:EggplantRotten.png|32x32px|link=Eggplant|Eggplant]]</span>
| [[Eggplant]]
| 0.2
| -16
| -80
| -9
| 10*
| 5
| 8
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Eggplant
|-
| [[File:OnionRings.png|32x32px|link=Fried Onion Rings|Fried Onion Rings]]
| [[Fried Onion Rings]]
| 0.1
| -10
| -100
| -
| -
| 4
| 7
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.FriedOnionRings
|-
| [[File:OnionRings.png|32x32px|link=Fried Onion Rings|Fried Onion Rings]]
| [[Fried Onion Rings]]
| 0.1
| -10
| -100
| -
| -
| 4
| 7
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.FriedOnionRingsCraft
|-
| [[File:FrenchFries.png|32x32px|link=Fries|Fries]]
| [[Fries]]
| 0.2
| -10
| -50
| -
| -10
| 3
| 5
| 20
| 40
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.FrenchFries
|-
| [[File:GrapeLeaves.png|32x32px|link=Grape Leaves|Grape Leaves]]
| [[Grape Leaves]]
| 0.1
| -4
| -40
| -
| -
| 6
| 10
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.GrapeLeaves
|-
| <span class="cycle-img">[[File:Greenpeas.png|32x32px|link=Green Peas|Green Peas]][[File:GreenpeasRotten.png|32x32px|link=Green Peas|Green Peas]]</span>
| [[Green Peas]]
| 0.2
| -4
| -20
| -1
| -
| 3
| 5
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Greenpeas
|-
| [[File:DriedPeas.png|32x32px|link=Green Peas (Dried)|Green Peas (Dried)]]
| [[Green Peas (Dried)]]
| 0.02
| -1
| -50
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.GreenpeasSeed
|-
| [[File:PepperHabanero.png|32x32px|link=Habanero|Habanero]]
| [[Habanero]]
| 0.1
| -2
| -20
| -
| -
| 5
| 8
| 10
| 30
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.PepperHabanero
|-
| [[File:PepperHabanero_Dried.png|32x32px|link=Habanero (Dried)|Habanero (Dried)]]
| [[Habanero (Dried)]]
| 0.1
| -1
| -10
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.PepperHabaneroDried
|-
| [[File:PepperJalapeno.png|32x32px|link=Jalapeno|Jalapeno]]
| [[Jalapeno]]
| 0.1
| -2
| -20
| -
| -
| 5
| 8
| 10
| 30
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.PepperJalapeno
|-
| [[File:PepperJalapeno_Dried.png|32x32px|link=Jalapeno (Dried)|Jalapeno (Dried)]]
| [[Jalapeno (Dried)]]
| 0.1
| -1
| -10
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.PepperJalapenoDried
|-
| <span class="cycle-img">[[File:Kale.png|32x32px|link=Kale|Kale]][[File:KaleRotten.png|32x32px|link=Kale|Kale]]</span>
| [[Kale]]
| 0.2
| -16
| -80
| -10
| -
| 3
| 5
| 5
| 20
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Kale
|-
| [[File:DriedKidneyBeans.png|32x32px|link=Kidney Beans (Dried)|Kidney Beans (Dried)]]
| [[Kidney Beans (Dried)]]
| 2
| -60
| -30
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DriedKidneyBeans
|-
| <span class="cycle-img">[[File:Leek.png|32x32px|link=Leek|Leek]][[File:LeekRotten.png|32x32px|link=Leek|Leek]]</span>
| [[Leek]]
| 0.2
| -12
| -60
| -5
| 5*
| 5
| 8
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Leek
|-
| [[File:DriedLentils.png|32x32px|link=Lentils (Dried)|Lentils (Dried)]]
| [[Lentils (Dried)]]
| 2
| -60
| -30
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DriedLentils
|-
| <span class="cycle-img">[[File:Lettuce.png|32x32px|link=Lettuce|Lettuce]][[File:LettuceRotten.png|32x32px|link=Lettuce|Lettuce]]</span>
| [[Lettuce]]
| 0.2
| -15
| -75
| -7
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Lettuce
|-
| [[File:MushroomGeneric1.png|32x32px|link=Mushrooms|Mushrooms]]
| [[Mushrooms]]
| 0.2
| -13
| -65
| -1
| -
| 3
| 4
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.MushroomGeneric1
|-
| [[File:MushroomGeneric2.png|32x32px|link=Mushrooms|Mushrooms]]
| [[Mushrooms]]
| 0.2
| -13
| -65
| -1
| -
| 3
| 4
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.MushroomGeneric2
|-
| [[File:MushroomGeneric3.png|32x32px|link=Mushrooms|Mushrooms]]
| [[Mushrooms]]
| 0.2
| -15
| -75
| -1
| -
| 3
| 4
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.MushroomGeneric3
|-
| [[File:MushroomGeneric4.png|32x32px|link=Mushrooms|Mushrooms]]
| [[Mushrooms]]
| 0.2
| -13
| -65
| -1
| -
| 3
| 4
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.MushroomGeneric4
|-
| [[File:MushroomGeneric5.png|32x32px|link=Mushrooms|Mushrooms]]
| [[Mushrooms]]
| 0.2
| -15
| -75
| -1
| -
| 3
| 4
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.MushroomGeneric5
|-
| [[File:MushroomGeneric6.png|32x32px|link=Mushrooms|Mushrooms]]
| [[Mushrooms]]
| 0.2
| -13
| -65
| -1
| -
| 3
| 4
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.MushroomGeneric6
|-
| [[File:MushroomGeneric7.png|32x32px|link=Mushrooms|Mushrooms]]
| [[Mushrooms]]
| 0.2
| -13
| -65
| -1
| -
| 3
| 4
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.MushroomGeneric7
|-
| [[File:MushroomButton.png|32x32px|link=Mushrooms|Mushrooms]]
| [[Mushrooms]]
| 0.2
| -7
| -35
| -
| -
| 3
| 4
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.MushroomsButton
|-
| [[File:Olives.png|32x32px|link=Olives|Olives]]
| [[Olives]]
| 0.1
| -5
| -50
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Olives
|-
| <span class="cycle-img">[[File:Onion.png|32x32px|link=Onion|Onion]][[File:OnionRotten.png|32x32px|link=Onion|Onion]]</span>
| [[Onion]]
| 0.2
| -10
| -50
| -
| -
| 14
| 28
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Onion
|-
| [[File:Frozen_Corn.png|32x32px|link=Packaged Corn|Packaged Corn]]
| [[Packaged Corn]]
| 0.6
| -20
| -33
| -5
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CornFrozen
|-
| [[File:Peas.png|32x32px|link=Packaged Peas|Packaged Peas]]
| [[Packaged Peas]]
| 0.6
| -20
| -33
| -5
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Peas
|-
| [[File:Frozen_MixedVegetables.png|32x32px|link=Packaged Vegetables|Packaged Vegetables]]
| [[Packaged Vegetables]]
| 0.6
| -20
| -33
| -5
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.MixedVegetables
|-
| [[File:Peanut.png|32x32px|link=Peanuts|Peanuts]]
| [[Peanuts]]
| 0.2
| -8
| -40
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Peanuts
|-
| <span class="cycle-img">[[File:Potato.png|32x32px|link=Potato|Potato]][[File:PotatoRotten.png|32x32px|link=Potato|Potato]]</span>
| [[Potato]]
| 0.2
| -18
| -90
| -7
| 5*
| 28
| 280
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Potato
|-
| <span class="cycle-img">[[File:Pumpkin.png|32x32px|link=Pumpkin|Pumpkin]][[File:PumpkinRotten.png|32x32px|link=Pumpkin|Pumpkin]]</span>
| [[Pumpkin]]
| 1
| -40
| -40
| -
| 10*
| 14
| 28
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Pumpkin
|-
| <span class="cycle-img">[[File:Pumpkin_Smashed.png|32x32px|link=Pumpkin Chunks|Pumpkin Chunks]][[File:Pumpkin_SmashedRotten.png|32x32px|link=Pumpkin Chunks|Pumpkin Chunks]]</span>
| [[Pumpkin Chunks]]
| 0.2
| -8
| -40
| -
| 2*
| 14
| 28
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PumpkinSmashed
|-
| <span class="cycle-img">[[File:Pumpkin_Slice.png|32x32px|link=Pumpkin Slice|Pumpkin Slice]][[File:Pumpkin_SliceRotten.png|32x32px|link=Pumpkin Slice|Pumpkin Slice]]</span>
| [[Pumpkin Slice]]
| 0.1
| -4
| -40
| -
| -
| 14
| 28
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PumpkinSliced
|-
| <span class="cycle-img">[[File:Radish.png|32x32px|link=Radish|Radish]][[File:RadishRotten.png|32x32px|link=Radish|Radish]]</span>
| [[Radish]]
| 0.1
| -3
| -30
| -1
| -
| 3
| 7
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.RedRadish
|-
| [[File:RefriedBeans.png|32x32px|link=Refried Beans|Refried Beans]]
| [[Refried Beans]]
| 0.2
| -10
| -50
| -
| -
| 4
| 8
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.RefriedBeans
|-
| <span class="cycle-img">[[File:Soybeans.png|32x32px|link=Soybeans|Soybeans]][[File:SoybeansRotten.png|32x32px|link=Soybeans|Soybeans]]</span>
| [[Soybeans]]
| 0.1
| -5
| -50
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Soybeans
|-
| [[File:DriedSoyBeans.png|32x32px|link=Soybeans (Dried)|Soybeans (Dried)]]
| [[Soybeans (Dried)]]
| 0.02
| -1
| -50
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SoybeansSeed
|-
| <span class="cycle-img">[[File:Spinach.png|32x32px|link=Spinach|Spinach]][[File:SpinachRotten.png|32x32px|link=Spinach|Spinach]]</span>
| [[Spinach]]
| 0.1
| -5
| -50
| -
| -
| 4
| 6
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Spinach
|-
| [[File:DriedSplitPeas.png|32x32px|link=Split Peas (Dried)|Split Peas (Dried)]]
| [[Split Peas (Dried)]]
| 2
| -60
| -30
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DriedSplitPeas
|-
| <span class="cycle-img">[[File:Squash.png|32x32px|link=Squash|Squash]][[File:SquashRotten.png|32x32px|link=Squash|Squash]]</span>
| [[Squash]]
| 0.5
| -20
| -40
| -
| 10*
| 14
| 28
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Squash
|-
| <span class="cycle-img">[[File:SugarBeets.png|32x32px|link=Sugar Beet|Sugar Beet]][[File:SugarBeetsRotten.png|32x32px|link=Sugar Beet|Sugar Beet]]</span>
| [[Sugar Beet]]
| 0.2
| -9
| -45
| -4
| 10
| 4
| 6
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SugarBeet
|-
| <span class="cycle-img">[[File:SweetPotato.png|32x32px|link=Sweet Potato|Sweet Potato]][[File:SweetPotatoRotten.png|32x32px|link=Sweet Potato|Sweet Potato]]</span>
| [[Sweet Potato]]
| 0.2
| -18
| -90
| -7
| 10*
| 28
| 280
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SweetPotato
|-
| [[File:TatoDots.png|32x32px|link=Tato Dots|Tato Dots]]
| [[Tato Dots]]
| 0.2
| -10
| -50
| -
| -10
| 3
| 5
| 20
| 40
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.TatoDots
|-
| <span class="cycle-img">[[File:Tofu.png|32x32px|link=Tofu|Tofu]][[File:TofuRotten.png|32x32px|link=Tofu|Tofu]]</span>
| [[Tofu]]
| 0.3
| -10
| -33
| -
| -
| 6
| 14
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Tofu
|-
| [[File:TofuFried.png|32x32px|link=Tofu (Fried)|Tofu (Fried)]]
| [[Tofu (Fried)]]
| 0.3
| -15
| -50
| -
| -
| 6
| 14
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.TofuFried
|-
| <span class="cycle-img">[[File:Tomato.png|32x32px|link=Tomato|Tomato]][[File:TomatoRotten.png|32x32px|link=Tomato|Tomato]]</span>
| [[Tomato]]
| 0.2
| -12
| -60
| -8
| -
| 4
| 12
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Tomato
|-
| <span class="cycle-img">[[File:Turnip.png|32x32px|link=Turnip|Turnip]][[File:TurnipRotten.png|32x32px|link=Turnip|Turnip]]</span>
| [[Turnip]]
| 0.2
| -18
| -90
| -7
| -
| 28
| 280
| 30
| 60
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Turnip
|-
| [[File:DriedWhiteBeans.png|32x32px|link=White Beans (Dried)|White Beans (Dried)]]
| [[White Beans (Dried)]]
| 2
| -60
| -30
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DriedWhiteBeans
|-
| <span class="cycle-img">[[File:Zucchini.png|32x32px|link=Zucchini|Zucchini]][[File:ZucchiniRotten.png|32x32px|link=Zucchini|Zucchini]]</span>
| [[Zucchini]]
| 0.3
| -10
| -33
| -10
| -
| 6
| 14
| 20
| 40
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Zucchini
|}
</div><!-- Bot_flag_end|type=food_item_list|id=vegetable -->

=== Pickled food ===
<!-- Bot_flag|type=food_item_list|id=pickled --><div class="scroll-x">
{| class="wikitable theme-red sortable sticky-column" style="text-align: center;"
! Icon
! Name
! [[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Hunger_32.png|link=|Hunger]]
! [[File:Status_Hunger_32.png|link=|Hunger]]/[[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Mood_Sad_32.png|link=|Unhappiness]]
! [[File:UI_Fresh_Time.png|32px|link=|Fresh (days)]]
! [[File:UI_Rotten_Time.png|32px|link=|Rotten (days)]]
! [[File:UI_Cook_Time.png|32px|link=|Cooked (mins)]]
! [[File:UI_Burn_Time.png|32px|link=|Burned (mins)]]
! [[File:Pepper.png|24px|link=|Spice]]
! Item ID
|-
| [[File:JarBrown.png|32x32px|link=Jar of Bell Peppers|Jar of Bell Peppers]]
| [[Jar of Bell Peppers]]
| 0.8
| -48
| -60
| -
| 30
| 60
| 60
| 120
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedBellPepper
|-
| [[File:JarBrown.png|32x32px|link=Jar of Bell Peppers (Open)|Jar of Bell Peppers (Open)]]
| [[Jar of Bell Peppers (Open)]]
| 0.8
| -48
| -60
| -
| 2
| 4
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedBellPepper_Open
|-
| [[File:JarGreen.png|32x32px|link=Jar of Broccoli|Jar of Broccoli]]
| [[Jar of Broccoli]]
| 0.8
| -45
| -56
| -
| 30
| 60
| 60
| 120
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedBroccoli
|-
| [[File:JarGreen.png|32x32px|link=Jar of Broccoli (Open)|Jar of Broccoli (Open)]]
| [[Jar of Broccoli (Open)]]
| 0.8
| -45
| -56
| -
| 2
| 4
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedBroccoli_Open
|-
| [[File:JarGreen.png|32x32px|link=Jar of Cabbage|Jar of Cabbage]]
| [[Jar of Cabbage]]
| 0.8
| -48
| -60
| -
| 30
| 60
| 60
| 120
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedCabbage
|-
| [[File:JarGreen.png|32x32px|link=Jar of Cabbage (Open)|Jar of Cabbage (Open)]]
| [[Jar of Cabbage (Open)]]
| 0.8
| -48
| -60
| -
| 2
| 4
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedCabbage_Open
|-
| [[File:JarBrown.png|32x32px|link=Jar of Carrots|Jar of Carrots]]
| [[Jar of Carrots]]
| 0.8
| -40
| -50
| -
| 30
| 60
| 60
| 120
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedCarrots
|-
| [[File:JarBrown.png|32x32px|link=Jar of Carrots (Open)|Jar of Carrots (Open)]]
| [[Jar of Carrots (Open)]]
| 0.8
| -40
| -50
| -
| 2
| 4
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedCarrots_Open
|-
| [[File:JamPurple.png|32x32px|link=Jar of Eggplants|Jar of Eggplants]]
| [[Jar of Eggplants]]
| 0.8
| -48
| -60
| -
| 30
| 60
| 60
| 120
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedEggplant
|-
| [[File:JamPurple.png|32x32px|link=Jar of Eggplants (Open)|Jar of Eggplants (Open)]]
| [[Jar of Eggplants (Open)]]
| 0.8
| -48
| -60
| -
| 2
| 4
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedEggplant_Open
|-
| [[File:Jar_Roe.png|32x32px|link=Jar of Fish Roe|Jar of Fish Roe]]
| [[Jar of Fish Roe]]
| 0.8
| -48
| -60
| -
| 30
| 60
| 60
| 120
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedRoe
|-
| [[File:JarWhite.png|32x32px|link=Jar of Leeks|Jar of Leeks]]
| [[Jar of Leeks]]
| 0.8
| -48
| -60
| -
| 30
| 60
| 60
| 120
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedLeek
|-
| [[File:JarWhite.png|32x32px|link=Jar of Leeks (Open)|Jar of Leeks (Open)]]
| [[Jar of Leeks (Open)]]
| 0.8
| -48
| -60
| -
| 2
| 4
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedLeek_Open
|-
| [[File:JarWhite.png|32x32px|link=Jar of Potatoes|Jar of Potatoes]]
| [[Jar of Potatoes]]
| 0.8
| -48
| -60
| -
| 30
| 60
| 60
| 120
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedPotato
|-
| [[File:JarWhite.png|32x32px|link=Jar of Potatoes (Open)|Jar of Potatoes (Open)]]
| [[Jar of Potatoes (Open)]]
| 0.8
| -48
| -60
| -
| 2
| 4
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedPotato_Open
|-
| [[File:JarBrown.png|32x32px|link=Jar of Radishes|Jar of Radishes]]
| [[Jar of Radishes]]
| 0.8
| -45
| -56
| -
| 30
| 60
| 60
| 120
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedRedRadish
|-
| [[File:JarBrown.png|32x32px|link=Jar of Radishes (Open)|Jar of Radishes (Open)]]
| [[Jar of Radishes (Open)]]
| 0.8
| -45
| -56
| -
| 2
| 4
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedRedRadish_Open
|-
| [[File:JarBrown.png|32x32px|link=Jar of Tomatoes|Jar of Tomatoes]]
| [[Jar of Tomatoes]]
| 0.8
| -48
| -60
| -
| 30
| 60
| 60
| 120
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedTomato
|-
| [[File:JarBrown.png|32x32px|link=Jar of Tomatoes (Open)|Jar of Tomatoes (Open)]]
| [[Jar of Tomatoes (Open)]]
| 0.8
| -48
| -60
| -
| 2
| 4
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedTomato_Open
|-
| [[File:Jar_Roe.png|32x32px|link=Opened Jar of Fish Roe|Opened Jar of Fish Roe]]
| [[Opened Jar of Fish Roe]]
| 0.8
| -10
| -12
| -20
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CannedRoe_Open
|}
</div><!-- Bot_flag_end|type=food_item_list|id=pickled -->

=== Herbs ===
<!-- Bot_flag|type=food_item_list|id=herb --><div class="scroll-x">
{| class="wikitable theme-red sortable sticky-column" style="text-align: center;"
! Icon
! Name
! [[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Hunger_32.png|link=|Hunger]]
! [[File:Status_Hunger_32.png|link=|Hunger]]/[[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Mood_Sad_32.png|link=|Unhappiness]]
! [[File:Mood_Stressed_32.png|link=|Stress]]
! [[File:UI_Fresh_Time.png|32px|link=|Fresh (days)]]
! [[File:UI_Rotten_Time.png|32px|link=|Rotten (days)]]
! [[File:UI_Cook_Time.png|32px|link=|Cooked (mins)]]
! [[File:UI_Burn_Time.png|32px|link=|Burned (mins)]]
! [[File:Pepper.png|24px|link=|Spice]]
! Item ID
|-
| [[File:HerbBasil.png|32x32px|link=Basil|Basil]]
| [[Basil]]
| 0.1
| -1
| -10
| -
| -
| 6
| 10
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Basil
|-
| [[File:Seasoning_Basil.png|32x32px|link=Basil (Dried)|Basil (Dried)]]
| [[Basil (Dried)]]
| 0.2
| -20
| -100
| 10
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Seasoning_Basil
|-
| [[File:DriedHerbs_generic.png|32x32px|link=Basil (Dried)|Basil (Dried)]]
| [[Basil (Dried)]]
| 0.1
| -5
| -50
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.BasilDried
|-
| <span class="cycle-img">[[File:BlackSage.png|32x32px|link=Black Sage|Black Sage]][[File:BlackSageRotten.png|32x32px|link=Black Sage|Black Sage]]</span>
| [[Black Sage]]
| 0.1
| -1
| -10
| -
| -
| 6
| 10
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.BlackSage
|-
| [[File:BlackSage_Dried.png|32x32px|link=Black Sage (Dried)|Black Sage (Dried)]]
| [[Black Sage (Dried)]]
| 0.1
| -1
| -10
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.BlackSageDried
|-
| <span class="cycle-img">[[File:Chamomile.png|32x32px|link=Chamomile|Chamomile]][[File:ChamomileRotten.png|32x32px|link=Chamomile|Chamomile]]</span>
| [[Chamomile]]
| 0.1
| -1
| -10
| -
| -1
| 6
| 10
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Chamomile
|-
| [[File:Chamomile_Dried.png|32x32px|link=Chamomile (Dried)|Chamomile (Dried)]]
| [[Chamomile (Dried)]]
| 0.1
| -5
| -50
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.ChamomileDried
|-
| [[File:HerbChives.png|32x32px|link=Chives|Chives]]
| [[Chives]]
| 0.1
| -1
| -10
| -
| -
| 6
| 10
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Chives
|-
| [[File:Seasoning_Chives.png|32x32px|link=Chives (Dried) (seasoning)|Chives (Dried)]]
| [[Chives (Dried) (seasoning)|Chives (Dried)]]
| 0.2
| -20
| -100
| 10
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Seasoning_Chives
|-
| [[File:DriedHerbs_generic.png|32x32px|link=Chives (Dried)|Chives (Dried)]]
| [[Chives (Dried)]]
| 0.1
| -5
| -50
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.ChivesDried
|-
| [[File:HerbCilantro.png|32x32px|link=Cilantro|Cilantro]]
| [[Cilantro]]
| 0.1
| -1
| -10
| -
| -
| 6
| 10
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Cilantro
|-
| [[File:Seasoning_Cilantro.png|32x32px|link=Cilantro (Dried)|Cilantro (Dried)]]
| [[Cilantro (Dried)]]
| 0.2
| -20
| -100
| 10
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Seasoning_Cilantro
|-
| [[File:DriedHerbs_generic.png|32x32px|link=Cilantro (Dried)|Cilantro (Dried)]]
| [[Cilantro (Dried)]]
| 0.1
| -5
| -50
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.CilantroDried
|-
| [[File:Seeds_Generic.png|32x32px|link=Cilantro Seeds|Cilantro Seeds]]
| [[Cilantro Seeds]]
| 0.02
| -1
| -50
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.CilantroSeed
|-
| [[File:Cinnamon.png|32x32px|link=Cinnamon|Cinnamon]]
| [[Cinnamon]]
| 0.1
| -5
| -50
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Cinnamon
|-
| <span class="cycle-img">[[File:CommonMallow.png|32x32px|link=Common Mallow|Common Mallow]][[File:CommonMallowRotten.png|32x32px|link=Common Mallow|Common Mallow]]</span>
| [[Common Mallow]]
| 0.1
| -1
| -10
| -
| -
| 6
| 10
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.CommonMallow
|-
| [[File:CommonMallow_Dried.png|32x32px|link=Common Mallow (Dried)|Common Mallow (Dried)]]
| [[Common Mallow (Dried)]]
| 0.1
| -1
| -10
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.CommonMallowDried
|-
| [[File:FourLeafClover.png|32x32px|link=Four Leaf Clover|Four Leaf Clover]]
| [[Four Leaf Clover]]
| 0.1
| -1
| -10
| -
| -
| 6
| 10
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.FourLeafClover
|-
| [[File:Garlic.png|32x32px|link=Garlic|Garlic]]
| [[Garlic]]
| 0.2
| -5
| -25
| -
| -
| 14
| 28
| 30
| 60
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Garlic
|-
| [[File:HerbChives.png|32x32px|link=Green Onions|Green Onions]]
| [[Green Onions]]
| 0.2
| -3
| -15
| -
| -
| 7
| 14
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.GreenOnions
|-
| [[File:Bouquet_Lavender.png|32x32px|link=Lavender|Lavender]]
| [[Lavender]]
| 0.1
| -1
| -10
| -
| -1
| 6
| 10
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Lavender
|-
| [[File:Petals_Lavender.png|32x32px|link=Lavender Petals (Dried)|Lavender Petals (Dried)]]
| [[Lavender Petals (Dried)]]
| 0.1
| -1
| -10
| -
| -1
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.LavenderPetalsDried
|-
| [[File:LemonGrass.png|32x32px|link=Lemongrass|Lemongrass]]
| [[Lemongrass]]
| 0.1
| -1
| -10
| -
| -
| 6
| 10
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.LemonGrass
|-
| <span class="cycle-img">[[File:Marigold.png|32x32px|link=Marigold|Marigold]][[File:MarigoldRotten.png|32x32px|link=Marigold|Marigold]]</span>
| [[Marigold]]
| 0.1
| -1
| -10
| -
| -
| 6
| 10
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Marigold
|-
| [[File:Marigold_Dried.png|32x32px|link=Marigold (Dried)|Marigold (Dried)]]
| [[Marigold (Dried)]]
| 0.1
| -1
| -10
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.MarigoldDried
|-
| <span class="cycle-img">[[File:Mint.png|32x32px|link=Mint|Mint]][[File:MintRotten.png|32x32px|link=Mint|Mint]]</span>
| [[Mint]]
| 0.1
| -1
| -10
| -
| -1
| 6
| 10
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.MintHerb
|-
| [[File:Mint.png|32x32px|link=Mint (Dried)|Mint (Dried)]]
| [[Mint (Dried)]]
| 0.1
| -1
| -10
| -
| -1
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.MintHerbDried
|-
| [[File:Nettle.png|32x32px|link=Nettles|Nettles]]
| [[Nettles]]
| 0.1
| -4
| -40
| -
| -
| 6
| 10
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Nettles
|-
| [[File:HerbOregano.png|32x32px|link=Oregano|Oregano]]
| [[Oregano]]
| 0.1
| -1
| -10
| -
| -
| 6
| 10
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Oregano
|-
| [[File:Seasoning_Oregano.png|32x32px|link=Oregano (Dried)|Oregano (Dried)]]
| [[Oregano (Dried)]]
| 0.2
| -20
| -100
| 10
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Seasoning_Oregano
|-
| [[File:DriedHerbs_generic.png|32x32px|link=Oregano (Dried)|Oregano (Dried)]]
| [[Oregano (Dried)]]
| 0.1
| -5
| -50
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.OreganoDried
|-
| [[File:HerbParsley.png|32x32px|link=Parsley|Parsley]]
| [[Parsley]]
| 0.1
| -1
| -10
| -
| -
| 6
| 10
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Parsley
|-
| [[File:Seasoning_Parsley.png|32x32px|link=Parsley (Dried)|Parsley (Dried)]]
| [[Parsley (Dried)]]
| 0.2
| -20
| -100
| 10
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Seasoning_Parsley
|-
| [[File:DriedHerbs_generic.png|32x32px|link=Parsley (Dried)|Parsley (Dried)]]
| [[Parsley (Dried)]]
| 0.1
| -5
| -50
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.ParsleyDried
|-
| [[File:Petals_Rose.png|32x32px|link=Rose Petals (Dried)|Rose Petals (Dried)]]
| [[Rose Petals (Dried)]]
| 0.1
| -1
| -10
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.RosePetalsDried
|-
| [[File:HerbRosemary.png|32x32px|link=Rosemary|Rosemary]]
| [[Rosemary]]
| 0.1
| -1
| -10
| -
| -
| 14
| 28
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Rosemary
|-
| [[File:Seasoning_Rosemary.png|32x32px|link=Rosemary (Dried)|Rosemary (Dried)]]
| [[Rosemary (Dried)]]
| 0.2
| -20
| -100
| 10
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Seasoning_Rosemary
|-
| [[File:DriedHerbs_generic.png|32x32px|link=Rosemary (Dried)|Rosemary (Dried)]]
| [[Rosemary (Dried)]]
| 0.1
| -5
| -50
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.RosemaryDried
|-
| [[File:Bouquet_Rose.png|32x32px|link=Roses|Roses]]
| [[Roses]]
| 0.1
| -1
| -10
| -
| -
| 6
| 10
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Roses
|-
| [[File:HerbSage.png|32x32px|link=Sage|Sage]]
| [[Sage]]
| 0.1
| -1
| -10
| -
| -
| 6
| 10
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Sage
|-
| [[File:Seasoning_Sage.png|32x32px|link=Sage (Dried)|Sage (Dried)]]
| [[Sage (Dried)]]
| 0.2
| -20
| -100
| 10
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Seasoning_Sage
|-
| [[File:DriedHerbs_generic.png|32x32px|link=Sage (Dried)|Sage (Dried)]]
| [[Sage (Dried)]]
| 0.1
| -5
| -50
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.SageDried
|-
| [[File:Thistle.png|32x32px|link=Thistles|Thistles]]
| [[Thistles]]
| 0.1
| -4
| -40
| -
| -
| 6
| 10
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Thistle
|-
| [[File:HerbThyme.png|32x32px|link=Thyme|Thyme]]
| [[Thyme]]
| 0.1
| -1
| -10
| -
| -
| 6
| 10
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Thyme
|-
| [[File:Seasoning_Thyme.png|32x32px|link=Thyme (Dried)|Thyme (Dried)]]
| [[Thyme (Dried)]]
| 0.2
| -20
| -100
| 10
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Seasoning_Thyme
|-
| [[File:DriedHerbs_generic.png|32x32px|link=Thyme (Dried)|Thyme (Dried)]]
| [[Thyme (Dried)]]
| 0.1
| -5
| -50
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.ThymeDried
|-
| [[File:WildGarlic.png|32x32px|link=Wild Garlic|Wild Garlic]]
| [[Wild Garlic]]
| 0.1
| -1
| -10
| -
| -
| 6
| 10
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.WildGarlic2
|-
| [[File:WildGarlic.png|32x32px|link=Wild Garlic (Dried)|Wild Garlic (Dried)]]
| [[Wild Garlic (Dried)]]
| 0.1
| -1
| -10
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.WildGarlicDried
|}
</div><!-- Bot_flag_end|type=food_item_list|id=herb -->

=== Plants ===
<!-- Bot_flag|type=food_item_list|id=plant --><div class="scroll-x">
{| class="wikitable theme-red sortable sticky-column" style="text-align: center;"
! Icon
! Name
! [[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Hunger_32.png|link=|Hunger]]
! [[File:Status_Hunger_32.png|link=|Hunger]]/[[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Mood_Sad_32.png|link=|Unhappiness]]
! [[File:UI_Fresh_Time.png|32px|link=|Fresh (days)]]
! [[File:UI_Rotten_Time.png|32px|link=|Rotten (days)]]
! [[File:UI_Cook_Time.png|32px|link=|Cooked (mins)]]
! [[File:UI_Burn_Time.png|32px|link=|Burned (mins)]]
! [[File:Pepper.png|24px|link=|Spice]]
! Item ID
|-
| [[File:Acorn.png|32x32px|link=Acorn|Acorn]]
| [[Acorn]]
| 0.1
| -10
| -100
| 10*
| 180
| 365
| 10
| 30
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Acorn
|-
| <span class="cycle-img">[[File:Barley.png|32x32px|link=Barley Sheaf|Barley Sheaf]][[File:BarleyRotten.png|32x32px|link=Barley Sheaf|Barley Sheaf]]</span>
| [[Barley Sheaf]]
| 1
| -5
| -5
| -
| 7
| 14
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BarleySheaf
|-
| <span class="cycle-img">[[File:Barley.png|32x32px|link=Barley Sheaf (Dried)|Barley Sheaf (Dried)]][[File:BarleyRotten.png|32x32px|link=Barley Sheaf (Dried)|Barley Sheaf (Dried)]]</span>
| [[Barley Sheaf (Dried)]]
| 1
| -5
| -5
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BarleySheafDried
|-
| [[File:Comfrey_Dried.png|32x32px|link=Comfrey (Dried)|Comfrey (Dried)]]
| [[Comfrey (Dried)]]
| 0.1
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.ComfreyDried
|-
| <span class="cycle-img">[[File:Flax_Harvested.png|32x32px|link=Flax|Flax]][[File:Flax_HarvestedRotten.png|32x32px|link=Flax|Flax]][[File:Flax_Harvested_Rotten.png|32x32px|link=Flax|Flax]]</span>
| [[Flax]]
| 0.2
| -
| -
| -
| 7
| 14
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Flax
|-
| [[File:Flax_Rippled.png|32x32px|link=Flax (Rippled)|Flax (Rippled)]]
| [[Flax (Rippled)]]
| 0.2
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.FlaxRippled
|-
| [[File:Grasstuft.png|32x32px|link=Grass Cutting|Grass Cutting]]
| [[Grass Cutting]]
| 0.1
| -7
| -70
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.GrassTuft
|-
| [[File:Haytuft.png|32x32px|link=Hay|Hay]]
| [[Hay]]
| 0.1
| -12
| -120
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.HayTuft
|-
| <span class="cycle-img">[[File:IndustrialHemp.png|32x32px|link=Hemp|Hemp]][[File:IndustrialHempRotten.png|32x32px|link=Hemp|Hemp]]</span>
| [[Hemp]]
| 1
| -5
| -5
| -
| 7
| 14
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.HempBundle
|-
| [[File:IndustrialHemp_Dried.png|32x32px|link=Hemp (Dried)|Hemp (Dried)]]
| [[Hemp (Dried)]]
| 1
| -5
| -5
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.HempBundleDried
|-
| <span class="cycle-img">[[File:Hops.png|32x32px|link=Hops|Hops]][[File:HopsRotten.png|32x32px|link=Hops|Hops]]</span>
| [[Hops]]
| 0.3
| -
| -
| -
| 7
| 14
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Hops
|-
| [[File:Hops_Dried.png|32x32px|link=Hops (Dried)|Hops (Dried)]]
| [[Hops (Dried)]]
| 0.3
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.HopsDried
|-
| [[File:BroadleafPlaintain_Dried.png|32x32px|link=Plantain (Dried)|Plantain (Dried)]]
| [[Plantain (Dried)]]
| 0.1
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PlantainDried
|-
| [[File:Bouquet_Poppy.png|32x32px|link=Poppies|Poppies]]
| [[Poppies]]
| 0.1
| -
| -
| -
| 6
| 10
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Poppies
|-
| [[File:PoppyPods.png|32x32px|link=Poppy Pods|Poppy Pods]]
| [[Poppy Pods]]
| 0.1
| -
| -
| -
| 6
| 10
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PoppyPods
|-
| [[File:PoppyPods.png|32x32px|link=Poppy Pods (Dried)|Poppy Pods (Dried)]]
| [[Poppy Pods (Dried)]]
| 0.1
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PoppyPodsDried
|-
| <span class="cycle-img">[[File:RyeWheat.png|32x32px|link=Rye Sheaf|Rye Sheaf]][[File:RyeWheatRotten.png|32x32px|link=Rye Sheaf|Rye Sheaf]]</span>
| [[Rye Sheaf]]
| 1
| -5
| -5
| -
| 7
| 14
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.RyeSheaf
|-
| <span class="cycle-img">[[File:RyeWheat.png|32x32px|link=Rye Sheaf (Dried)|Rye Sheaf (Dried)]][[File:RyeWheatRotten.png|32x32px|link=Rye Sheaf (Dried)|Rye Sheaf (Dried)]]</span>
| [[Rye Sheaf (Dried)]]
| 1
| -5
| -5
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.RyeSheafDried
|-
| [[File:SunflowerHead.png|32x32px|link=Sunflower Head|Sunflower Head]]
| [[Sunflower Head]]
| 0.2
| -
| -
| -
| 10
| 13
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SunflowerHead
|-
| [[File:SunflowerHead_Dried.png|32x32px|link=Sunflower Head (Dried)|Sunflower Head (Dried)]]
| [[Sunflower Head (Dried)]]
| 0.2
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SunflowerHeadDried
|-
| [[File:Tobacco.png|32x32px|link=Tobacco|Tobacco]]
| [[Tobacco]]
| 0.2
| -
| -
| -
| 7
| 14
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Tobacco
|-
| <span class="cycle-img">[[File:WheatBundle.png|32x32px|link=Wheat Sheaf|Wheat Sheaf]][[File:WheatBundleRotten.png|32x32px|link=Wheat Sheaf|Wheat Sheaf]]</span>
| [[Wheat Sheaf]]
| 1
| -5
| -5
| -
| 7
| 14
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.WheatSheaf
|-
| <span class="cycle-img">[[File:WheatBundle.png|32x32px|link=Wheat Sheaf (Dried)|Wheat Sheaf (Dried)]][[File:WheatBundleRotten.png|32x32px|link=Wheat Sheaf (Dried)|Wheat Sheaf (Dried)]]</span>
| [[Wheat Sheaf (Dried)]]
| 1
| -5
| -5
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.WheatSheafDried
|}
</div><!-- Bot_flag_end|type=food_item_list|id=plant -->

=== Spices ===
<!-- Bot_flag|type=food_item_list|id=spice --><div class="scroll-x">
{| class="wikitable theme-red sortable sticky-column" style="text-align: center;"
! Icon
! Name
! [[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Hunger_32.png|link=|Hunger]]
! [[File:Status_Hunger_32.png|link=|Hunger]]/[[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Thirst_32.png|link=|Thirst]]
! [[File:Mood_Sad_32.png|link=|Unhappiness]]
! [[File:Mood_Bored_32.png|link=|Boredom]]
! [[File:UI_Fresh_Time.png|32px|link=|Fresh (days)]]
! [[File:UI_Rotten_Time.png|32px|link=|Rotten (days)]]
! [[File:UI_Cook_Time.png|32px|link=|Cooked (mins)]]
! [[File:UI_Burn_Time.png|32px|link=|Burned (mins)]]
! [[File:Pepper.png|24px|link=|Spice]]
! Item ID
|-
| [[File:BalsamicVinegar.png|32x32px|link=Balsamic Vinegar|Balsamic Vinegar]]
| [[Balsamic Vinegar]]
| 0.2
| -20
| -100
| -
| 50
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.BalsamicVinegar
|-
| [[File:BBQSauce.png|32x32px|link=Barbecue Sauce|Barbecue Sauce]]
| [[Barbecue Sauce]]
| 0.2
| -20
| -100
| -
| 30
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.BBQSauce
|-
| [[File:BouillionCube.png|32x32px|link=Bouillon Cube|Bouillon Cube]]
| [[Bouillon Cube]]
| 0.1
| -3
| -30
| 5
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.BouillonCube
|-
| [[File:SugarBrown.png|32x32px|link=Brown Sugar|Brown Sugar]]
| [[Brown Sugar]]
| 0.6
| -30
| -50
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.SugarBrown
|-
| [[File:Butter.png|32x32px|link=Butter|Butter]]
| [[Butter]]
| 0.3
| -24
| -80
| -
| 20
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Butter
|-
| [[File:Cornflour.png|32x32px|link=Cornflour|Cornflour]]
| [[Cornflour]]
| 2
| -60
| -30
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Cornflour2
|-
| [[File:Cornmeal.png|32x32px|link=Cornmeal|Cornmeal]]
| [[Cornmeal]]
| 2
| -20
| -10
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Cornmeal2
|-
| [[File:Flax_Seeds.png|32x32px|link=Flax Seeds|Flax Seeds]]
| [[Flax Seeds]]
| 0.02
| -1
| -50
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.FlaxSeed
|-
| [[File:Flour.png|32x32px|link=Flour|Flour]]
| [[Flour]]
| 2
| -60
| -30
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Flour2
|-
| [[File:PowderedGarlic.png|32x32px|link=Garlic (Powdered)|Garlic (Powdered)]]
| [[Garlic (Powdered)]]
| 0.2
| -10
| -50
| 20
| 20
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.PowderedGarlic
|-
| [[File:GingerPickled.png|32x32px|link=Ginger (Pickled)|Ginger (Pickled)]]
| [[Ginger (Pickled)]]
| 0.1
| -5
| -50
| -
| -
| -
| 14
| 21
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.GingerPickled
|-
| [[File:RootGinger.png|32x32px|link=Ginger Root|Ginger Root]]
| [[Ginger Root]]
| 0.1
| -5
| -50
| -
| -
| -
| 6
| 10
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.GingerRoot
|-
| [[File:Ginseng.png|32x32px|link=Ginseng|Ginseng]]
| [[Ginseng]]
| 0.1
| -1
| -10
| -
| -
| -
| 14
| 28
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Ginseng
|-
| [[File:Honeybottle.png|32x32px|link=Honey|Honey]]
| [[Honey]]
| 0.4
| -20
| -50
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Honey
|-
| [[File:Hotsauce.png|32x32px|link=Hot Sauce|Hot Sauce]]
| [[Hot Sauce]]
| 0.2
| -16
| -80
| -
| 20
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Hotsauce
|-
| [[File:Ketchup.png|32x32px|link=Ketchup|Ketchup]]
| [[Ketchup]]
| 0.2
| -20
| -100
| -
| 30
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Ketchup
|-
| [[File:Lard.png|32x32px|link=Lard|Lard]]
| [[Lard]]
| 0.3
| -24
| -80
| -
| 30
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Lard
|-
| [[File:MapleSyrup.png|32x32px|link=Maple Syrup|Maple Syrup]]
| [[Maple Syrup]]
| 0.2
| -45
| -225
| -
| -20
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.MapleSyrup
|-
| [[File:Margerine.png|32x32px|link=Margarine|Margarine]]
| [[Margarine]]
| 0.3
| -24
| -80
| -
| 20
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Margarine
|-
| [[File:Marinarai.png|32x32px|link=Marinara|Marinara]]
| [[Marinara]]
| 0.2
| -10
| -50
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Marinara
|-
| <span class="cycle-img">[[File:TZ_MayonnaiseFull.png|32x32px|link=Mayonnaise|Mayonnaise]][[File:TZ_MayonnaiseFullRotten.png|32x32px|link=Mayonnaise|Mayonnaise]]</span>
| [[Mayonnaise]]
| 0.5
| -30
| -60
| -
| 5
| 10
| 10
| 13
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.MayonnaiseFull
|-
| [[File:Mustard.png|32x32px|link=Mustard|Mustard]]
| [[Mustard]]
| 0.2
| -20
| -100
| -
| 30
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Mustard
|-
| [[File:Dip_NachoCheese.png|32x32px|link=Nacho Cheese|Nacho Cheese]]
| [[Nacho Cheese]]
| 0.2
| -16
| -80
| -
| -10
| -
| 60
| 75
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Dip_NachoCheese
|-
| [[File:OilOlive.png|32x32px|link=Olive Oil|Olive Oil]]
| [[Olive Oil]]
| 0.2
| -30
| -150
| -
| 50
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.OilOlive
|-
| [[File:PowderedOnion.png|32x32px|link=Onion (Powdered)|Onion (Powdered)]]
| [[Onion (Powdered)]]
| 0.2
| -10
| -50
| 20
| 20
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.PowderedOnion
|-
| [[File:Pepper.png|32x32px|link=Pepper|Pepper]]
| [[Pepper]]
| 0.2
| -10
| -50
| 20
| 20
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Pepper
|-
| [[File:Pickles.png|32x32px|link=Pickle|Pickle]]
| [[Pickle]]
| 0.1
| -6
| -60
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Pickles
|-
| [[File:PoppySeeds.png|32x32px|link=Poppy Seeds|Poppy Seeds]]
| [[Poppy Seeds]]
| 0.1
| -1
| -10
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.PoppySeed
|-
| <span class="cycle-img">[[File:PumpkinSeeds.png|32x32px|link=Pumpkin Seeds|Pumpkin Seeds]][[File:PumpkinSeedsCooked.png|32x32px|link=Pumpkin Seeds|Pumpkin Seeds]][[File:PumpkinSeedsBurnt.png|32x32px|link=Pumpkin Seeds|Pumpkin Seeds]]</span>
| [[Pumpkin Seeds]]
| 0.1
| -5
| -50
| -
| 5*
| -
| ∞
| ∞
| 10
| 30
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.PumpkinSeed
|-
| [[File:Dip_Ranch.png|32x32px|link=Ranch|Ranch]]
| [[Ranch]]
| 0.2
| -16
| -80
| -
| -
| -
| 60
| 75
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Dip_Ranch
|-
| <span class="cycle-img">[[File:TZ_RemouladeFull.png|32x32px|link=Remoulade|Remoulade]][[File:TZ_RemouladeFullRotten.png|32x32px|link=Remoulade|Remoulade]]</span>
| [[Remoulade]]
| 0.5
| -10
| -20
| -
| 5
| 10
| 8
| 11
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.RemouladeFull
|-
| [[File:RiceVinegar.png|32x32px|link=Rice Vinegar|Rice Vinegar]]
| [[Rice Vinegar]]
| 0.2
| -20
| -100
| -
| 50
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.RiceVinegar
|-
| [[File:Dip_Salsa.png|32x32px|link=Salsa|Salsa]]
| [[Salsa]]
| 0.2
| -16
| -80
| -
| -
| -
| 60
| 75
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Dip_Salsa
|-
| [[File:Salt.png|32x32px|link=Salt|Salt]]
| [[Salt]]
| 0.2
| -10
| -50
| 20
| 20
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Salt
|-
| [[File:SeasoningSalt.png|32x32px|link=Seasoning Salt|Seasoning Salt]]
| [[Seasoning Salt]]
| 0.2
| -10
| -50
| 20
| 20
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.SeasoningSalt
|-
| [[File:Seaweed.png|32x32px|link=Seaweed|Seaweed]]
| [[Seaweed]]
| 0.2
| -3
| -15
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Seaweed
|-
| [[File:SesameOil.png|32x32px|link=Sesame Oil|Sesame Oil]]
| [[Sesame Oil]]
| 0.2
| -10
| -50
| 40
| 50
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.SesameOil
|-
| [[File:SourCream.png|32x32px|link=Sour Cream|Sour Cream]]
| [[Sour Cream]]
| 0.2
| -16
| -80
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.SourCream
|-
| [[File:Soysauce.png|32x32px|link=Soy Sauce|Soy Sauce]]
| [[Soy Sauce]]
| 0.2
| -10
| -50
| 40
| 50
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Soysauce
|-
| [[File:SugarCubes.png|32x32px|link=Sugar Cubes|Sugar Cubes]]
| [[Sugar Cubes]]
| 0.02
| -4
| -200
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.SugarCubes
|-
| [[File:SugarPacket.png|32x32px|link=Sugar Packet|Sugar Packet]]
| [[Sugar Packet]]
| 0.005
| -1
| -200
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.SugarPacket
|-
| [[File:SunflowerSeeds.png|32x32px|link=Sunflower Seeds|Sunflower Seeds]]
| [[Sunflower Seeds]]
| 0.1
| -5
| -50
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.SunflowerSeeds
|-
| [[File:TomatoPaste.png|32x32px|link=Tomato Paste|Tomato Paste]]
| [[Tomato Paste]]
| 0.2
| -15
| -75
| -
| 20
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.TomatoPaste
|-
| [[File:OilVegetable.png|32x32px|link=Vegetable Oil|Vegetable Oil]]
| [[Vegetable Oil]]
| 0.2
| -30
| -150
| -
| 50
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.OilVegetable
|-
| [[File:Violets.png|32x32px|link=Violets|Violets]]
| [[Violets]]
| 0.1
| -2
| -20
| -
| -
| -
| 6
| 10
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Violets
|-
| [[File:Wasabi.png|32x32px|link=Wasabi|Wasabi]]
| [[Wasabi]]
| 0.2
| -10
| -50
| 20
| -
| -
| 4
| 8
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Wasabi
|-
| [[File:Sugar.png|32x32px|link=White Sugar|White Sugar]]
| [[White Sugar]]
| 0.6
| -30
| -50
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Sugar
|}
</div><!-- Bot_flag_end|type=food_item_list|id=spice -->

=== Grains ===
<!-- Bot_flag|type=food_item_list|id=grains --><div class="scroll-x">
{| class="wikitable theme-red sortable sticky-column" style="text-align: center;"
! Icon
! Name
! [[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Hunger_32.png|link=|Hunger]]
! [[File:Status_Hunger_32.png|link=|Hunger]]/[[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Thirst_32.png|link=|Thirst]]
! [[File:Mood_Sad_32.png|link=|Unhappiness]]
! [[File:UI_Fresh_Time.png|32px|link=|Fresh (days)]]
! [[File:UI_Rotten_Time.png|32px|link=|Rotten (days)]]
! [[File:Pepper.png|24px|link=|Spice]]
! Item ID
|-
| <span class="cycle-img">[[File:Bread.png|32x32px|link=Bread|Bread]][[File:BreadRotten.png|32x32px|link=Bread|Bread]]</span>
| [[Bread]]
| 0.3
| -30
| -100
| -
| -
| 3
| 6
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Bread
|-
| [[File:Ramen.png|32x32px|link=Dry Ramen Noodles|Dry Ramen Noodles]]
| [[Dry Ramen Noodles]]
| 0.2
| -10
| -50
| 40
| 20
| 365
| 730
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Ramen
|-
| [[File:BunsHotdog_single.png|32x32px|link=Hotdog Bun|Hotdog Bun]]
| [[Hotdog Bun]]
| 0.1
| -10
| -100
| -
| -
| 3
| 6
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BunsHotdog_single
|-
| [[File:BunsHamburger_single.png|32x32px|link=Hamburger Bun|Hamburger Bun]]
| [[Hamburger Bun]]
| 0.1
| -10
| -100
| -
| -
| 3
| 6
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BunsHamburger_single
|-
| [[File:BunsHamburger.png|32x32px|link=Pack of Hamburger Buns|Pack of Hamburger Buns]]
| [[Pack of Hamburger Buns]]
| 0.4
| -
| -
| -
| -
| 3
| 6
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BunsHamburger
|-
| [[File:BunsHotdog.png|32x32px|link=Pack of Hotdog Buns|Pack of Hotdog Buns]]
| [[Pack of Hotdog Buns]]
| 0.3
| -
| -
| -
| -
| 3
| 6
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BunsHotdog
|-
| [[File:SpagettiRaw.png|32x32px|link=Pasta|Pasta]]
| [[Pasta]]
| 2
| -60
| -30
| 60
| 40
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Pasta
|-
| [[File:RiceRaw.png|32x32px|link=Rice|Rice]]
| [[Rice]]
| 2
| -60
| -30
| -
| -
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Rice
|}
</div><!-- Bot_flag_end|type=food_item_list|id=grains -->

=== Candy ===
<!-- Bot_flag|type=food_item_list|id=candy --><div class="scroll-x">
{| class="wikitable theme-red sortable sticky-column" style="text-align: center;"
! Icon
! Name
! [[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Hunger_32.png|link=|Hunger]]
! [[File:Status_Hunger_32.png|link=|Hunger]]/[[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Thirst_32.png|link=|Thirst]]
! [[File:Mood_Sad_32.png|link=|Unhappiness]]
! [[File:Mood_Stressed_32.png|link=|Stress]]
! [[File:UI_Fresh_Time.png|32px|link=|Fresh (days)]]
! [[File:UI_Rotten_Time.png|32px|link=|Rotten (days)]]
! [[File:Pepper.png|24px|link=|Spice]]
! Item ID
|-
| [[File:Chocolate_Butterchunkers.png|32x32px|link=Butterchunkers Bar|Butterchunkers Bar]]
| [[Butterchunkers Bar]]
| 0.2
| -20
| -100
| -
| -10
| -1
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Chocolate_Butterchunkers
|-
| [[File:CandiedApple.png|32x32px|link=Candied Apple|Candied Apple]]
| [[Candied Apple]]
| 0.2
| -18
| -90
| -4
| -10
| -1
| 5
| 8
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CandiedApple
|-
| [[File:CandyFruitSlices.png|32x32px|link=Candied Fruit Slices|Candied Fruit Slices]]
| [[Candied Fruit Slices]]
| 0.1
| -5
| -50
| -
| -10
| -
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CandyFruitSlices
|-
| [[File:Candycane.png|32x32px|link=Candy Cane|Candy Cane]]
| [[Candy Cane]]
| 0.2
| -10
| -50
| -
| -10
| -
| ∞
| ∞
| [[File:UI Tick.png|link=|Used as spice in cooking]]
| Base.Candycane
|-
| [[File:CandyCorn.png|32x32px|link=Candy Corn|Candy Corn]]
| [[Candy Corn]]
| 0.2
| -10
| -50
| -
| -10
| -
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CandyCorn
|-
| [[File:CandyPackagei.png|32x32px|link=Candy Package|Candy Package]]
| [[Candy Package]]
| 0.6
| -
| -
| -
| -
| -
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CandyPackage
|-
| [[File:CandyCaramels.png|32x32px|link=Caramel Candies|Caramel Candies]]
| [[Caramel Candies]]
| 0.1
| -5
| -50
| -
| -10
| -1
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CandyCaramels
|-
| [[File:Chocolate_Candy.png|32x32px|link=Chocolate Candy|Chocolate Candy]]
| [[Chocolate Candy]]
| 0.1
| -5
| -50
| -
| -10
| -1
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Chocolate_Candy
|-
| [[File:Chocolate_Crackle.png|32x32px|link=Crackle Bar|Crackle Bar]]
| [[Crackle Bar]]
| 0.2
| -20
| -100
| -
| -10
| -1
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Chocolate_Crackle
|-
| [[File:Chocolate_Deux.png|32x32px|link=Deux Bar|Deux Bar]]
| [[Deux Bar]]
| 0.2
| -20
| -100
| -
| -10
| -1
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Chocolate_Deux
|-
| [[File:Chocolate_GalacticDairy.png|32x32px|link=Galactic Dairy Bar|Galactic Dairy Bar]]
| [[Galactic Dairy Bar]]
| 0.2
| -20
| -100
| -
| -10
| -1
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Chocolate_GalacticDairy
|-
| [[File:Gum.png|32x32px|link=Gum|Gum]]
| [[Gum]]
| 0.1
| -1
| -10
| -
| -5
| -
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Gum
|-
| [[File:GummyBears.png|32x32px|link=Gummy Bears|Gummy Bears]]
| [[Gummy Bears]]
| 0.1
| -5
| -50
| -
| -10
| -
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.GummyBears
|-
| [[File:CandyGummyfish.png|32x32px|link=Gummy Fish Candy|Gummy Fish Candy]]
| [[Gummy Fish Candy]]
| 0.1
| -5
| -50
| -
| -10
| -1
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CandyGummyfish
|-
| [[File:GummyWorms.png|32x32px|link=Gummy Worms|Gummy Worms]]
| [[Gummy Worms]]
| 0.1
| -5
| -50
| -
| -10
| -
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.GummyWorms
|-
| [[File:CandyMolasses.png|32x32px|link=Halloween Candy|Halloween Candy]]
| [[Halloween Candy]]
| 0.1
| -5
| -50
| -
| -10
| -1
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CandyMolasses
|-
| [[File:HardCandies.png|32x32px|link=Hard Candies|Hard Candies]]
| [[Hard Candies]]
| 0.1
| -5
| -50
| -
| -10
| -
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.HardCandies
|-
| [[File:JellyBeans.png|32x32px|link=Jellybeans|Jellybeans]]
| [[Jellybeans]]
| 0.1
| -5
| -50
| -
| -10
| -
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.JellyBeans
|-
| [[File:Jujujubes.png|32x32px|link=Jujubes|Jujubes]]
| [[Jujubes]]
| 0.1
| -5
| -50
| -
| -10
| -
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Jujubes
|-
| [[File:LicoriceBlack.png|32x32px|link=Licorice|Licorice]]
| [[Licorice]]
| 0.1
| -2
| -20
| -
| -5
| -
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.LicoriceBlack
|-
| [[File:LicoriceRed.png|32x32px|link=Licorice|Licorice]]
| [[Licorice]]
| 0.1
| -2
| -20
| -
| -5
| -
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.LicoriceRed
|-
| [[File:Allsorts.png|32x32px|link=Licorice Allsorts|Licorice Allsorts]]
| [[Licorice Allsorts]]
| 0.2
| -10
| -50
| -
| -10
| -
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Allsorts
|-
| [[File:Lollipop.png|32x32px|link=Lollipop|Lollipop]]
| [[Lollipop]]
| 0.1
| -5
| -50
| -
| -10
| -
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Lollipop
|-
| [[File:Chocolate.png|32x32px|link=Milk Chocolate Bar|Milk Chocolate Bar]]
| [[Milk Chocolate Bar]]
| 0.2
| -20
| -100
| -
| -10
| -
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Chocolate
|-
| [[File:MintCandy.png|32x32px|link=Mint Candy|Mint Candy]]
| [[Mint Candy]]
| 0.1
| -2
| -20
| -
| -5
| -
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.MintCandy
|-
| [[File:CandyNovapops.png|32x32px|link=Novapops Candy|Novapops Candy]]
| [[Novapops Candy]]
| 0.1
| -5
| -50
| -
| -10
| -1
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CandyNovapops
|-
| [[File:RockCandy.png|32x32px|link=Rock Candy|Rock Candy]]
| [[Rock Candy]]
| 0.1
| -5
| -50
| -
| -10
| -
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.RockCandy
|-
| [[File:Chocolate_RoysPBPucks.png|32x32px|link=Roy's Peanut Butter Pucks|Roy's Peanut Butter Pucks]]
| [[Roy's Peanut Butter Pucks]]
| 0.2
| -20
| -100
| -
| -10
| -1
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Chocolate_RoysPBPucks
|-
| [[File:Chocolate_Smirkers.png|32x32px|link=Smirkers Bar|Smirkers Bar]]
| [[Smirkers Bar]]
| 0.2
| -20
| -100
| -
| -10
| -1
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Chocolate_Smirkers
|-
| [[File:Chocolate_SnikSnak.png|32x32px|link=SnikSnak Bar|SnikSnak Bar]]
| [[SnikSnak Bar]]
| 0.2
| -20
| -100
| -
| -10
| -2
| ∞
| ∞
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Chocolate_SnikSnak
|}
</div><!-- Bot_flag_end|type=food_item_list|id=candy -->

=== Miscellaneous food ===
<!-- Bot_flag|type=food_item_list|id=miscellaneous --><div class="scroll-x">
{| class="wikitable theme-red sortable sticky-column" style="text-align: center;"
! Icon
! Name
! [[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Hunger_32.png|link=|Hunger]]
! [[File:Status_Hunger_32.png|link=|Hunger]]/[[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Thirst_32.png|link=|Thirst]]
! [[File:Mood_Sad_32.png|link=|Unhappiness]]
! [[File:Mood_Stressed_32.png|link=|Stress]]
! [[File:Mood_Sleepy_32.png|link=|Fatigue]]
! [[File:Mood_Nauseous_32.png|link=|Food Sickness]]
! [[File:UI_Fresh_Time.png|32px|link=|Fresh (days)]]
! [[File:UI_Rotten_Time.png|32px|link=|Rotten (days)]]
! [[File:UI_Cook_Time.png|32px|link=|Cooked (mins)]]
! [[File:UI_Burn_Time.png|32px|link=|Burned (mins)]]
! [[File:Pepper.png|24px|link=|Spice]]
! Item ID
|-
| [[File:Pie_Apple.png|32x32px|link=Apple Pie Slice|Apple Pie Slice]]
| [[Apple Pie Slice]]
| 0.5
| -30
| -60
| -
| -10
| -
| -
| -
| 5
| 8
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PieApple
|-
| [[File:Frozen_ChickenNuggets.png|32x32px|link=Bag of Chicken Nuggets|Bag of Chicken Nuggets]]
| [[Bag of Chicken Nuggets]]
| 1
| -
| -
| -
| -
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Frozen_ChickenNuggets
|-
| [[File:Frozen_FrenchFries.png|32x32px|link=Bag of Fries|Bag of Fries]]
| [[Bag of Fries]]
| 1
| -
| -
| -
| -
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Frozen_FrenchFries
|-
| [[File:Frozen_TatoDots.png|32x32px|link=Bag of Tato Dots|Bag of Tato Dots]]
| [[Bag of Tato Dots]]
| 1
| -
| -
| -
| -
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Frozen_TatoDots
|-
| [[File:WheatGrains.png|32x32px|link=Barley Seeds|Barley Seeds]]
| [[Barley Seeds]]
| 0.02
| -5
| -250
| -
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.BarleySeed
|-
| [[File:CakeBlackForest.png|32x32px|link=Black Forest Cake Slice|Black Forest Cake Slice]]
| [[Black Forest Cake Slice]]
| 0.2
| -10
| -50
| -
| -15
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CakeBlackForest
|-
| [[File:Pie_Blueberry.png|32x32px|link=Blueberry Pie Slice|Blueberry Pie Slice]]
| [[Blueberry Pie Slice]]
| 0.5
| -30
| -60
| -
| -10
| -
| -
| -
| 5
| 8
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PieBlueberry
|-
| [[File:NoodleSoup.png|32x32px|link=Bowl of Noodle Soup|Bowl of Noodle Soup]]
| [[Bowl of Noodle Soup]]
| 1
| -10
| -10
| -
| -20
| -
| -
| -
| 1
| 3
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.NoodleSoup
|-
| [[File:BowlFull.png|32x32px|link=Bowl of Ramen Noodles|Bowl of Ramen Noodles]]
| [[Bowl of Ramen Noodles]]
| 1
| -10
| -10
| -
| -20
| -
| -
| -
| 1
| 3
| 10
| 20
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.RamenBowl
|-
| [[File:Flax_PasteBowl.png|32x32px|link=Bowl with Seed Paste|Bowl with Seed Paste]]
| [[Bowl with Seed Paste]]
| 0.3
| -30
| -100
| -
| 50
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SeedPasteBowl
|-
| [[File:Chocolate_Heartbox.png|32x32px|link=Box of Chocolates|Box of Chocolates]]
| [[Box of Chocolates]]
| 0.5
| -40
| -80
| -
| -20
| -2
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Chocolate_HeartBox
|-
| [[File:Pipe_BeerCan.png|32x32px|link=Can Pipe with Tobacco|Can Pipe with Tobacco]]
| [[Can Pipe with Tobacco]]
| 0.3
| -
| -
| -
| -
| -15
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CanPipe_Tobacco
|-
| [[File:OatsRaw.png|32x32px|link=Can of Oats|Can of Oats]]
| [[Can of Oats]]
| 0.8
| -50
| -62
| -
| -
| -
| -
| -
| 180
| 365
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.OatsRaw
|-
| [[File:CakeCarrot.png|32x32px|link=Carrot Cake Slice|Carrot Cake Slice]]
| [[Carrot Cake Slice]]
| 0.2
| -7
| -35
| -
| -10
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CakeCarrot
|-
| [[File:CatTreats.png|32x32px|link=Cat Treats|Cat Treats]]
| [[Cat Treats]]
| 0.1
| -5
| -50
| -
| 20
| -
| -
| -
| 365
| 547
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CatTreats
|-
| <span class="cycle-img">[[File:Cereal_SunBallz.png|32x32px|link=Cereal|Cereal]][[File:Cereal_CornFlakes.png|32x32px|link=Cereal|Cereal]][[File:Cereal_Muesli.png|32x32px|link=Cereal|Cereal]][[File:Cereal_HappyCurios.png|32x32px|link=Cereal|Cereal]][[File:Cereal_OatRings.png|32x32px|link=Cereal|Cereal]]</span>
| [[Cereal]]
| 0.2
| -40
| -200
| -
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Cereal
|-
| <span class="cycle-img">[[File:Cheese.png|32x32px|link=Cheese|Cheese]][[File:CheeseRotten.png|32x32px|link=Cheese|Cheese]]</span>
| [[Cheese]]
| 0.2
| -15
| -75
| -
| -
| -
| -
| -
| 14
| 20
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Cheese
|-
| [[File:CakeCheesecake.png|32x32px|link=Cheese Cake Slice|Cheese Cake Slice]]
| [[Cheese Cake Slice]]
| 0.2
| -8
| -40
| -
| -10
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CakeCheeseCake
|-
| [[File:ChickenFoot.png|32x32px|link=Chicken Foot|Chicken Foot]]
| [[Chicken Foot]]
| 0.1
| -12
| -120
| -
| -
| -
| -
| -
| 2
| 4
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.ChickenFoot
|-
| [[File:Crisps2.png|32x32px|link=Chips - Barbecue|Chips - Barbecue]]
| [[Chips - Barbecue]]
| 0.2
| -15
| -75
| -
| -5
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Crisps2
|-
| [[File:Crisps.png|32x32px|link=Chips - Plain|Chips - Plain]]
| [[Chips - Plain]]
| 0.2
| -15
| -75
| -
| -5
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Crisps
|-
| [[File:Crisps3.png|32x32px|link=Chips - Salt & Vinegar|Chips - Salt & Vinegar]]
| [[Chips - Salt & Vinegar]]
| 0.2
| -15
| -75
| -
| -5
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Crisps3
|-
| [[File:Crisps4.png|32x32px|link=Chips - Sour Cream & Onion|Chips - Sour Cream & Onion]]
| [[Chips - Sour Cream & Onion]]
| 0.2
| -15
| -75
| -
| -5
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Crisps4
|-
| [[File:Snackcake_Chocakes.png|32x32px|link=Choco Cakes|Choco Cakes]]
| [[Choco Cakes]]
| 0.2
| -10
| -50
| -
| -10
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.ChocoCakes
|-
| [[File:Painauchocolat.png|32x32px|link=Chocolate Bread|Chocolate Bread]]
| [[Chocolate Bread]]
| 0.1
| -2
| -20
| -
| -5
| -
| -
| -
| 3
| 7
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Painauchocolat
|-
| [[File:CakeChocolate.png|32x32px|link=Chocolate Cake Slice|Chocolate Cake Slice]]
| [[Chocolate Cake Slice]]
| 0.2
| -10
| -50
| -
| -15
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CakeChocolate
|-
| [[File:ChocolateChips.png|32x32px|link=Chocolate Chips|Chocolate Chips]]
| [[Chocolate Chips]]
| 0.1
| -6
| -60
| -
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.ChocolateChips
|-
| [[File:DoughnutChocolate.png|32x32px|link=Chocolate Donut|Chocolate Donut]]
| [[Chocolate Donut]]
| 0.1
| -7
| -70
| -
| -15
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DoughnutChocolate
|-
| [[File:ChocolateCoveredCoffeeBeans.png|32x32px|link=Chocolate-Covered Coffee Beans|Chocolate-Covered Coffee Beans]]
| [[Chocolate-Covered Coffee Beans]]
| 0.1
| -5
| -50
| -
| -10
| -
| -5
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.ChocolateCoveredCoffeeBeans
|-
| [[File:CinnamonRoll.png|32x32px|link=Cinnamon Roll|Cinnamon Roll]]
| [[Cinnamon Roll]]
| 0.1
| -12
| -120
| -
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CinnamonRoll
|-
| [[File:CocoaPowder.png|32x32px|link=Cocoa Powder|Cocoa Powder]]
| [[Cocoa Powder]]
| 1
| -30
| -30
| 50
| -10
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CocoaPowder
|-
| [[File:InstantCoffee.png|32x32px|link=Coffee|Coffee]]
| [[Coffee]]
| 1
| -30
| -30
| 60
| 20
| -
| -50
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Coffee2
|-
| [[File:Cone.png|32x32px|link=Cone|Cone]]
| [[Cone]]
| 0.1
| -5
| -50
| -
| -
| -
| -
| -
| 15
| 20
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Cone
|-
| [[File:Cornbread.png|32x32px|link=Cornbread|Cornbread]]
| [[Cornbread]]
| 0.1
| -10
| -100
| -
| -
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Cornbread
|-
| [[File:Corndog.png|32x32px|link=Corndog|Corndog]]
| [[Corndog]]
| 0.1
| -12
| -120
| -
| -
| -
| -
| -
| 3
| 6
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Corndog
|-
| [[File:Crackers.png|32x32px|link=Crackers|Crackers]]
| [[Crackers]]
| 0.1
| -5
| -50
| -
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Crackers
|-
| [[File:Creamocle.png|32x32px|link=Creamocle|Creamocle]]
| [[Creamocle]]
| 0.2
| -15
| -75
| -
| -10
| -
| -
| -
| 1
| 2
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Creamocle
|-
| [[File:Creamocle_Melted.png|32x32px|link=Creamocle (Melted)|Creamocle (Melted)]]
| [[Creamocle (Melted)]]
| 0.2
| -15
| -75
| -
| -
| -
| -
| -
| 2
| 3
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Creamocle_Melted
|-
| [[File:CrispyRiceSquare.png|32x32px|link=Crispy Rice Square|Crispy Rice Square]]
| [[Crispy Rice Square]]
| 0.2
| -10
| -50
| -
| -10
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CrispyRiceSquare
|-
| [[File:Croissant.png|32x32px|link=Croissant|Croissant]]
| [[Croissant]]
| 0.1
| -8
| -80
| -
| -15
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Croissant
|-
| [[File:Cupcake.png|32x32px|link=Cupcake|Cupcake]]
| [[Cupcake]]
| 0.2
| -20
| -100
| -
| -10
| -
| -
| -
| 4
| 8
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Cupcake
|-
| [[File:Danish.png|32x32px|link=Danish|Danish]]
| [[Danish]]
| 0.1
| -7
| -70
| -
| -15
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Danish
|-
| [[File:DehydratedMeatStick.png|32x32px|link=Dehydrated Meat Stick|Dehydrated Meat Stick]]
| [[Dehydrated Meat Stick]]
| 0.1
| -10
| -100
| -
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DehydratedMeatStick
|-
| [[File:DoughnutPlain.png|32x32px|link=Donut|Donut]]
| [[Donut]]
| 0.1
| -7
| -70
| -
| -15
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DoughnutPlain
|-
| <span class="cycle-img">[[File:Dough.png|32x32px|link=Dough|Dough]][[File:DoughRotten.png|32x32px|link=Dough|Dough]][[File:DoughCooked.png|32x32px|link=Dough|Dough]][[File:DoughBurnt.png|32x32px|link=Dough|Dough]]</span>
| [[Dough]]
| 0.3
| -15
| -50
| 20
| -20
| -
| -
| ?
| 3
| 6
| 40
| 80
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Dough
|-
| [[File:CatFood.png|32x32px|link=Dry Cat Food|Dry Cat Food]]
| [[Dry Cat Food]]
| 2
| -60
| -30
| -
| 20
| -
| -
| -
| 365
| 547
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CatFoodBag
|-
| [[File:DogFoodBag.png|32x32px|link=Dry Dog Food|Dry Dog Food]]
| [[Dry Dog Food]]
| 2
| -60
| -30
| -
| 20
| -
| -
| -
| 365
| 547
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DogFoodBag
|-
| [[File:SushiEgg.png|32x32px|link=Egg Sushi|Egg Sushi]]
| [[Egg Sushi]]
| 0.1
| -8
| -80
| -
| -10
| -
| -
| -
| 2
| 4
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SushiEgg
|-
| [[File:ChickenFried.png|32x32px|link=Fried Chicken|Fried Chicken]]
| [[Fried Chicken]]
| 0.1
| -15
| -150
| -
| -
| -
| -
| -
| 2
| 4
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.ChickenFried
|-
| [[File:Fries.png|32x32px|link=Fries|Fries]]
| [[Fries]]
| 0.4
| -10
| -25
| -
| -10
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Fries
|-
| [[File:DoughnutFrosted.png|32x32px|link=Frosted Donut|Frosted Donut]]
| [[Frosted Donut]]
| 0.1
| -7
| -70
| -
| -15
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DoughnutFrosted
|-
| [[File:JamFruit.png|32x32px|link=Fruit Jam|Fruit Jam]]
| [[Fruit Jam]]
| 0.2
| -30
| -150
| -
| -10
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.JamFruit
|-
| [[File:MuffinFruit.png|32x32px|link=Fruit Muffin|Fruit Muffin]]
| [[Fruit Muffin]]
| 0.1
| -7
| -70
| -
| -10
| -
| -
| -
| 5
| 8
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.MuffinFruit
|-
| [[File:FudgeePop.png|32x32px|link=Fudgee Pop|Fudgee Pop]]
| [[Fudgee Pop]]
| 0.2
| -15
| -75
| -
| -10
| -
| -
| -
| 1
| 2
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.FudgeePop
|-
| [[File:FudgeePop_Melted.png|32x32px|link=Fudgee Pop (Melted)|Fudgee Pop (Melted)]]
| [[Fudgee Pop (Melted)]]
| 0.2
| -15
| -75
| -
| -
| -
| -
| -
| 2
| 3
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.FudgeePop_Melted
|-
| [[File:Gingerbreadman.png|32x32px|link=Gingerbread Man|Gingerbread Man]]
| [[Gingerbread Man]]
| 0.1
| -5
| -50
| -
| -10
| -1
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Gingerbreadman
|-
| [[File:GrahamCrackers.png|32x32px|link=Graham Crackers|Graham Crackers]]
| [[Graham Crackers]]
| 0.1
| -5
| -50
| -
| -3
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.GrahamCrackers
|-
| [[File:GranolaBar.png|32x32px|link=Granola Bar|Granola Bar]]
| [[Granola Bar]]
| 0.2
| -15
| -75
| -
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.GranolaBar
|-
| [[File:Snackcake_HiHis.png|32x32px|link=Hi His|Hi His]]
| [[Hi His]]
| 0.2
| -10
| -50
| -
| -10
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.HiHis
|-
| [[File:MugWhiteFull.png|32x32px|link=Beverage (mug)|Hot Drink]]
| [[Beverage (mug)|Hot Drink]]
| 0.5
| -
| -
| -20
| -10
| -
| -
| -
| ∞
| ∞
| 10
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.TestHotDrink
|-
| [[File:MugRedFull.png|32x32px|link=Beverage (mug)|Hot Drink]]
| [[Beverage (mug)|Hot Drink]]
| 0.5
| -
| -
| -20
| -10
| -
| -
| -
| ∞
| ∞
| 10
| 50
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.HotDrinkRed
|-
| [[File:Icecream.png|32x32px|link=Ice Cream|Ice Cream]]
| [[Ice Cream]]
| 0.2
| -30
| -150
| -
| -10
| -5
| -
| -
| 1
| 2
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Icecream
|-
| [[File:IcecreamMelted.png|32x32px|link=Ice Cream|Ice Cream (Melted)]]
| [[Ice Cream|Ice Cream (Melted)]]
| 0.2
| -30
| -150
| -
| -
| -
| -
| -
| 2
| 3
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.IcecreamMelted
|-
| [[File:ConeIcecream.png|32x32px|link=Ice Cream Cone|Ice Cream Cone (Melted)]]
| [[Ice Cream Cone|Ice Cream Cone (Melted)]]
| 0.2
| -15
| -75
| -
| -
| -
| -
| -
| 2
| 3
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.ConeIcecreamMelted
|-
| [[File:IcecreamSandwich.png|32x32px|link=Ice Cream Sandwich|Ice Cream Sandwich]]
| [[Ice Cream Sandwich]]
| 0.2
| -15
| -75
| -
| -10
| -
| -
| -
| 1
| 2
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.IcecreamSandwich
|-
| [[File:IcecreamSandwich_Melted.png|32x32px|link=Ice Cream Sandwich (Melted)|Ice Cream Sandwich (Melted)]]
| [[Ice Cream Sandwich (Melted)]]
| 0.2
| -15
| -75
| -
| -
| -
| -
| -
| 2
| 3
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.IcecreamSandwich_Melted
|-
| [[File:Icing.png|32x32px|link=Icing|Icing]]
| [[Icing]]
| 0.1
| -10
| -100
| -
| -10
| -
| -
| -
| 4
| 8
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Icing
|-
| <span class="cycle-img">[[File:Popcorn.png|32x32px|link=Instant Popcorn|Instant Popcorn]][[File:PopcornCooked.png|32x32px|link=Instant Popcorn|Instant Popcorn]]</span>
| [[Instant Popcorn]]
| 0.3
| -10
| -33
| 10
| -
| -
| -
| -
| ∞
| ∞
| 5
| 10
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Popcorn
|-
| [[File:DoughnutJelly.png|32x32px|link=Jelly Donut|Jelly Donut]]
| [[Jelly Donut]]
| 0.1
| -7
| -70
| -
| -15
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.DoughnutJelly
|-
| [[File:JellyRoll.png|32x32px|link=Jelly Roll|Jelly Roll]]
| [[Jelly Roll]]
| 0.1
| -7
| -70
| -
| -15
| -1
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.JellyRoll
|-
| [[File:Pie_Keylime.png|32x32px|link=Key Lime Pie Slice|Key Lime Pie Slice]]
| [[Key Lime Pie Slice]]
| 0.5
| -30
| -60
| -
| -10
| -
| -
| -
| 5
| 8
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PieKeyLime
|-
| [[File:LemonBar.png|32x32px|link=Lemon Bar|Lemon Bar]]
| [[Lemon Bar]]
| 0.1
| -7
| -70
| -
| -15
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.LemonBar
|-
| [[File:Pie_Lemonmeringue.png|32x32px|link=Lemon Meringue Pie Slice|Lemon Meringue Pie Slice]]
| [[Lemon Meringue Pie Slice]]
| 0.5
| -30
| -60
| -
| -10
| -
| -
| -
| 5
| 8
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PieLemonMeringue
|-
| [[File:Macandcheese.png|32x32px|link=Mac and Cheese|Mac and Cheese]]
| [[Mac and Cheese]]
| 0.5
| -
| -
| -
| -
| -
| -
| -
| 180
| 365
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Macandcheese
|-
| [[File:JamMarmalade.png|32x32px|link=Marmalade|Marmalade]]
| [[Marmalade]]
| 0.2
| -30
| -150
| -
| -10
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.JamMarmalade
|-
| <span class="cycle-img">[[File:Marshmallows.png|32x32px|link=Marshmallows|Marshmallows]][[File:MarshmallowsCooked.png|32x32px|link=Marshmallows|Marshmallows]][[File:MarshmallowsBurnt.png|32x32px|link=Marshmallows|Marshmallows]]</span>
| [[Marshmallows]]
| 0.1
| -5
| -50
| -
| -5
| -
| -
| -
| ∞
| ∞
| 5
| 10
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Marshmallows
|-
| [[File:MeatSteamBun.png|32x32px|link=Meat Steam Bun|Meat Steam Bun]]
| [[Meat Steam Bun]]
| 0.1
| -15
| -150
| -
| -
| -
| -
| -
| 2
| 4
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.MeatSteamBun
|-
| [[File:Modjeska.png|32x32px|link=Modjeska|Modjeska]]
| [[Modjeska]]
| 0.1
| -10
| -100
| -
| -10
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Modjeska
|-
| [[File:PeanutButter.png|32x32px|link=Peanut Butter|Peanut Butter]]
| [[Peanut Butter]]
| 0.3
| -25
| -83
| -
| -15
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PeanutButter
|-
| [[File:Peppermint.png|32x32px|link=Peppermint Candy|Peppermint Candy]]
| [[Peppermint Candy]]
| 0.1
| -2
| -20
| -
| -5
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Peppermint
|-
| [[File:Perogies.png|32x32px|link=Perogies|Perogies]]
| [[Perogies]]
| 0.1
| -7
| -70
| -
| -
| -
| -
| -
| 3
| 7
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Perogies
|-
| [[File:Snackcake_Plonkies.png|32x32px|link=Plonkies|Plonkies]]
| [[Plonkies]]
| 0.2
| -10
| -50
| -
| -10
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Plonkies
|-
| [[File:Popsicle.png|32x32px|link=Popsicle|Popsicle]]
| [[Popsicle]]
| 0.2
| -15
| -75
| -
| -10
| -
| -
| -
| 1
| 2
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Popsicle
|-
| [[File:Popsicle_Melted.png|32x32px|link=Popsicle (Melted)|Popsicle (Melted)]]
| [[Popsicle (Melted)]]
| 0.2
| -15
| -75
| -
| -
| -
| -
| -
| 2
| 3
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Popsicle_Melted
|-
| [[File:PorkRinds.png|32x32px|link=Pork Rinds|Pork Rinds]]
| [[Pork Rinds]]
| 0.1
| -5
| -50
| -
| -2
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PorkRinds
|-
| [[File:PotatoPancakes.png|32x32px|link=Potato Pancakes|Potato Pancakes]]
| [[Potato Pancakes]]
| 0.1
| -15
| -150
| -
| -
| -
| -
| -
| 3
| 7
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PotatoPancakes
|-
| [[File:Pretzel.png|32x32px|link=Pretzel|Pretzels]]
| [[Pretzel|Pretzels]]
| 0.1
| -5
| -50
| -
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Pretzel
|-
| [[File:Processedcheese.png|32x32px|link=Processed Cheese|Processed Cheese]]
| [[Processed Cheese]]
| 0.1
| -5
| -50
| -
| -
| -
| -
| -
| 6
| 10
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Processedcheese
|-
| [[File:PiePumpkin.png|32x32px|link=Pumpkin Pie Slice|Pumpkin Pie Slice]]
| [[Pumpkin Pie Slice]]
| 0.5
| -30
| -60
| -
| -10
| -
| -
| -
| 5
| 8
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.PiePumpkin
|-
| [[File:Snackcake_QuaggaCakes.png|32x32px|link=Quagga Cakes|Quagga Cakes]]
| [[Quagga Cakes]]
| 0.2
| -10
| -50
| -
| -10
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.QuaggaCakes
|-
| [[File:CookieJelly.png|32x32px|link=Raspberry Shortbread Cookie|Raspberry Shortbread Cookie]]
| [[Raspberry Shortbread Cookie]]
| 0.1
| -5
| -50
| -
| -10
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CookieJelly
|-
| [[File:CakeRedVelvet.png|32x32px|link=Red Velvet Cake Slice|Red Velvet Cake Slice]]
| [[Red Velvet Cake Slice]]
| 0.2
| -8
| -40
| -
| -10
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CakeRedVelvet
|-
| [[File:PotFull.png|32x32px|link=Rice (sugar beet)|Rice]]
| [[Rice (sugar beet)|Rice]]
| 3
| -45
| -15
| -
| 30
| -
| -
| -
| 3
| 6
| 120
| 150
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SugarBeetPulpPot
|-
| [[File:PotFull.png|32x32px|link=Rice (sugar beet)|Rice]]
| [[Rice (sugar beet)|Rice]]
| 3
| -30
| -10
| -
| 30
| -
| -
| -
| 1
| 2
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SugarBeetSyrupPot
|-
| [[File:PotFull.png|32x32px|link=Rice (sugar beet)|Rice]]
| [[Rice (sugar beet)|Rice]]
| 3
| -30
| -10
| -
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SugarBeetSugarPot
|-
| [[File:RicePaper.png|32x32px|link=Rice Paper|Rice Paper]]
| [[Rice Paper]]
| 0.1
| -4
| -40
| -
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.RicePaper
|-
| [[File:WheatGrains.png|32x32px|link=Rye Seeds|Rye Seeds]]
| [[Rye Seeds]]
| 0.02
| -5
| -250
| -
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.RyeSeed
|-
| [[File:CookieBox.png|32x32px|link=Scout Cookies|Scout Cookies]]
| [[Scout Cookies]]
| 0.2
| -20
| -100
| -
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.ScoutCookies
|-
| [[File:Flax_Paste.png|32x32px|link=Seed Paste|Seed Paste]]
| [[Seed Paste]]
| 0.2
| -30
| -150
| -
| 50
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SeedPaste
|-
| [[File:Ceramic_SmokingPipe_Unfired.png|32x32px|link=Smoking Pipe with Tobacco|Smoking Pipe with Tobacco]]
| [[Smoking Pipe with Tobacco]]
| 0.3
| -
| -
| -
| -
| -15
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SmokingPipe_Tobacco
|-
| [[File:Smore.png|32x32px|link=Smore|Smore]]
| [[Smore]]
| 0.1
| -10
| -100
| -
| -10
| -
| -
| -
| 10
| 15
| 5
| 10
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Smore
|-
| [[File:Snackcake_SnoSpheres.png|32x32px|link=Sno Globes|Sno Globes]]
| [[Sno Globes]]
| 0.2
| -10
| -50
| -
| -10
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.SnoGlobes
|-
| [[File:Springroll.png|32x32px|link=Spring Roll|Spring Roll]]
| [[Spring Roll]]
| 0.1
| -20
| -200
| -
| -
| -
| -
| -
| 2
| 4
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Springroll
|-
| [[File:CakeStrawberryShortcake.png|32x32px|link=Strawberry Cake Slice|Strawberry Cake Slice]]
| [[Strawberry Cake Slice]]
| 0.2
| -8
| -40
| -
| -10
| -
| -
| -
| 3
| 5
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.CakeStrawberryShortcake
|-
| <span class="cycle-img">[[File:TVDinner.png|32x32px|link=TV Dinner|TV Dinner]][[File:TVDinnerRotten.png|32x32px|link=TV Dinner|TV Dinner]][[File:TVDinnerCooked.png|32x32px|link=TV Dinner|TV Dinner]][[File:TVDinnerBurnt.png|32x32px|link=TV Dinner|TV Dinner]]</span>
| [[TV Dinner]]
| 0.4
| -23
| -58
| -
| 20
| -
| -
| ?
| 3
| 5
| 10
| 15
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.TVDinner
|-
| [[File:frog_tadpole.png|32x32px|link=Tadpole|Tadpole]]
| [[Tadpole]]
| 0.1
| -1
| -10
| -
| 20
| -
| -
| ?
| 2
| 4
| 5
| 25
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Tadpole
|-
| [[File:Teabag.png|32x32px|link=Tea Bag|Tea Bag]]
| [[Tea Bag]]
| 0.1
| -5
| -50
| 10
| 10
| -
| -15
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Teabag2
|-
| [[File:CornChips.png|32x32px|link=Tortilla Chips|Tortilla Chips]]
| [[Tortilla Chips]]
| 0.2
| -15
| -75
| -
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.TortillaChips
|-
| [[File:CannedWater.png|32x32px|link=Water Ration Can|Water Ration Can]]
| [[Water Ration Can]]
| 0.8
| -
| -
| -
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.WaterRationCan
|-
| [[File:WheatGrains.png|32x32px|link=Wheat Seeds|Wheat Seeds]]
| [[Wheat Seeds]]
| 0.02
| -5
| -250
| -
| -
| -
| -
| -
| ∞
| ∞
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.WheatSeed
|-
| [[File:Yoghurt.png|32x32px|link=Yogurt|Yogurt]]
| [[Yogurt]]
| 0.3
| -10
| -33
| -
| -
| -
| -
| -
| 10
| 15
| -
| -
| [[File:UI Cross.png|link=|Used as ingredient in cooking]]
| Base.Yoghurt
|}
</div><!-- Bot_flag_end|type=food_item_list|id=miscellaneous -->

== See also ==
* {{ll|Evolved recipes}}
* {{ll|Cooking}}
* {{ll|Drinks}}
* {{ll|Fishing}}
* {{ll|Foraging}}
* {{ll|Nutrition}}
* {{ll|Trapping}}

{{ll|Category:Food|&#32;}}
{{ll|Category:Items}}
```
