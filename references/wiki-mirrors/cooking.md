# Wiki mirror — Cooking

**Source:** https://pzwiki.net/wiki/Cooking
**Fetched:** 2026-09-09
**Wiki page version:** 42.18.0
**License:** CC BY-NC-SA 3.0 — attribution: PZwiki contributors

## Digest

- The Cooking skill: what each level buys in evolved recipes, poison detect/hide thresholds, XP sources, and the ingredient-consumption mechanic. Stamped 42.18.0.
- Per-level table: ingredient consumed falls 100% -> 70% (3 points a level) while nutrition added per ingredient rises 100% -> 117%, because a flat +6.66%/level is applied after the consumption cut — the page notes level 10 lands slightly below level 9.
- Rotten ingredients are locked until cooking 7, then allowed at 5% (levels 7-8) and 10% (levels 9-10); each level also shaves 0.05 s off adding an ingredient.
- Poisoning: recipes with three or more ingredients can be spiked (bleach and friends); the level needed to detect runs 3 against a level-0 poisoner up to 10 against level 7+.
- Ingredient accounting, worked on the page: a fresh potato holds 18 hunger points, gives 9 to a salad and loses 9 at cooking 0; at cooking 10 it gives 10.5 and loses 6.3. An evolved recipe inherits the age of its base ingredient only.
- "Increases nutrition of evolved recipes" is the claim most likely to mislead us: 01-notes.md Q1/Q2 show `Eat` reads calories and macros as bare fields with no skill term anywhere, so any cooking-skill effect must be baked into the crafted item at recipe-build time — verify against `EvolvedRecipe` / `ISAddItemInRecipe` before assuming calories scale with skill at all.
- Silent on the plain item-state modifiers (`getHungerChange` x1.3 cooked, `getThirstChange` /2 cooked and /5 burnt) — those are item state, not skill, and belong to the Food mirror.

## Wikitext

