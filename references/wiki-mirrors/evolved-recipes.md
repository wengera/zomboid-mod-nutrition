# Wiki mirror — Evolved recipes

**Source:** https://pzwiki.net/wiki/Evolved_recipes
**Fetched:** 2026-09-10
**Wiki page version:** 41.78.19
**License:** CC BY-NC-SA 3.0 — attribution: PZwiki contributors

## Digest

- How the evolved-recipe system works (a starting item plus ingredients becomes a named dish), the roster of recipes with their base and product items, and a transcluded per-ingredient hunger table. Stamped 41.78.19 — Build 41, so treat every number as suspect for 42.20.4.
- The shape it gets right: an ingredient's hunger contribution is per-recipe (jerky is worth 15 in a stew but 5 in a sandwich), the same amount is deducted from the ingredient, and the deduction shrinks with cooking skill so one fresh potato goes into a salad twice. That is `EvolvedRecipe.addItem`'s `hungerAfterSkill = hunger x (1 - 0.03*cookLvl)`, further divided by 1.3 if the ingredient was cooked (`docs/superpowers/plans/02-notes.md` Q5).
- Stale ingredients keep their hunger and lose the mood penalty; rotten ones need Cooking 7 and give "a small amount" — the code puts numbers on that: 5% of `baseHunger` at levels 7-8, 10% at 9-10.
- Spices and condiments go in once each, only into a started dish, and do not count against the ingredient limit — matches the spice branch of `addItem` (`isSpiceAdded`, no `MaxItems` charge), which also transfers no hunger and no macros whatsoever.
- Claims every ingredient adds -5 boredom **and** unhappiness, negated at three copies and penalised beyond — verify against `EvolvedRecipe.addItem`: on this jar only `unhappyChange` moves (`-(5 - dupes*5)`, clamped at +25, plus a separate over-stuffing term once `extraItems` exceeds `cookLvl + 2`), `boredomChange` is zeroed once and never touched again, and the bonus already stops on the second identical copy with the penalty starting on the third.
- The recipe table is B41-sized (~35 rows) and predates the `Template` mechanism: 42.20.4 loads 62 `evolvedrecipe` blocks from `media/scripts/generated/evolvedrecipes.txt`, and an item's `EvolvedRecipe = Name:use` attaches to the matching recipe *and* to every recipe whose `Template` equals that key. Verify any roster entry or hunger figure against `EvolvedRecipe.Load` / `Item.OnScriptsLoaded`, not this table.
- Silent on the nutrition side, which is where the mod's money is: `addItem` also sums `ingredientMacro x (1 + cookLvl/15) x share` into the dish, so a level-10 cook banks about 1.67x the calories a level-0 cook does for the same hunger.

## Wikitext

```wikitext
{{LangSwitch}}
{{Navbar items}}
{{Page version|41.78.19}}
[[File:Recipe Ingredients Page Img1.png|frame|right|In-game UI showing a character about to create a [[salad]] using a [[bowl]]]]
An '''evolved recipe''' is a way to create [[food]] [[item]]s that was introduced in [[Build 32]]. It allows ingredients to be combined to create custom recipes. Each recipe requires a starting item, before other ingredients can be added. Multiple ingredients can be used to increase the effectiveness of the recipe.

== Usage ==
{{Main|Cooking}}
To start crafting the recipe, the player must right-click on the starting item with at least one usable ingredient in the [[player]]'s inventory. The name of the item crafted will depend on the ingredients used. Any recipe with 3 or more ingredients can be renamed by the player.

The [[hunger]] reduction of a recipe depends on the ingredient used. For example, in a [[soup]], a [[potato]] provides 15 hunger reduction, while a [[cabbage]] only provides 10. The hunger reduction an ingredient provides is also affected by the recipe itself. While [[Beef Jerky|beef jerky]] can provide 15 hunger reduction to a [[stew]], it can only 5 hunger reduction to a [[Sandwich (bread)|sandwich]]. The amount of hunger reduction granted will be shown in the menu when hovering over an ingredient to add.

Due to this, some ingredients will not be fully used when added to a recipe, with a portion remaining in the player's inventory. Hunger reduction points varies not only by the original recipe, but also by item. For example, a [[potato]] has a base of 18 hunger reduction points, when fresh and uncooked. If used in a [[salad]], that potato provides 9 hunger reduction to that salad. Subsequently, 9 points of hunger reduction are subtracted from the original potato, scaling inversely with cooking level (less hunger points are subtracted as cooking skill increases). This allows the potato to be used twice in a salad before being used up completely, assuming it is fresh and uncooked.

Ingredients also provide [[boredom]] and [[unhappiness]] reduction: every ingredient adds -5 boredom/unhappiness the first time it is added. If three of the same ingredients are added then the boredom/unhappiness bonuses are negated, and if more than three of the same ingredient are added, a penalty to boredom/unhappiness will be added.

=== Advantages ===
There are several advantages to using food in recipes instead of eating it individually. Depending on the recipe:
* Ingredients can provide more hunger reduction than as stand-alone foods.
* Recipes provide boredom and unhappiness reductions.
* Using ingredients in some recipes will eliminate boredom and unhappiness penalties caused by eating stale food.
* Ingredients that have gone stale can still be used in recipes. Their hunger reduction will be added, while the boredom and unhappiness penalties will not. This is a good way to extend the life of your perishable foods.
* Ingredients that have gone rotten can be used by characters with [[cooking]] [[skill]] of at least 7. This will add a small amount of the hunger reduction, and will not cause the recipe to be rotten. See the cooking page for more information.

=== Condiments & spices ===
Some ingredients can only be added to a recipe that has already been started.
* Condiments & spices like [[salt]], [[pepper]], [[ketchup]], [[mustard]], [[marinara]], [[mayonnaise]], etc. can be used as condiments & spices to enhance a recipe. Each condiment & spice can only be added once per recipe. They do not count towards the number of ingredients. They need to be added before cooking.

=== Pre-cooked ingredients ===
Cooking certain ingredients before adding them to a recipe allows them to be used in [[salad]]s or [[sandwich]]es where they could not be used raw:
* [[Bacon]], [[Bacon Strips|bacon strips]], [[Bacon Bits|bacon bits]], [[Chicken Leg|chicken]], [[Fish Fillet|fish fillet]], [[Mutton Chop|mutton chop]], [[Pork Chop|pork chop]], [[Rabbit Meat|rabbit meat]], [[salmon]], [[Rodent Meat|rodent meat]], and [[Small Bird Meat|small bird meat]] can all be used if cooked first.
* Any raw ingredient that can be used in a recipe can also be used in that recipe as a cooked ingredient.

== Recipes ==
The following table contains each evolved recipe currently in the games files, along with their starting item. Each recipe has its own article with more information.

{| class="wikitable theme-red sortable" style="text-align: center;"
! Recipe name
! Description
! Starting item(s)
! Product
|-
| Soup
| Prepare Soup
| [[File:Pot_Water.png|link=Cooking Pot]]<br>[[Cooking Pot|Cooking Pot with Water]]
| [[File:PotFull.png|link=Soup]]<br>[[Soup]]
|-
| Stew
| Prepare Stew
| [[File:Pot_Water.png|link=Cooking Pot]]<br>[[Cooking Pot|Cooking Pot with Water]]
| [[File:PotFull.png|link=Stew]]<br>[[Stew]]
|-
| Bread
| Prepare Bread
| [[File:Dough.png|link=Bread (dough)]]<br>[[Bread (dough)]]
| [[File:Bread.png|link=Bread (crafted)]]<br>[[Bread (crafted)]]
|-
| Sandwich Baguette
| Make Sandwich
| [[File:Baguette.png|link=Baguette]]<br>[[Baguette]]
| [[File:BaguetteSandwich.png|link=Sandwich (baguette)]]<br>[[Sandwich (baguette)]]
|-
| Sandwich
| Make Sandwich
| [[File:BreadSlices.png|link=Bread Slices]]<br>[[Bread Slices]]
| [[File:Sandwich.png|link=Sandwich (bread)]]<br>[[Sandwich (bread)]]
|-
| Burger
| Prepare Burger
| [[File:BreadSlices.png|link=Bread Slices]]<br>[[Bread Slices]]
| [[File:Burger.png|link=Burger (crafted)]]<br>[[Burger (crafted)]]
|-
| Burrito
| Burrito
| [[File:Tortilla.png|link=Tortilla]]<br>[[Tortilla]]
| [[File:Burrito.png|link=Burrito (crafted)]]<br>[[Burrito (crafted)]]
|-
| Cake
| Prepare Cake
| [[File:Cake.png|link=Cake Preparation]]<br>[[Cake Preparation]]
| [[File:Cake.png|link=Cake (Crafted)]]<br>[[Cake (Crafted)]]
|-
| Muffin
| Muffin
| [[File:Muffintray_Batter.png|link=Muffin]]<br>[[Muffin]]
| [[File:Muffintray_Batter.png|link=Muffin (crafted)]]<br>[[Muffin (crafted)]]
|-
| Omelette
| Omelette
| [[File:PanFull.png|link=Omelette]]<br>[[Omelette]]
| [[File:PanFull.png|link=Omelette (crafted)]]<br>[[Omelette (crafted)]]
|-
| Pancakes
| Pancakes
| [[File:Pancakes.png|link=Pancakes]]<br>[[Pancakes]]
| [[File:PancakesFruit.png|link=Pancakes (crafted)]]<br>[[Pancakes (crafted)]]
|-
| Oatmeal
| Oatmeal
| [[File:Oatmeal.png|link=Bowl of Oatmeal]]<br>[[Bowl of Oatmeal]]
| [[File:Oatmeal.png|link=Bowl of Oatmeal]]<br>[[Bowl of Oatmeal]]
|-
| PastaPan
| Prepare Pasta
| [[File:SaucepanFilled.png|link=Saucepan]]<br>[[Saucepan|Saucepan with Water]]<br><small>AND</small><br>[[File:SpagettiRaw.png|link=Pasta]]<br>[[Pasta]]
| [[File:SaucepanFilled.png|link=Pasta (crafted pan)]]<br>[[Pasta (crafted pan)]]
|-
| PastaPot
| Prepare Pasta
| [[File:Pot_Water.png|link=Cooking Pot]]<br>[[Cooking Pot|Cooking Pot with Water]]<br><small>AND</small><br>[[File:SpagettiRaw.png|link=Pasta]]<br>[[Pasta]]
| [[File:PotFull.png|link=Pasta (crafted pot)]]<br>[[Pasta (crafted pot)]]
|-
| RicePan
| Prepare Rice
| [[File:SaucepanFilled.png|link=Saucepan]]<br>[[Saucepan|Saucepan with Water]]<br><small>AND</small><br>[[File:RiceRaw.png|link=Rice]]<br>[[Rice]]
| [[File:SaucepanFilled.png|link=Rice (crafted pan)]]<br>[[Rice (crafted pan)]]
|-
| RicePot
| Prepare Rice
| [[File:Pot_Water.png|link=Cooking Pot]]<br>[[Cooking Pot|Cooking Pot with Water]]<br><small>AND</small><br>[[File:RiceRaw.png|link=Rice]]<br>[[Rice]]
| [[File:PotFull.png|link=Rice (crafted pot)]]<br>[[Rice (crafted pot)]]
|-
| Pie
| Prepare Pie
| [[File:PieWhole.png|link=Pie Preparation]]<br>[[Pie Preparation]]
| [[File:PieWhole.png|link=Pie (savory)]]<br>[[Pie (savory)]]
|-
| PieSweet
| Prepare Sweet Pie
| [[File:PieWhole.png|link=Pie Preparation]]<br>[[Pie Preparation]]
| [[File:PieWhole.png|link=Pie (sweet)]]<br>[[Pie (sweet)]]
|-
| Pizza
| Prepare Pizza
| [[File:PizzaWhole.png|link=Pizza]]<br>[[Pizza]]
| [[File:PizzaWhole.png|link=Pizza (crafted)]]<br>[[Pizza (crafted)]]
|-
| Roasted Vegetables
| Place Ingredients in Roasting Pan
| [[File:Roastingpan.png|link=Roasting Pan]]<br>[[Roasting Pan]]
| [[File:RoastingpanFull.png|link=Roasted Vegetables]]<br>[[Roasted Vegetables]]
|-
| Stir fry Griddle Pan
| Prepare Stir-fry
| [[File:Griddle.png|link=Griddle Pan]]<br>[[Griddle Pan]]
| [[File:PanFull.png|link=Stir Fry (griddle)]]<br>[[Stir Fry (griddle)]]
|-
| Stir fry
| Prepare Stir-fry
| [[File:Pan.png|link=Frying Pan]]<br>[[Frying Pan]]
| [[File:PanFull.png|link=Stir Fry (pan)]]<br>[[Stir Fry (pan)]]
|-
| Salad
| Make Salad
| [[File:Bowl.png|link=Bowl]]<br>[[Bowl|Empty Bowl]]
| [[File:TZ_CraftSalat.png|link=Salad]]<br>[[Salad]]
|-
| FruitSalad
| Make Fruit Salad
| [[File:Bowl.png|link=Bowl]]<br>[[Bowl|Empty Bowl]]
| [[File:FruitSalad.png|link=Fruit Salad]]<br>[[Fruit Salad]]
|-
| Taco
| Taco
| [[File:TacoShell.png|link=Taco Shell]]<br>[[Taco Shell]]
| [[File:Taco.png|link=Taco (crafted)]]<br>[[Taco (crafted)]]
|-
| Toast
| Prepare Toast
| [[File:Toast.png|link=Toast]]<br>[[Toast]]
| [[File:BreadSlices.png|link=Toast]]<br>[[Toast]]
|-
| Waffles
| Waffles
| [[File:Waffles.png|link=Waffles]]<br>[[Waffles]]
| [[File:SafflesFruit.png|link=Waffles (crafted)]]<br>[[Waffles (crafted)]]
|-
| ConeIcecream
| Prepare Ice Cream Cone
| [[File:ConeIcecream.png|link=Ice Cream Cone]]<br>[[Ice Cream Cone]]
| [[File:ConeIceCreamTopped.png|link=Ice Cream Cone (crafted)]]<br>[[Ice Cream Cone (crafted)]]
|-
| Beer2
| Pour Cup of Beer
| [[File:PlasticCup.png|link=Plastic Cup]]<br>[[Plastic Cup]]
| [[File:PlasticCup.png|link=Beer in a Cup]]<br>[[Beer in a Cup]]
|-
| Beer
| Pour Tumbler of Beer
| [[File:GlassTumbler.png|link=Tumbler]]<br>[[Tumbler]]
| [[File:GlassTumbler.png|link=Beer in a Tumbler]]<br>[[Beer in a Tumbler]]
|-
| HotDrink<br>HotDrinkRed<br>HotDrinkWhite<br>HotDrinkSpiffo
| Prepare Beverage
| <span class="cycle-img">[[File:Mugl.png|link=Mug]][[File:MugRed.png|link=Mug]][[File:MugWhite.png|link=Mug]][[File:MugSpiffo.png|link=Mug]]</span><br>[[Mug|Mug of Water]]
| <span class="cycle-img">[[File:MugFulll.png|link=Beverage (mug)]][[File:MugRedFull.png|link=Beverage (mug)]][[File:MugWhiteFull.png|link=Beverage (mug)]][[File:MugSpiffoFull.png|link=Beverage (mug)]]</span><br>[[Beverage (mug)]]
|-
| HotDrinkTea
| Prepare Beverage
| <span class="cycle-img">[[File:GlassTumbler.png|link=Tumbler]][[File:Teacup.png|link=Teacup]][[File:PlasticCup.png|link=Plastic Cup]][[File:Mugl.png|link=Mug]][[File:MugRed.png|link=Mug]][[File:MugWhite.png|link=Mug]][[File:MugSpiffo.png|link=Mug]]</span><br>[[Mug|Mug of Water]]
| [[File:Teacup.png|link=Hot Teacup]]<br>[[Hot Teacup]]
|-
| Beverage2
| Prepare Beverage in Cup
| [[File:PlasticCup.png|link=Plastic Cup]]<br>[[Plastic Cup]]
| [[File:PlasticCup.png|link=Beverage (cup)]]<br>[[Beverage (cup)]]
|-
| Beverage
| Prepare Beverage in Tumbler
| [[File:GlassTumbler.png|link=Tumbler]]<br>[[Tumbler]]
| [[File:GlassTumbler.png|link=Beverage (tumbler)]]<br>[[Beverage (tumbler)]]
|-
| WineInGlass
| Pour Glass of Wine
| [[File:GlassWine.png|link=Wine Glass]]<br>[[Wine Glass]]
| [[File:GlassWine.png|link=Wine in a Glass]]<br>[[Wine in a Glass]]
|}

== Ingredient values ==
This table includes every ingredients hunger value for each recipe. To see ingredients in a specific recipe it is recommended to view that recipe's article. Ingredients are sorted alphabetically by default.

{{:Evolved recipes/Ingredients}}

== Gallery ==
<gallery>
File:TZ_MixedSaladPrep.png|Old icon of salad ingredients
File:TZ_MixedSaladPrepRotten.png|Old icon of salad ingredients, rotten
File:TZ_PotatosaladPrep.png|Old icon of potato salad ingredients
File:TZ_PotatosaladPrepRotten.png|Old icon of potato salad ingredients, rotten
File:TZ_PotatosaladPrepVegi.png|Old icon of potato salad vegetable ingredients
File:TZ_PotatosaladPrepVegiRotten.png|Old icon of potato salad vegetable ingredients, rotten
</gallery>

== See also ==
* {{ll|Evolved recipes/Ingredients}}
* {{ll|Cooking}}
* {{ll|Nutrition}}
* {{ll|Nutritional values}}

== Navigation ==
{{Navbox items|food}}

{{ll|Category:Evolved recipes}}
{{ll|Category:Guides}}
```