```wikitext
{{LangSwitch}}
{{Navbar player}}
{{Page version|42.18.0}}
{{Infobox skill
|name=Cooking
|icon=PanFull.png
|type=Crafting
|modifies=Increases nutrition of evolved recipes, decreases ingredient consumption by evolved recipes, poison detection
|skill_id=Cooking
}}
{{About|the [[skill]]|an [[item]] category|Cooking (item)|the [[crafting]] recipes|Cooking (crafting)}}
{{Quote|text=Allows the creation of more nutritious and delicious food.|author=In-game tooltip.}}
'''Cooking''' is a crafting [[skill]].

== Overview ==
Cooking allows the character to make the most out of [[food]] items when used as [[Evolved recipes|ingredients]].

== Effects ==
Each level of cooking skill increases the amount of nutrition each ingredient provides and reduces the amount of ingredient that is used. At level 7, the player can safely use small amounts of rotten food in their recipes.

{| class="wikitable theme-red"
|-
! Cooking level
| 0 || 1 || 2 || 3 || 4 || 5 || 6 || 7 || 8 || 9 || 10
|-
! Amount of ingredient used<ref name=":0">The base amount of an ingredient used is set per recipe. This is a modifier to that per-recipe value.</ref>
| 100% || 97% || 94% || 91% || 88% || 85% || 82% || 79% || 76% || 73% || 70%
|-
! Nutrition added per ingredient<ref name=":1">Each level increases nutrition added by 6.66%, but this is applied after the amount of the ingredient used is reduced, so the final value (displayed in the table) is much lower and has greatly diminishing returns.</ref>
| 100% || 103% || 107% || 109% || 111% || 113% || 115% || 116% || 117% || 117% || 117%<ref>The diminishing returns are so extreme that this is actually slightly lower than level 9.</ref>
|-
! Amount of rotten ingredient used
| colspan = 7 | Cannot use rotten food || colspan = 2 | 5% || colspan = 2 | 10%
|}
Each level of cooking skill also reduces the time it takes to add ingredients by a miniscule 0.05 seconds.

Evolved recipes with three or more ingredients can be poisoned with [[bleach]] or another poisonous item. A higher cooking level makes it easier for the player to detect poisons, and harder for the player's poisons to be detected. Food that has been detected as poisonous is marked with an icon [[File:SkullPoison.png]].
{| class="wikitable theme-red"
|-
! Poisoner's cooking level
| 0 || 1 || 2 || 3 || 4 || 5 || 6 || 7 || 8 || 9 || 10
|-
! Level required to detect poison
| 3 || 4 || 5 || 6 || 7 || 8 || 9 || colspan = 4 | 10
|}

== Leveling ==
Cooking experience is gained when cooking food in a [[heat source]], when crafting [[Cooking (crafting)#Recipes|cooking recipes]], and when adding ingredients to [[evolved recipes]].

=== Occupations ===
The following [[occupation]]s determine a character's initial skill levels.
* [[File:profession_burgerflipper.png]] [[Burger Flipper]] (+2)
* [[File:profession_chef2.png]] [[Chef]] (+4)

=== Traits ===
The following [[trait]] determine a character's initial skill levels.
{{Note|While the [[Keen Cook (occupation trait)]] does not affect cooking directly, the related [[occupation]]s do.}}
* [[File:trait_cook.png]] [[Keen Cook]] (+2)

The following traits determine an XP rate of the skill. These have no effect on starting level.
* [[File:trait_crafty.png]] [[Crafty]] increases the XP rate to 130%.
* [[File:trait_fastlearner.png]] [[Fast Learner]] increases the XP rate to 130%.
* [[File:trait_slowlearner.png]] [[Slow Learner]] lowers the XP rate to 70%.

=== Skill books ===
To (further) increase the multiplier for experience gain, the following [[skill book]]s can be read.
* [[File:Book9.png]] [[Cooking I: "Better Burger Flipping"]] (Levels 1-2)
* [[File:Book9.png]] [[Cooking II: "Essential Home Cooking Guide"]] (Levels 3-4)
* [[File:Book9.png]] [[Cooking III: "Flavorful Cuisine - 1993 Edition"]] (Levels 5-6)
* [[File:Book9.png]] [[Cooking IV: "Professional Tips from a Master Chef"]] (Levels 7-8)
* [[File:Book9.png]] [[Cooking V: "Ruban Vert Gourmet - Complete Cooking Techniques"]] (Levels 9-10)

=== Recipe resources ===
To learn relevant recipes if a character did not start with the [[Burger Flipper|burger flipper]], or [[chef]] [[occupation]] or have taken the [[Keen Cook|keen cook]] [[trait]], the following [[recipe magazine]]s can be read.
* [[File:MagazineFood6.png]] [[Magazine: Delicious Meals - June 1993]]
* [[File:MagazineFood.png]] [[Magazine: Good Cooking - June 1993]]
* [[File:MagazineFood2.png]] [[Magazine: Good Cooking - May 1993]]
* [[File:MagazineFood4.png]] [[Magazine: Grandma's Kitchen]]
* [[File:MagazineFood3.png]] [[Magazine: Italian Delights]]
* [[File:MagazineFood5.png]] [[Magazine: World Cooking]]

=== Entertainment ===
Entertainment gains are limited to the first 3 levels and any overflowing XP amount.

==== Life and Living TV ====
The following [[Life and Living TV]] shows give cooking XP.
* [[File:Television.png]] The Cook Show Day 1, 6:00 AM: +112.5
* [[File:Television.png]] The Cook Show Day 2, 6:00 AM: +75
* [[File:Television.png]] The Cook Show Day 3, 6:00 AM: +62.5
* [[File:Television.png]] The Cook Show Day 4, 6:00 AM: +87.5
* [[File:Television.png]] The Cook Show Day 5, 6:00 AM: +75
* [[File:Television.png]] The Cook Show Day 6, 6:00 AM: +62.5
* [[File:Television.png]] The Cook Show Day 7, 6:00 AM: +87.5
* [[File:Television.png]] The Cook Show Day 8, 6:00 AM: +125
* [[File:Television.png]] The Cook Show Day 9, 6:00 AM: +75

==== VHS ====
The following [[VHS]] tapes give cooking XP.
* [[File:Cassette3.png]] [[Making Sushi at Home]]: +62.5
* [[File:Cassette3.png]] [[The Cook Show E1|The Cook Show Episode 1: Cake]]: +75
* [[File:Cassette3.png]] [[The Cook Show E2|The Cook Show Episode 2: Soup]]: +100
* [[File:Cassette3.png]] [[The Cook Show E3|The Cook Show Episode 3: Stew]]: +62.5
* [[File:Cassette3.png]] [[The Cook Show E4|The Cook Show Episode 4: Salads]]: +50
* [[File:Cassette3.png]] [[The Cook Show E5|The Cook Show Episode 5: Stir-Fry]]: +50
* [[File:Cassette3.png]] [[The Cook Show E6|The Cook Show Episode 6: Sandwiches]]: +62.5
* [[File:Cassette3.png]] [[The Cook Show E7|The Cook Show Episode 7: Pie]]: +75

== Mechanics ==
Cooking can be initiated from the context menu for a cooking vessel or base ingredient. If the player has at least one ingredient valid for that recipe, they will be able to add it to start cooking. Further ingredients can be added from the same menu, to a limit defined per recipe. Food cooked this way benefits from an unhappiness reduction, increased nutrition, and reduced overall food usage. Spices can be added for a boredom reduction and a stronger unhappiness reduction.

[[Evolved recipes]] crafted from a base ingredient (such as the [[Bread Slices|bread]] in a [[Evolved recipes#Recipes|sandwich]]) will inherit the age of the base ingredient. This means that base ingredients that have gone stale will result in a stale food item. However, the age of any other ingredients does not have any effect on the final food (so long as they have not gone rotten), so it can be very efficient to prioritize use of stale food in recipes before they rot.

The [[hunger]] reduction of an evolved recipe depends on the ingredient(s) used and the cooking skill level it was created at. For example, in a [[soup]], a [[potato]] provides 15 hunger reduction, while a [[cabbage]] only provides 10. The hunger reduction an ingredient provides is also affected by the recipe itself and by the cooking skill as well. While [[Beef Jerky|beef jerky]] can provide 15 hunger reduction to a [[stew]], it can only provide 5 hunger reduction to a [[Sandwich (bread)|sandwich]]. The amount of hunger reduction granted will be shown in the menu when hovering over an ingredient to add.

As a result, some ingredients will not be fully used when added to a recipe, with a portion remaining in the player's inventory. Hunger reduction points vary not only by the original recipe but also by item. The amount of hunger reduction removed from the original food scales inversely with cooking level – less hunger points are subtracted from the ingredient<ref name=":0" /> as cooking skill increases – all the while, the hunger points provided to the recipe increase proportionally. This thereby allows cooking ingredients to be used more efficiently, albeit with severely diminishing returns<ref name=":1" />.

For example, a [[potato]] has a base of 18 hunger reduction points when fresh and uncooked. If used in a [[salad]], that potato provides 9 hunger reduction to that salad. Subsequently, 9 points of hunger reduction are subtracted from the original potato. Assuming it is fresh and uncooked, and assuming you are at cooking level 0, a single potato can be used twice in a salad before being completely used up. At cooking level 10, only 6.3 hunger points would be subtracted from the original potato, while it would provide 10.5 hunger points as a cooking ingredient.

== Crafting ==
{{Main|Cooking (crafting)}}
{{Crafting|ID=Cooking_crafting
|CutChicken
|CutTurkey
|MakeBaguetteDough
|MakeBiscuits
|MakeBowlOfBeans
|MakeBowlOfCereal
|MakeBowlOfOatmeal
|MakeBreadDough
|MakeCakeBatter
|MakeChocolateChipCookieDough
|MakeChocolateCookieDough
|MakeFriedOnionRings
|MakeFriedShrimp
|MakeGravy
|MakeHalloweenPumpkin
|MakeJar
|MakeMaki
|MakeMeatPatty
|MakeOatmealCookieDough
|MakeOnigiri
|MakePancake
|MakePieDough
|MakePizza
|MakeShortbreadCookieDough
|MakeSquidCalamari
|MakeSugarCookieDough
|MakeSushi
|PlaceCakeInBakingPan
|PlacePieInBakingPan
|PrepareMuffins
|PrepareOmelette
|ScoopIceCream
|SliceBaloney
|SliceBread
|SliceCakeOrPie
|SliceHam
|SliceHead
|SlicePizza
|SliceSalami
|SliceWatermelon
}}

== See also ==
* {{ll|Heat source}}
* {{ll|Evolved recipes}}

== References ==
<references />

== Navigation ==
{{Navbox stats|skills}}

{{ll|Category:Crafting skills}}
{{ll|Category:Skills}}
```
