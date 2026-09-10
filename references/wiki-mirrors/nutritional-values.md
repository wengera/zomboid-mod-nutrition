# Wiki mirror — Nutritional values

**Source:** https://pzwiki.net/wiki/Nutritional_values
**Fetched:** 2026-09-09
**Wiki page version:** 42.20.0
**License:** CC BY-NC-SA 3.0 — attribution: PZwiki contributors

## Digest

- Bot-generated lookup table — encumbrance, hunger, calories, carbohydrates, proteins, fat and item ID for every food. Stamped 42.20.0; no prose beyond the legend, so it is a data cross-check, not a mechanics source.
- Spot-check holds: Apple reads hunger -16, 95 kcal, 25.13 carbs, 0.47 protein, 0.31 fat, `Base.Apple` — the same numbers `docs/superpowers/plans/01-notes.md` reads from `media/scripts/generated/items/food.txt:8658`.
- Mixes two conventions in one row: hunger is the raw script value, but `Item.InstanceItem` divides `HungerChange` by 100 before storing it (-16 -> -0.16), while calories and the three macros are stored unscaled — use the hunger column for identity, not arithmetic.
- Rows are per item and state-free. Right for the macros (`Food.getCalories` and siblings are bare getfields; no cooked/burnt/rotten/frozen modifier exists) but wrong for hunger, which `Food.getHungerChange` scales x1.3 cooked, /3 burnt, /2.2 rotten — verify against `zombie.inventory.types.Food` (01-notes.md Q2).
- Column is labelled "Fat" while the script key and the Java field are `Lipids`; keep that mapping explicit when we generate our own dataset in P4.
- No per-row provenance or generation date, so treat any single row as W-grade until matched against `food.txt`.

## Wikitext

```wikitext
{{LangSwitch}}
{{Navbar game mechanics}}
{{Page version|42.20.0}}
This page contains a list of '''nutritional values''' for all [[food]] in [[Project Zomboid]].
__TOC__

== Legend ==
{{Legend nutrition}}

== List of nutritional values ==
<!-- Bot_flag|type=food_item_list|id=nutrition --><div class="scroll-x">
{| class="wikitable theme-red sortable sticky-column" style="text-align: center;"
! Icon
! Name
! [[File:Status_HeavyLoad_32.png|link=|Encumbrance]]
! [[File:Status_Hunger_32.png|link=|Hunger]]
! [[File:Fire_01_1.png|32px|link=|Calories]]
! [[File:Wheat.png|32px|link=|Carbohydrates]]
! [[File:Steak.png|32px|link=|Proteins]]
! [[File:Butter.png|32px|link=|Fat]]
! Item ID
|-
| [[File:Acorn.png|32x32px|link=Acorn|Acorn]]
| [[Acorn]]
| 0.1
| -10
| 55
| 12
| 6
| 24
| Base.Acorn
|-
| [[File:Fish_GarAlligator.png|32x32px|link=Alligator Gar|Alligator Gar]]
| [[Alligator Gar]]
| 0.4
| -15
| 159
| 1
| 35
| 1
| Base.AligatorGar
|-
| <span class="cycle-img">[[File:Apple.png|32x32px|link=Apple|Apple]][[File:AppleRotten.png|32x32px|link=Apple|Apple]]</span>
| [[Apple]]
| 0.2
| -16
| 95
| 25.13
| 0.47
| 0.31
| Base.Apple
|-
| [[File:Pie_Apple.png|32x32px|link=Apple Pie Slice|Apple Pie Slice]]
| [[Apple Pie Slice]]
| 0.5
| -30
| 404
| 20.45
| 54.53
| 20.61
| Base.PieApple
|-
| [[File:DriedApricots.png|32x32px|link=Apricots (Dried)|Apricots (Dried)]]
| [[Apricots (Dried)]]
| 0.2
| -16
| 241
| 62.6
| 3.4
| 0.5
| Base.DriedApricots
|-
| <span class="cycle-img">[[File:Avocado.png|32x32px|link=Avocado|Avocado]][[File:AvocadoRotten.png|32x32px|link=Avocado|Avocado]]</span>
| [[Avocado]]
| 0.3
| -16
| 227
| 11.75
| 2.67
| 20.96
| Base.Avocado
|-
| <span class="cycle-img">[[File:Bacon.png|32x32px|link=Bacon|Bacon]][[File:BaconRotten.png|32x32px|link=Bacon|Bacon]][[File:BaconCooked.png|32x32px|link=Bacon|Bacon]][[File:BaconBurnt.png|32x32px|link=Bacon|Bacon]]</span>
| [[Bacon]]
| 0.3
| -12
| 160
| -
| 10
| 14
| Base.Bacon
|-
| <span class="cycle-img">[[File:TZ_BaconBits.png|32x32px|link=Bacon Bits|Bacon Bits]][[File:TZ_BaconBitsRotten.png|32x32px|link=Bacon Bits|Bacon Bits]][[File:TZ_BaconBitsCooked.png|32x32px|link=Bacon Bits|Bacon Bits]][[File:TZ_BaconBitsOverdone.png|32x32px|link=Bacon Bits|Bacon Bits]]</span>
| [[Bacon Bits]]
| 0.025
| -1
| 10
| -
| 0.6125
| 0.875
| Base.BaconBits
|-
| <span class="cycle-img">[[File:TZ_BaconRashers.png|32x32px|link=Bacon Strip|Bacon Strip]][[File:TZ_BaconRashersRotten.png|32x32px|link=Bacon Strip|Bacon Strip]][[File:TZ_BaconRashersCooked.png|32x32px|link=Bacon Strip|Bacon Strip]][[File:TZ_BaconRashersOverdone.png|32x32px|link=Bacon Strip|Bacon Strip]]</span>
| [[Bacon Strip]]
| 0.1
| -4
| 40
| -
| 2.5
| 3.5
| Base.BaconRashers
|-
| [[File:BagelPlain.png|32x32px|link=Bagel|Bagel]]
| [[Bagel]]
| 0.1
| -10
| 177
| 33
| 5.9
| 2.22
| Base.BagelPlain
|-
| [[File:Baguette.png|32x32px|link=Baguette|Baguette]]
| [[Baguette]]
| 0.3
| -23
| 532
| 99
| 17.7
| 6.66
| Base.Baguette
|-
| [[File:Doughnut_Baguette.png|32x32px|link=Baguette|Baguette]]
| [[Baguette]]
| 0.3
| -15
| 532
| 99
| 17.7
| 6.66
| Base.BaguetteDough
|-
| [[File:BakingTray_CookiesBaked.png|32x32px|link=Chocolate Chip Cookie|Baking Tray with Chocolate Chip Cookies]]
| [[Chocolate Chip Cookie|Baking Tray with Chocolate Chip Cookies]]
| 1.9
| -23
| 960
| 132
| 1
| 48
| Base.CookieChocolateChipDough
|-
| [[File:BakingTray_CookiesBaked.png|32x32px|link=Chocolate Cookie|Baking Tray with Chocolate Cookies]]
| [[Chocolate Cookie|Baking Tray with Chocolate Cookies]]
| 1.9
| -23
| 1020
| 150
| 12
| 54
| Base.CookiesChocolateDough
|-
| [[File:BakingTray_CookiesBaked.png|32x32px|link=Oatmeal Cookie|Baking Tray with Oatmeal Cookies]]
| [[Oatmeal Cookie|Baking Tray with Oatmeal Cookies]]
| 1.9
| -23
| 660
| 120
| 6
| 36
| Base.CookiesOatmealDough
|-
| [[File:BakingTray_CookiesBaked.png|32x32px|link=Shortbread Cookie|Baking Tray with Shortbread Cookies]]
| [[Shortbread Cookie|Baking Tray with Shortbread Cookies]]
| 1.9
| -23
| 720
| 132
| 12
| 48
| Base.CookiesShortbreadDough
|-
| [[File:BakingTray_CookiesBaked.png|32x32px|link=Sugar Cookie|Baking Tray with Sugar Cookies]]
| [[Sugar Cookie|Baking Tray with Sugar Cookies]]
| 1.9
| -23
| 720
| 132
| 12
| 48
| Base.CookiesSugarDough
|-
| [[File:Baloney.png|32x32px|link=Baloney|Baloney]]
| [[Baloney]]
| 0.2
| -30
| 200
| 2
| 22.65
| 6.35
| Base.Baloney
|-
| [[File:BaloneySlices.png|32x32px|link=Baloney Slices|Baloney Slices]]
| [[Baloney Slices]]
| 0.04
| -5
| 33
| 0.33
| 3.78
| 1.06
| Base.BaloneySlice
|-
| [[File:BalsamicVinegar.png|32x32px|link=Balsamic Vinegar|Balsamic Vinegar]]
| [[Balsamic Vinegar]]
| 0.2
| -20
| 1250
| 300
| -
| -
| Base.BalsamicVinegar
|-
| <span class="cycle-img">[[File:Banana.png|32x32px|link=Banana|Banana]][[File:BananaRotten.png|32x32px|link=Banana|Banana]]</span>
| [[Banana]]
| 0.2
| -16
| 105
| 26.95
| 1.29
| 0.39
| Base.Banana
|-
| [[File:BBQSauce.png|32x32px|link=Barbecue Sauce|Barbecue Sauce]]
| [[Barbecue Sauce]]
| 0.2
| -20
| 980
| 252
| -
| -
| Base.BBQSauce
|-
| [[File:FruitSalad.png|32x32px|link=Salad|Base.FruitSaladClay]]
| [[Salad|Base.FruitSaladClay]]
| 0.7
| -60
| 97
| 25
| 1.4
| 0.5
| Base.FruitSaladClay
|-
| [[File:HerbBasil.png|32x32px|link=Basil|Basil]]
| [[Basil]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.Basil
|-
| [[File:Seasoning_Basil.png|32x32px|link=Basil (Dried)|Basil (Dried)]]
| [[Basil (Dried)]]
| 0.2
| -20
| 0.4
| -
| -
| -
| Base.Seasoning_Basil
|-
| [[File:DriedHerbs_generic.png|32x32px|link=Basil (Dried)|Basil (Dried)]]
| [[Basil (Dried)]]
| 0.1
| -5
| 0.1
| -
| -
| -
| Base.BasilDried
|-
| <span class="cycle-img">[[File:BeefLoin.png|32x32px|link=Beef|Beef]][[File:BeefLoinRotten.png|32x32px|link=Beef|Beef]][[File:BeefLoinCooked.png|32x32px|link=Beef|Beef]][[File:BeefLoinOverdone.png|32x32px|link=Beef|Beef]]</span>
| [[Beef]]
| 0.5
| -80
| 440
| -
| 62.62
| 18.7
| Base.Beef
|-
| [[File:BeefJerky.png|32x32px|link=Beef Jerky|Beef Jerky]]
| [[Beef Jerky]]
| 0.2
| -20
| 410
| 11
| 33
| 26
| Base.BeefJerky
|-
| <span class="cycle-img">[[File:MeatPatty.png|32x32px|link=Beef Patty|Beef Patty]][[File:MeatPattyRotten.png|32x32px|link=Beef Patty|Beef Patty]][[File:MeatPattyCooked.png|32x32px|link=Beef Patty|Beef Patty]][[File:MeatPattyBurnt.png|32x32px|link=Beef Patty|Beef Patty]]</span>
| [[Beef Patty]]
| 0.3
| -40
| 612
| -
| 46
| 30
| Base.MeatPatty
|-
| <span class="cycle-img">[[File:BellPepper.png|32x32px|link=Bell Pepper|Bell Pepper]][[File:BellPepperRotten.png|32x32px|link=Bell Pepper|Bell Pepper]]</span>
| [[Bell Pepper]]
| 0.2
| -8
| 30
| 7
| 1
| -
| Base.BellPepper
|-
| [[File:BeautyBerries.png|32x32px|link=Berries (beautyberry)|Berries]]
| [[Berries (beautyberry)|Berries]]
| 0.1
| -10
| 23
| 5
| 4
| -
| Base.BeautyBerry
|-
| [[File:HollyBerries.png|32x32px|link=Berries (holly berry)|Berries]]
| [[Berries (holly berry)|Berries]]
| 0.1
| -10
| 23
| 5
| 4
| -
| Base.HollyBerry
|-
| [[File:Winterberries.png|32x32px|link=Berries (winterberry)|Berries]]
| [[Berries (winterberry)|Berries]]
| 0.1
| -10
| 23
| 5
| 4
| -
| Base.WinterBerry
|-
| <span class="cycle-img">[[File:BerryBlack.png|32x32px|link=Berries|Berries]][[File:BerryBlackRotten.png|32x32px|link=Berries|Berries]]</span>
| [[Berries]]
| 0.1
| -10
| 23
| 5
| 4
| -
| Base.BerryBlack
|-
| <span class="cycle-img">[[File:BerryBlue.png|32x32px|link=Berries|Berries]][[File:BerryBlueRotten.png|32x32px|link=Berries|Berries]]</span>
| [[Berries]]
| 0.1
| -10
| 23
| 5
| 4
| -
| Base.BerryBlue
|-
| <span class="cycle-img">[[File:BerryGeneric1.png|32x32px|link=Berries|Berries]][[File:BerryGeneric1Rotten.png|32x32px|link=Berries|Berries]]</span>
| [[Berries]]
| 0.1
| -5
| 12
| 3
| 2
| -
| Base.BerryGeneric1
|-
| <span class="cycle-img">[[File:BerryGeneric2.png|32x32px|link=Berries|Berries]][[File:BerryGeneric2Rotten.png|32x32px|link=Berries|Berries]]</span>
| [[Berries]]
| 0.1
| -10
| 23
| 5
| 4
| -
| Base.BerryGeneric2
|-
| <span class="cycle-img">[[File:BerryGeneric3.png|32x32px|link=Berries|Berries]][[File:BerryGeneric3Rotten.png|32x32px|link=Berries|Berries]]</span>
| [[Berries]]
| 0.1
| -5
| 8
| 3
| 2
| -
| Base.BerryGeneric3
|-
| <span class="cycle-img">[[File:BerryGeneric4.png|32x32px|link=Berries|Berries]][[File:BerryGeneric4Rotten.png|32x32px|link=Berries|Berries]]</span>
| [[Berries]]
| 0.1
| -10
| 23
| 5
| 4
| -
| Base.BerryGeneric4
|-
| <span class="cycle-img">[[File:BerryGeneric5.png|32x32px|link=Berries|Berries]][[File:BerryGeneric5Rotten.png|32x32px|link=Berries|Berries]]</span>
| [[Berries]]
| 0.1
| -10
| 23
| 5
| 4
| -
| Base.BerryGeneric5
|-
| [[File:BerryPoisonIvy.png|32x32px|link=Berries|Berries]]
| [[Berries]]
| 0.1
| -5
| 23
| 5
| 4
| -
| Base.BerryPoisonIvy
|-
| [[File:Biscuit.png|32x32px|link=Biscuit|Biscuit]]
| [[Biscuit]]
| 0.1
| -5
| 160
| 22
| 1
| 8
| Base.Biscuit
|-
| [[File:Muffintray_Batter.png|32x32px|link=Muffin Tray with Biscuits|Biscuits]]
| [[Muffin Tray with Biscuits|Biscuits]]
| 1.5
| -23
| 960
| 132
| 6
| 48
| Base.Muffintray_Biscuit
|-
| [[File:Blackbeans.png|32x32px|link=Black Beans|Black Beans]]
| [[Black Beans]]
| 0.1
| -10
| 45
| 10.45
| 3.95
| 0.45
| Base.Blackbeans
|-
| [[File:DriedBlackBeans.png|32x32px|link=Black Beans (Dried)|Black Beans (Dried)]]
| [[Black Beans (Dried)]]
| 2
| -60
| 3084
| 580
| 199
| -
| Base.DriedBlackBeans
|-
| [[File:Fish_CrappieBlack.png|32x32px|link=Black Crappie|Black Crappie]]
| [[Black Crappie]]
| 0.4
| -15
| 159
| 1
| 35
| 1
| Base.BlackCrappie
|-
| [[File:CakeBlackForest.png|32x32px|link=Black Forest Cake Slice|Black Forest Cake Slice]]
| [[Black Forest Cake Slice]]
| 0.2
| -10
| 90
| 4
| 10
| 12
| Base.CakeBlackForest
|-
| <span class="cycle-img">[[File:BlackSage.png|32x32px|link=Black Sage|Black Sage]][[File:BlackSageRotten.png|32x32px|link=Black Sage|Black Sage]]</span>
| [[Black Sage]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.BlackSage
|-
| [[File:BlackSage_Dried.png|32x32px|link=Black Sage (Dried)|Black Sage (Dried)]]
| [[Black Sage (Dried)]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.BlackSageDried
|-
| [[File:Fish_CatfishBlue.png|32x32px|link=Blue Catfish|Blue Catfish]]
| [[Blue Catfish]]
| 0.4
| -15
| 159
| 1
| 35
| 1
| Base.BlueCatfish
|-
| [[File:Pie_Blueberry.png|32x32px|link=Blueberry Pie Slice|Blueberry Pie Slice]]
| [[Blueberry Pie Slice]]
| 0.5
| -30
| 404
| 20.45
| 54.53
| 20.61
| Base.PieBlueberry
|-
| [[File:Fish_Bluegill.png|32x32px|link=Bluegill|Bluegill]]
| [[Bluegill]]
| 0.4
| -15
| 159
| 1
| 35
| 1
| Base.Bluegill
|-
| [[File:BouillionCube.png|32x32px|link=Bouillon Cube|Bouillon Cube]]
| [[Bouillon Cube]]
| 0.1
| -3
| 16
| 2.3
| 0.6
| 0.5
| Base.BouillonCube
|-
| [[File:BowlFull.png|32x32px|link=Bowl of Beans|Bowl of Beans]]
| [[Bowl of Beans]]
| 1.5
| -24
| 170
| 33
| 7
| 1
| Base.BeanBowl
|-
| [[File:Oatmeal.png|32x32px|link=Bowl of Cereal|Bowl of Cereal]]
| [[Bowl of Cereal]]
| 0.8
| -20
| 295
| 71.5
| 6.5
| 3.25
| Base.CerealBowl
|-
| [[File:NoodleSoup.png|32x32px|link=Bowl of Noodle Soup|Bowl of Noodle Soup]]
| [[Bowl of Noodle Soup]]
| 1
| -10
| 52
| -
| 10
| 14
| Base.NoodleSoup
|-
| [[File:Oatmeal.png|32x32px|link=Bowl of Oatmeal|Bowl of Oatmeal]]
| [[Bowl of Oatmeal]]
| 0.8
| -10
| 300
| 81
| 15
| 9
| Base.Oatmeal
|-
| [[File:FriedRice.png|32x32px|link=Pasta (crafted pot)|Bowl of Pasta]]
| [[Pasta (crafted pot)|Bowl of Pasta]]
| 1
| -12
| 330
| 41
| 24
| 6.5
| Base.PastaBowl
|-
| [[File:FriedRice.png|32x32px|link=Pasta (crafted pot)|Bowl of Pasta]]
| [[Pasta (crafted pot)|Bowl of Pasta]]
| 1
| -12
| 330
| 41
| 24
| 6.5
| Base.PastaBowlClay
|-
| [[File:BowlFull.png|32x32px|link=Bowl of Ramen Noodles|Bowl of Ramen Noodles]]
| [[Bowl of Ramen Noodles]]
| 1
| -10
| 52
| -
| 10
| 14
| Base.RamenBowl
|-
| [[File:FriedRice.png|32x32px|link=Rice (crafted pot)|Bowl of Rice]]
| [[Rice (crafted pot)|Bowl of Rice]]
| 1
| -12
| 160
| 36
| 3
| -
| Base.RiceBowl
|-
| [[File:FriedRice.png|32x32px|link=Rice (crafted pot)|Bowl of Rice]]
| [[Rice (crafted pot)|Bowl of Rice]]
| 1
| -12
| 160
| 36
| 3
| -
| Base.RiceBowlClay
|-
| [[File:BowlFull.png|32x32px|link=Bowl of Soup|Bowl of Soup]]
| [[Bowl of Soup]]
| 1
| -15
| 124
| 15
| 6.3
| 4.7
| Base.SoupBowl
|-
| [[File:BowlFull.png|32x32px|link=Bowl of Soup|Bowl of Soup]]
| [[Bowl of Soup]]
| 1
| -15
| 124
| 15
| 6.3
| 4.7
| Base.SoupBowlClay
|-
| [[File:BowlFull.png|32x32px|link=Stew|Bowl of Stew]]
| [[Stew|Bowl of Stew]]
| 1
| -15
| 250
| 34
| 23
| 3
| Base.StewBowl
|-
| [[File:BowlFull.png|32x32px|link=Stew|Bowl of Stew]]
| [[Stew|Bowl of Stew]]
| 1
| -15
| 250
| 34
| 23
| 3
| Base.StewBowlClay
|-
| [[File:Flax_PasteBowl.png|32x32px|link=Bowl with Seed Paste|Bowl with Seed Paste]]
| [[Bowl with Seed Paste]]
| 0.3
| -30
| 2120
| -
| -
| 130
| Base.SeedPasteBowl
|-
| [[File:Chocolate_Heartbox.png|32x32px|link=Box of Chocolates|Box of Chocolates]]
| [[Box of Chocolates]]
| 0.5
| -40
| 1700
| 220
| 20
| 130
| Base.Chocolate_HeartBox
|-
| <span class="cycle-img">[[File:Bread.png|32x32px|link=Bread|Bread]][[File:BreadRotten.png|32x32px|link=Bread|Bread]]</span>
| [[Bread]]
| 0.3
| -30
| 532
| 99
| 17.7
| 6.66
| Base.Bread
|-
| <span class="cycle-img">[[File:Dough.png|32x32px|link=Bread (dough)|Bread]][[File:DoughRotten.png|32x32px|link=Bread (dough)|Bread]][[File:DoughCooked.png|32x32px|link=Bread (dough)|Bread]][[File:DoughBurnt.png|32x32px|link=Bread (dough)|Bread]]</span>
| [[Bread (dough)|Bread]]
| 0.3
| -24
| 532
| 99
| 17.7
| 6.66
| Base.BreadDough
|-
| <span class="cycle-img">[[File:BreadSlices.png|32x32px|link=Bread Slices|Bread Slices]][[File:BreadSlicesRotten.png|32x32px|link=Bread Slices|Bread Slices]]</span>
| [[Bread Slices]]
| 0.1
| -10
| 177
| 33
| 5.9
| 2.22
| Base.BreadSlices
|-
| <span class="cycle-img">[[File:Broccoli.png|32x32px|link=Broccoli|Broccoli]][[File:BroccoliRotten.png|32x32px|link=Broccoli|Broccoli]]</span>
| [[Broccoli]]
| 0.2
| -9
| 11
| 2
| 0.9
| 0.1
| Base.Broccoli
|-
| [[File:SugarBrown.png|32x32px|link=Brown Sugar|Brown Sugar]]
| [[Brown Sugar]]
| 0.6
| -30
| 337
| 90
| -
| -
| Base.SugarBrown
|-
| <span class="cycle-img">[[File:BrusselSprouts.png|32x32px|link=Brussels Sprouts|Brussels Sprouts]][[File:BrusselSproutsRotten.png|32x32px|link=Brussels Sprouts|Brussels Sprouts]]</span>
| [[Brussels Sprouts]]
| 0.6
| -20
| 119
| 20.45
| 7.95
| 0.85
| Base.BrusselSprouts
|-
| [[File:MetalBucket_Soup.png|32x32px|link=Bucket of Soup|Bucket of Soup]]
| [[Bucket of Soup]]
| 3
| -40
| 202
| 25
| 14
| 4.5
| Base.BucketOfSoup
|-
| [[File:MetalBucket_Soup.png|32x32px|link=Bucket of Stew|Bucket of Stew]]
| [[Bucket of Stew]]
| 3
| -40
| 202
| 25
| 14
| 4.5
| Base.BucketOfStew
|-
| [[File:Burger.png|32x32px|link=Burger|Burger]]
| [[Burger]]
| 0.3
| -25
| 440
| -
| 25
| 37
| Base.Burger
|-
| [[File:Burger.png|32x32px|link=Burger|Burger]]
| [[Burger]]
| 0.3
| -20
| 440
| 30.5
| 25
| 37
| Base.BurgerRecipe
|-
| [[File:Burrito.png|32x32px|link=Burrito|Burrito]]
| [[Burrito]]
| 0.3
| -25
| 500
| 100
| 37
| 34
| Base.Burrito
|-
| [[File:Burrito.png|32x32px|link=Burrito|Burrito]]
| [[Burrito]]
| 0.1
| -5
| 40
| -
| 2
| 2
| Base.BurritoRecipe
|-
| [[File:Butter.png|32x32px|link=Butter|Butter]]
| [[Butter]]
| 0.3
| -24
| 3200
| -
| -
| 352
| Base.Butter
|-
| [[File:Chocolate_Butterchunkers.png|32x32px|link=Butterchunkers Bar|Butterchunkers Bar]]
| [[Butterchunkers Bar]]
| 0.2
| -20
| 230
| 29
| 2
| 12
| Base.Chocolate_Butterchunkers
|-
| <span class="cycle-img">[[File:Cabbage.png|32x32px|link=Cabbage|Cabbage]][[File:CabbageRotten.png|32x32px|link=Cabbage|Cabbage]]</span>
| [[Cabbage]]
| 0.2
| -24
| 180
| 41
| 9
| 0.7
| Base.Cabbage
|-
| [[File:CabbageRoll.png|32x32px|link=Cabbage Roll|Cabbage Roll]]
| [[Cabbage Roll]]
| 0.3
| -20
| 110
| 7
| 5
| 7
| Base.CabbageRoll
|-
| <span class="cycle-img">[[File:Cake.png|32x32px|link=Cake (crafted)|Cake]][[File:CakeCooked.png|32x32px|link=Cake (crafted)|Cake]][[File:CakeOverdone.png|32x32px|link=Cake (crafted)|Cake]]</span>
| [[Cake (crafted)|Cake]]
| 0.5
| -15
| 560
| 9
| 10
| 53
| Base.CakeRaw
|-
| <span class="cycle-img">[[File:Cake.png|32x32px|link=Cake Preparation|Cake Preparation]][[File:CakeCooked.png|32x32px|link=Cake Preparation|Cake Preparation]][[File:CakeOverdone.png|32x32px|link=Cake Preparation|Cake Preparation]]</span>
| [[Cake Preparation]]
| 0.5
| -30
| 800
| 50
| 8
| 48
| Base.CakePrep
|-
| [[File:CakeSlice.png|32x32px|link=Cake Slice|Cake Slice]]
| [[Cake Slice]]
| 0.2
| -7
| 70
| 1
| 5
| 5
| Base.CakeSlice
|-
| [[File:OatsRaw.png|32x32px|link=Can of Oats|Can of Oats]]
| [[Can of Oats]]
| 0.8
| -50
| 1500
| 405
| 75
| 45
| Base.OatsRaw
|-
| [[File:CandiedApple.png|32x32px|link=Candied Apple|Candied Apple]]
| [[Candied Apple]]
| 0.2
| -18
| 250
| 36
| 6
| 9
| Base.CandiedApple
|-
| [[File:CandyFruitSlices.png|32x32px|link=Candied Fruit Slices|Candied Fruit Slices]]
| [[Candied Fruit Slices]]
| 0.1
| -5
| 40
| 10
| -
| 0.5
| Base.CandyFruitSlices
|-
| [[File:Candycane.png|32x32px|link=Candy Cane|Candy Cane]]
| [[Candy Cane]]
| 0.2
| -10
| 16.6
| 4.33
| -
| -
| Base.Candycane
|-
| [[File:CandyCorn.png|32x32px|link=Candy Corn|Candy Corn]]
| [[Candy Corn]]
| 0.2
| -10
| 32
| 14
| -
| -
| Base.CandyCorn
|-
| [[File:CandyPackagei.png|32x32px|link=Candy Package|Candy Package]]
| [[Candy Package]]
| 0.6
| -
| 500
| 125
| -
| 2.5
| Base.CandyPackage
|-
| [[File:Beans.png|32x32px|link=Canned Beans|Canned Beans]]
| [[Canned Beans]]
| 0.8
| -
| 170
| 33
| 7
| 1
| Base.TinnedBeans
|-
| [[File:BeansOpen.png|32x32px|link=Canned Beans|Canned Beans (Open)]]
| [[Canned Beans|Canned Beans (Open)]]
| 0.8
| -24
| 170
| 33
| 7
| 1
| Base.OpenBeans
|-
| [[File:CannedCarrots.png|32x32px|link=Canned Carrots|Canned Carrots]]
| [[Canned Carrots]]
| 0.8
| -
| 10.5
| 28
| -
| -
| Base.CannedCarrots2
|-
| [[File:CannedCarrotsOpen.png|32x32px|link=Canned Carrots|Canned Carrots (Open)]]
| [[Canned Carrots|Canned Carrots (Open)]]
| 0.8
| -12
| 10.5
| 28
| -
| -
| Base.CannedCarrotsOpen
|-
| [[File:CannedChili.png|32x32px|link=Canned Chili|Canned Chili]]
| [[Canned Chili]]
| 0.8
| -
| 260
| 33
| 16
| 7
| Base.CannedChili
|-
| [[File:CannedChiliOpen.png|32x32px|link=Canned Chili|Canned Chili (Open)]]
| [[Canned Chili|Canned Chili (Open)]]
| 0.8
| -16
| 260
| 33
| 16
| 7
| Base.CannedChiliOpen
|-
| [[File:CannedCorn.png|32x32px|link=Canned Corn|Canned Corn]]
| [[Canned Corn]]
| 0.8
| -
| 315
| 70
| 7
| 1.75
| Base.CannedCorn
|-
| [[File:CannedCornOpen.png|32x32px|link=Canned Corn|Canned Corn (Open)]]
| [[Canned Corn|Canned Corn (Open)]]
| 0.8
| -16
| 315
| 70
| 7
| 1.75
| Base.CannedCornOpen
|-
| [[File:CannedCornedBeef.png|32x32px|link=Canned Corned Beef|Canned Corned Beef]]
| [[Canned Corned Beef]]
| 0.8
| -
| 720
| -
| 78
| 48
| Base.CannedCornedBeef
|-
| [[File:CannedCornedBeefOpen.png|32x32px|link=Canned Corned Beef|Canned Corned Beef (Open)]]
| [[Canned Corned Beef|Canned Corned Beef (Open)]]
| 0.8
| -24
| 720
| -
| 78
| 48
| Base.CannedCornedBeefOpen
|-
| [[File:Dogfood.png|32x32px|link=Canned Dog Food|Canned Dog Food]]
| [[Canned Dog Food]]
| 0.8
| -
| 498
| 77.56
| 16.04
| 12.58
| Base.Dogfood
|-
| [[File:DogfoodOpen.png|32x32px|link=Canned Dog Food|Canned Dog Food (Open)]]
| [[Canned Dog Food|Canned Dog Food (Open)]]
| 0.8
| -30
| 498
| 77.56
| 16.04
| 12.58
| Base.DogfoodOpen
|-
| [[File:CannedCondensedMilk.png|32x32px|link=Canned Evaporated Milk|Canned Evaporated Milk]]
| [[Canned Evaporated Milk]]
| 0.8
| -
| 472
| 23.6
| 23.6
| 23.6
| Base.CannedMilk
|-
| [[File:CannedCondensedMilk_Open.png|32x32px|link=Canned Evaporated Milk|Canned Evaporated Milk (Open)]]
| [[Canned Evaporated Milk|Canned Evaporated Milk (Open)]]
| 0.8
| -10
| 472
| 23.6
| 23.6
| 23.6
| Base.CannedMilkOpen
|-
| [[File:CannedJuice.png|32x32px|link=Canned Fruit Beverage|Canned Fruit Beverage]]
| [[Canned Fruit Beverage]]
| 0.8
| -
| 250
| -
| 10
| 24
| Base.CannedFruitBeverage
|-
| [[File:CannedJuice_Open.png|32x32px|link=Canned Fruit Beverage|Canned Fruit Beverage (Open)]]
| [[Canned Fruit Beverage|Canned Fruit Beverage (Open)]]
| 0.8
| -15
| 250
| -
| 10
| 24
| Base.CannedFruitBeverageOpen
|-
| [[File:CannedFruitCocktail.png|32x32px|link=Canned Fruit Cocktail|Canned Fruit Cocktail]]
| [[Canned Fruit Cocktail]]
| 0.8
| -
| 250
| -
| 10
| 24
| Base.CannedFruitCocktail
|-
| [[File:CannedFruitCocktailOpen.png|32x32px|link=Canned Fruit Cocktail|Canned Fruit Cocktail (Open)]]
| [[Canned Fruit Cocktail|Canned Fruit Cocktail (Open)]]
| 0.8
| -15
| 250
| -
| 10
| 24
| Base.CannedFruitCocktailOpen
|-
| [[File:CannedMushroomSoup.png|32x32px|link=Canned Mushroom Soup|Canned Mushroom Soup]]
| [[Canned Mushroom Soup]]
| 0.8
| -
| 160
| 19
| 3
| 8
| Base.CannedMushroomSoup
|-
| [[File:CannedMushroomSoupOpen.png|32x32px|link=Canned Mushroom Soup|Canned Mushroom Soup (Open)]]
| [[Canned Mushroom Soup|Canned Mushroom Soup (Open)]]
| 0.8
| -10
| 160
| 19
| 3
| 8
| Base.CannedMushroomSoupOpen
|-
| [[File:CannedPeaches.png|32x32px|link=Canned Peaches|Canned Peaches]]
| [[Canned Peaches]]
| 0.8
| -
| 250
| -
| 10
| 24
| Base.CannedPeaches
|-
| [[File:CannedPeachesOpen.png|32x32px|link=Canned Peaches|Canned Peaches (Open)]]
| [[Canned Peaches|Canned Peaches (Open)]]
| 0.8
| -15
| 250
| -
| 10
| 24
| Base.CannedPeachesOpen
|-
| [[File:CannedPeas.png|32x32px|link=Canned Peas|Canned Peas]]
| [[Canned Peas]]
| 0.8
| -
| 280
| 52.5
| 14
| -
| Base.CannedPeas
|-
| [[File:CannedPeasOpen.png|32x32px|link=Canned Peas|Canned Peas (Open)]]
| [[Canned Peas|Canned Peas (Open)]]
| 0.8
| -16
| 280
| 52.5
| 14
| -
| Base.CannedPeasOpen
|-
| [[File:CannedPineapple.png|32x32px|link=Canned Pineapple|Canned Pineapple]]
| [[Canned Pineapple]]
| 0.8
| -
| 250
| -
| 10
| 24
| Base.CannedPineapple
|-
| [[File:CannedPineappleOpen.png|32x32px|link=Canned Pineapple|Canned Pineapple (Open)]]
| [[Canned Pineapple|Canned Pineapple (Open)]]
| 0.8
| -15
| 250
| -
| 10
| 24
| Base.CannedPineappleOpen
|-
| [[File:CannedPotato.png|32x32px|link=Canned Potato|Canned Potato]]
| [[Canned Potato]]
| 0.8
| -
| 175
| 35
| 2.5
| -
| Base.CannedPotato2
|-
| [[File:CannedPotatoOpen.png|32x32px|link=Canned Potato|Canned Potato (Open)]]
| [[Canned Potato|Canned Potato (Open)]]
| 0.8
| -18
| 175
| 35
| 2.5
| -
| Base.CannedPotatoOpen
|-
| [[File:CannedSardines.png|32x32px|link=Canned Sardines|Canned Sardines]]
| [[Canned Sardines]]
| 0.3
| -
| 150
| -
| 14
| 11
| Base.CannedSardines
|-
| [[File:CannedSardinesOpen.png|32x32px|link=Canned Sardines|Canned Sardines (Open)]]
| [[Canned Sardines|Canned Sardines (Open)]]
| 0.3
| -14
| 150
| -
| 14
| 11
| Base.CannedSardinesOpen
|-
| [[File:CannedBolognese.png|32x32px|link=Canned Spaghetti Bolognese|Canned Spaghetti Bolognese]]
| [[Canned Spaghetti Bolognese]]
| 0.8
| -
| 540
| 68
| 18
| 22
| Base.CannedBolognese
|-
| [[File:CannedBologneseOpen.png|32x32px|link=Canned Spaghetti Bolognese|Canned Spaghetti Bolognese (Open)]]
| [[Canned Spaghetti Bolognese|Canned Spaghetti Bolognese (Open)]]
| 0.8
| -24
| 540
| 68
| 18
| 22
| Base.CannedBologneseOpen
|-
| [[File:CannedTomato.png|32x32px|link=Canned Tomato|Canned Tomato]]
| [[Canned Tomato]]
| 0.8
| -
| 90
| 18
| 3
| -
| Base.CannedTomato2
|-
| [[File:CannedTomatoOpen.png|32x32px|link=Canned Tomato|Canned Tomato (Open)]]
| [[Canned Tomato|Canned Tomato (Open)]]
| 0.8
| -12
| 90
| 18
| 3
| -
| Base.CannedTomatoOpen
|-
| [[File:Tuna.png|32x32px|link=Canned Tuna|Canned Tuna]]
| [[Canned Tuna]]
| 0.3
| -
| 370
| -
| 15
| 34
| Base.TunaTin
|-
| [[File:TunaOpen.png|32x32px|link=Canned Tuna|Canned Tuna (Open)]]
| [[Canned Tuna|Canned Tuna (Open)]]
| 0.3
| -18
| 370
| -
| 15
| 34
| Base.TunaTinOpen
|-
| [[File:Soup.png|32x32px|link=Canned Vegetable Soup|Canned Vegetable Soup]]
| [[Canned Vegetable Soup]]
| 0.8
| -
| 125
| 20
| 7.5
| 2.5
| Base.TinnedSoup
|-
| [[File:SoupOpen.png|32x32px|link=Canned Vegetable Soup|Canned Vegetable Soup (Open)]]
| [[Canned Vegetable Soup|Canned Vegetable Soup (Open)]]
| 0.8
| -25
| 125
| 20
| 7.5
| 2.5
| Base.TinnedSoupOpen
|-
| [[File:Capers.png|32x32px|link=Capers|Capers]]
| [[Capers]]
| 0.1
| -5
| 10
| 2
| 1
| -
| Base.Capers
|-
| [[File:CandyCaramels.png|32x32px|link=Caramel Candies|Caramel Candies]]
| [[Caramel Candies]]
| 0.1
| -5
| 170
| 28
| 1
| 5
| Base.CandyCaramels
|-
| [[File:CakeCarrot.png|32x32px|link=Carrot Cake Slice|Carrot Cake Slice]]
| [[Carrot Cake Slice]]
| 0.2
| -7
| 70
| 4
| 10
| 12
| Base.CakeCarrot
|-
| <span class="cycle-img">[[File:Carrots.png|32x32px|link=Carrots|Carrots]][[File:CarrotsRotten.png|32x32px|link=Carrots|Carrots]]</span>
| [[Carrots]]
| 0.2
| -8
| 25
| 6
| 0.6
| 0.15
| Base.Carrots
|-
| [[File:CatTreats.png|32x32px|link=Cat Treats|Cat Treats]]
| [[Cat Treats]]
| 0.1
| -5
| 70
| 12
| 1
| 6
| Base.CatTreats
|-
| [[File:Insect_AmericanLadyCaterpillar.png|32x32px|link=Caterpillar (American lady)|Caterpillar]]
| [[Caterpillar (American lady)|Caterpillar]]
| 0.1
| -1
| 27
| 3
| 27.55
| 20.24
| Base.AmericanLadyCaterpillar
|-
| [[File:Insect_BandedWoolyBearCaterpillar.png|32x32px|link=Caterpillar (banded woolly bear)|Caterpillar]]
| [[Caterpillar (banded woolly bear)|Caterpillar]]
| 0.1
| -1
| 27
| 3
| 27.55
| 20.24
| Base.BandedWoolyBearCaterpillar
|-
| [[File:Insect_MonarchrCaterpillar.png|32x32px|link=Caterpillar (monarch)|Caterpillar]]
| [[Caterpillar (monarch)|Caterpillar]]
| 0.1
| -1
| 27
| 3
| 27.55
| 20.24
| Base.MonarchCaterpillar
|-
| [[File:Insect_SawflyLarva.png|32x32px|link=Caterpillar (sawfly larva)|Caterpillar]]
| [[Caterpillar (sawfly larva)|Caterpillar]]
| 0.1
| -1
| 27
| 3
| 27.55
| 20.24
| Base.SawflyLarva
|-
| [[File:Insect_SilkMothCaterpillar.png|32x32px|link=Caterpillar (silk moth)|Caterpillar]]
| [[Caterpillar (silk moth)|Caterpillar]]
| 0.1
| -1
| 27
| 3
| 27.55
| 20.24
| Base.SilkMothCaterpillar
|-
| [[File:Insect_SwallowtailCaterpillar.png|32x32px|link=Caterpillar (swallowtail)|Caterpillar]]
| [[Caterpillar (swallowtail)|Caterpillar]]
| 0.1
| -1
| 27
| 3
| 27.55
| 20.24
| Base.SwallowtailCaterpillar
|-
| <span class="cycle-img">[[File:Cauliflower.png|32x32px|link=Cauliflower|Cauliflower]][[File:CauliflowerRotten.png|32x32px|link=Cauliflower|Cauliflower]]</span>
| [[Cauliflower]]
| 0.2
| -9
| 24
| 3
| 4
| -
| Base.Cauliflower
|-
| [[File:Insect_Centipede1.png|32x32px|link=Centipede|Centipede]]
| [[Centipede]]
| 0.1
| -1
| 60
| 3.5
| 15.21
| 6.5
| Base.Centipede
|-
| [[File:Insect_Centipede2.png|32x32px|link=Centipede|Centipede]]
| [[Centipede]]
| 0.1
| -1
| 60
| 3.5
| 15.21
| 6.5
| Base.Centipede2
|-
| <span class="cycle-img">[[File:Cereal_SunBallz.png|32x32px|link=Cereal|Cereal]][[File:Cereal_CornFlakes.png|32x32px|link=Cereal|Cereal]][[File:Cereal_Muesli.png|32x32px|link=Cereal|Cereal]][[File:Cereal_HappyCurios.png|32x32px|link=Cereal|Cereal]][[File:Cereal_OatRings.png|32x32px|link=Cereal|Cereal]]</span>
| [[Cereal]]
| 0.2
| -40
| 2360
| 572
| 52
| 26
| Base.Cereal
|-
| <span class="cycle-img">[[File:Chamomile.png|32x32px|link=Chamomile|Chamomile]][[File:ChamomileRotten.png|32x32px|link=Chamomile|Chamomile]]</span>
| [[Chamomile]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.Chamomile
|-
| [[File:Chamomile_Dried.png|32x32px|link=Chamomile (Dried)|Chamomile (Dried)]]
| [[Chamomile (Dried)]]
| 0.1
| -5
| 0.1
| -
| -
| -
| Base.ChamomileDried
|-
| [[File:Fish_CatfishChannel.png|32x32px|link=Channel Catfish|Channel Catfish]]
| [[Channel Catfish]]
| 0.4
| -15
| 159
| 1
| 35
| 1
| Base.ChannelCatfish
|-
| <span class="cycle-img">[[File:Cheese.png|32x32px|link=Cheese|Cheese]][[File:CheeseRotten.png|32x32px|link=Cheese|Cheese]]</span>
| [[Cheese]]
| 0.2
| -15
| 113
| 0.87
| 6.4
| 9.33
| Base.Cheese
|-
| [[File:CakeCheesecake.png|32x32px|link=Cheese Cake Slice|Cheese Cake Slice]]
| [[Cheese Cake Slice]]
| 0.2
| -8
| 80
| 4
| 10
| 12
| Base.CakeCheeseCake
|-
| [[File:CheesePowdered.png|32x32px|link=Cheese Powder|Cheese Powder]]
| [[Cheese Powder]]
| 0.1
| -14
| 130
| 20.7
| 21
| 9.7
| Base.cheese_powdered
|-
| <span class="cycle-img">[[File:Cherry.png|32x32px|link=Cherry|Cherry]][[File:CherryRotten.png|32x32px|link=Cherry|Cherry]]</span>
| [[Cherry]]
| 0.1
| -3
| 5
| 1.31
| 0.09
| -
| Base.Cherry
|-
| [[File:Pie.png|32x32px|link=Cherry Pie Slice|Cherry Pie Slice]]
| [[Cherry Pie Slice]]
| 0.5
| -30
| 404
| 20.45
| 54.53
| 20.61
| Base.Pie
|-
| [[File:DriedChickpeas.png|32x32px|link=Chick Peas (Dried)|Chick Peas (Dried)]]
| [[Chick Peas (Dried)]]
| 2
| -60
| 2851
| 544
| 181
| -
| Base.DriedChickpeas
|-
| <span class="cycle-img">[[File:ChickenWhole.png|32x32px|link=Chicken (Whole)|Chicken (Whole)]][[File:ChickenWholeRotten.png|32x32px|link=Chicken (Whole)|Chicken (Whole)]][[File:ChickenWholeCooked.png|32x32px|link=Chicken (Whole)|Chicken (Whole)]][[File:ChickenWholeOverdone.png|32x32px|link=Chicken (Whole)|Chicken (Whole)]]</span>
| [[Chicken (Whole)]]
| 1.2
| -160
| 1495
| -
| 99.8
| 41
| Base.ChickenWhole
|-
| <span class="cycle-img">[[File:ChickenFilet.png|32x32px|link=Chicken Fillet|Chicken Fillet]][[File:ChickenFiletRotten.png|32x32px|link=Chicken Fillet|Chicken Fillet]][[File:ChickenFiletCooked.png|32x32px|link=Chicken Fillet|Chicken Fillet]][[File:ChickenFiletOverdone.png|32x32px|link=Chicken Fillet|Chicken Fillet]]</span>
| [[Chicken Fillet]]
| 0.3
| -30
| 230
| -
| 38
| 9
| Base.ChickenFillet
|-
| [[File:ChickenFoot.png|32x32px|link=Chicken Foot|Chicken Foot]]
| [[Chicken Foot]]
| 0.1
| -12
| 70
| 17
| 16
| 14
| Base.ChickenFoot
|-
| <span class="cycle-img">[[File:Chicken.png|32x32px|link=Chicken Leg|Chicken Leg]][[File:ChickenRotten.png|32x32px|link=Chicken Leg|Chicken Leg]][[File:ChickenCooked.png|32x32px|link=Chicken Leg|Chicken Leg]][[File:ChickenOverdone.png|32x32px|link=Chicken Leg|Chicken Leg]]</span>
| [[Chicken Leg]]
| 0.3
| -33
| 230
| -
| 38
| 9
| Base.Chicken
|-
| [[File:ChickenNuggets.png|32x32px|link=Chicken Nuggets|Chicken Nuggets]]
| [[Chicken Nuggets]]
| 0.2
| -10
| 230
| 10.2
| 26.441
| 8.1
| Base.ChickenNuggets
|-
| <span class="cycle-img">[[File:ChickenWing.png|32x32px|link=Chicken Wing|Chicken Wing]][[File:ChickenWingRotten.png|32x32px|link=Chicken Wing|Chicken Wing]][[File:ChickenWingCooked.png|32x32px|link=Chicken Wing|Chicken Wing]][[File:ChickenWingOverdone.png|32x32px|link=Chicken Wing|Chicken Wing]]</span>
| [[Chicken Wing]]
| 0.3
| -19
| 190
| -
| 22
| 6
| Base.ChickenWings
|-
| [[File:Crisps2.png|32x32px|link=Chips - Barbecue|Chips - Barbecue]]
| [[Chips - Barbecue]]
| 0.2
| -15
| 720
| 72
| 4.5
| 45
| Base.Crisps2
|-
| [[File:Crisps.png|32x32px|link=Chips - Plain|Chips - Plain]]
| [[Chips - Plain]]
| 0.2
| -15
| 720
| 72
| 4.5
| 45
| Base.Crisps
|-
| [[File:Crisps3.png|32x32px|link=Chips - Salt & Vinegar|Chips - Salt & Vinegar]]
| [[Chips - Salt & Vinegar]]
| 0.2
| -15
| 720
| 72
| 4.5
| 45
| Base.Crisps3
|-
| [[File:Crisps4.png|32x32px|link=Chips - Sour Cream & Onion|Chips - Sour Cream & Onion]]
| [[Chips - Sour Cream & Onion]]
| 0.2
| -15
| 720
| 72
| 4.5
| 45
| Base.Crisps4
|-
| [[File:HerbChives.png|32x32px|link=Chives|Chives]]
| [[Chives]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.Chives
|-
| [[File:Seasoning_Chives.png|32x32px|link=Chives (Dried) (seasoning)|Chives (Dried)]]
| [[Chives (Dried) (seasoning)|Chives (Dried)]]
| 0.2
| -20
| 0.4
| -
| -
| -
| Base.Seasoning_Chives
|-
| [[File:DriedHerbs_generic.png|32x32px|link=Chives (Dried)|Chives (Dried)]]
| [[Chives (Dried)]]
| 0.1
| -5
| 0.1
| -
| -
| -
| Base.ChivesDried
|-
| [[File:Snackcake_Chocakes.png|32x32px|link=Choco Cakes|Choco Cakes]]
| [[Choco Cakes]]
| 0.2
| -10
| 200
| 30
| 1.8
| 8
| Base.ChocoCakes
|-
| [[File:Painauchocolat.png|32x32px|link=Chocolate Bread|Chocolate Bread]]
| [[Chocolate Bread]]
| 0.1
| -2
| 414
| 47.4
| 6.9
| 21.1
| Base.Painauchocolat
|-
| [[File:CakeChocolate.png|32x32px|link=Chocolate Cake Slice|Chocolate Cake Slice]]
| [[Chocolate Cake Slice]]
| 0.2
| -10
| 90
| 4
| 10
| 12
| Base.CakeChocolate
|-
| [[File:Chocolate_Candy.png|32x32px|link=Chocolate Candy|Chocolate Candy]]
| [[Chocolate Candy]]
| 0.1
| -5
| 110
| 27
| -
| -
| Base.Chocolate_Candy
|-
| [[File:CookieChocolateChip.png|32x32px|link=Chocolate Chip Cookie|Chocolate Chip Cookie]]
| [[Chocolate Chip Cookie]]
| 0.1
| -5
| 160
| 22
| 1
| 8
| Base.CookieChocolateChip
|-
| [[File:ChocolateChips.png|32x32px|link=Chocolate Chips|Chocolate Chips]]
| [[Chocolate Chips]]
| 0.1
| -6
| 50
| 17
| 1
| 8
| Base.ChocolateChips
|-
| [[File:CookiesChocolate.png|32x32px|link=Chocolate Cookie|Chocolate Cookie]]
| [[Chocolate Cookie]]
| 0.1
| -5
| 170
| 25
| 2
| 9
| Base.CookiesChocolate
|-
| [[File:DoughnutChocolate.png|32x32px|link=Chocolate Donut|Chocolate Donut]]
| [[Chocolate Donut]]
| 0.1
| -7
| 180
| 35
| 3
| 15
| Base.DoughnutChocolate
|-
| [[File:ChocolateCoveredCoffeeBeans.png|32x32px|link=Chocolate-Covered Coffee Beans|Chocolate-Covered Coffee Beans]]
| [[Chocolate-Covered Coffee Beans]]
| 0.1
| -5
| 40
| 10
| -
| 0.5
| Base.ChocolateCoveredCoffeeBeans
|-
| [[File:HerbCilantro.png|32x32px|link=Cilantro|Cilantro]]
| [[Cilantro]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.Cilantro
|-
| [[File:Seasoning_Cilantro.png|32x32px|link=Cilantro (Dried)|Cilantro (Dried)]]
| [[Cilantro (Dried)]]
| 0.2
| -20
| 0.4
| -
| -
| -
| Base.Seasoning_Cilantro
|-
| [[File:DriedHerbs_generic.png|32x32px|link=Cilantro (Dried)|Cilantro (Dried)]]
| [[Cilantro (Dried)]]
| 0.1
| -5
| 0.1
| -
| -
| -
| Base.CilantroDried
|-
| [[File:Seeds_Generic.png|32x32px|link=Cilantro Seeds|Cilantro Seeds]]
| [[Cilantro Seeds]]
| 0.02
| -1
| 0.1
| -
| -
| -
| Base.CilantroSeed
|-
| [[File:Cinnamon.png|32x32px|link=Cinnamon|Cinnamon]]
| [[Cinnamon]]
| 0.1
| -5
| 1
| -
| -
| -
| Base.Cinnamon
|-
| [[File:CinnamonRoll.png|32x32px|link=Cinnamon Roll|Cinnamon Roll]]
| [[Cinnamon Roll]]
| 0.1
| -12
| 350
| 50
| 4
| 24
| Base.CinnamonRoll
|-
| <span class="cycle-img">[[File:Cockroach.png|32x32px|link=Cockroach|Cockroach]][[File:CockroachCooked.png|32x32px|link=Cockroach|Cockroach]]</span>
| [[Cockroach]]
| 0.1
| -1
| 30
| 1.27
| 7.41
| 3.9
| Base.Cockroach
|-
| [[File:CocoaPowder.png|32x32px|link=Cocoa Powder|Cocoa Powder]]
| [[Cocoa Powder]]
| 1
| -30
| 60
| 8
| 2
| 5
| Base.CocoaPowder
|-
| [[File:InstantCoffee.png|32x32px|link=Coffee|Coffee]]
| [[Coffee]]
| 1
| -30
| 2
| -
| 1
| -
| Base.Coffee2
|-
| <span class="cycle-img">[[File:CommonMallow.png|32x32px|link=Common Mallow|Common Mallow]][[File:CommonMallowRotten.png|32x32px|link=Common Mallow|Common Mallow]]</span>
| [[Common Mallow]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.CommonMallow
|-
| [[File:CommonMallow_Dried.png|32x32px|link=Common Mallow (Dried)|Common Mallow (Dried)]]
| [[Common Mallow (Dried)]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.CommonMallowDried
|-
| [[File:Cone.png|32x32px|link=Cone|Cone]]
| [[Cone]]
| 0.1
| -5
| 15
| 10
| 2
| 5
| Base.Cone
|-
| [[File:Pot_Water.png|32x32px|link=Pasta (crafted pot)|Cooking Pot with Pasta]]
| [[Pasta (crafted pot)|Cooking Pot with Pasta]]
| 3
| -10
| 560
| 109.3
| 18.66
| 2.66
| Base.WaterPotPasta
|-
| <span class="cycle-img">[[File:Pot_Forged_Pasta.png|32x32px|link=Pasta (crafted pot)|Cooking Pot with Pasta]][[File:Pot_Forged_PastaRotten.png|32x32px|link=Pasta (crafted pot)|Cooking Pot with Pasta]]</span>
| [[Pasta (crafted pot)|Cooking Pot with Pasta]]
| 3
| -10
| 560
| 109.3
| 18.66
| 2.66
| Base.WaterPotForgedPasta
|-
| [[File:Pot_Water.png|32x32px|link=Rice (crafted pot)|Cooking Pot with Rice]]
| [[Rice (crafted pot)|Cooking Pot with Rice]]
| 3
| -10
| 480
| 108
| 12
| -
| Base.WaterPotRice
|-
| <span class="cycle-img">[[File:Pot_Forged_Rice.png|32x32px|link=Rice (crafted pot)|Cooking Pot with Rice]][[File:Pot_Forged_RiceRotten.png|32x32px|link=Rice (crafted pot)|Cooking Pot with Rice]]</span>
| [[Rice (crafted pot)|Cooking Pot with Rice]]
| 3
| -10
| 480
| 108
| 12
| -
| Base.WaterPotForgedRice
|-
| [[File:CopperPot_Pasta.png|32x32px|link=Copper Saucepan with Pasta|Copper Saucepan with Pasta]]
| [[Copper Saucepan with Pasta]]
| 3
| -10
| 560
| 109.3
| 18.66
| 2.66
| Base.WaterSaucepanPastaCopper
|-
| [[File:CopperPot_Pasta.png|32x32px|link=Copper Saucepan with Rice|Copper Saucepan with Rice]]
| [[Copper Saucepan with Rice]]
| 3
| -10
| 480
| 108
| 12
| -
| Base.WaterSaucepanRiceCopper
|-
| <span class="cycle-img">[[File:Corn.png|32x32px|link=Corn|Corn]][[File:CornRotten.png|32x32px|link=Corn|Corn]]</span>
| [[Corn]]
| 0.2
| -14
| 88
| 26.74
| 4.68
| 1.93
| Base.Corn
|-
| [[File:DriedCorn.png|32x32px|link=Corn (Dried)|Corn (Dried)]]
| [[Corn (Dried)]]
| 0.02
| -4
| 24.8
| 7.6
| 1.32
| 0.56
| Base.CornSeed
|-
| [[File:Cornbread.png|32x32px|link=Cornbread|Cornbread]]
| [[Cornbread]]
| 0.1
| -10
| 300
| 54
| 7
| 10
| Base.Cornbread
|-
| [[File:Corndog.png|32x32px|link=Corndog|Corndog]]
| [[Corndog]]
| 0.1
| -12
| 180
| 7
| 19
| 9
| Base.Corndog
|-
| [[File:Crackers.png|32x32px|link=Crackers|Crackers]]
| [[Crackers]]
| 0.1
| -5
| 70
| 12
| 1
| 6
| Base.Crackers
|-
| [[File:Chocolate_Crackle.png|32x32px|link=Crackle Bar|Crackle Bar]]
| [[Crackle Bar]]
| 0.2
| -20
| 230
| 29
| 2
| 12
| Base.Chocolate_Crackle
|-
| <span class="cycle-img">[[File:Crayfish.png|32x32px|link=Crayfish|Crayfish]][[File:CrayfishRotten.png|32x32px|link=Crayfish|Crayfish]][[File:CrayfishCooked.png|32x32px|link=Crayfish|Crayfish]]</span>
| [[Crayfish]]
| 0.2
| -10
| 40
| -
| 8
| 2
| Base.Crayfish
|-
| [[File:Creamocle.png|32x32px|link=Creamocle|Creamocle]]
| [[Creamocle]]
| 0.2
| -15
| 100
| 19
| 1
| 1.5
| Base.Creamocle
|-
| [[File:Creamocle_Melted.png|32x32px|link=Creamocle (Melted)|Creamocle (Melted)]]
| [[Creamocle (Melted)]]
| 0.2
| -15
| 100
| 19
| 1
| 1.5
| Base.Creamocle_Melted
|-
| <span class="cycle-img">[[File:Cricket.png|32x32px|link=Cricket|Cricket]][[File:CricketCooked.png|32x32px|link=Cricket|Cricket]]</span>
| [[Cricket]]
| 0.1
| -1
| 20
| 1.34
| 3.6
| 1.32
| Base.Cricket
|-
| [[File:CrispyRiceSquare.png|32x32px|link=Crispy Rice Square|Crispy Rice Square]]
| [[Crispy Rice Square]]
| 0.2
| -10
| 140
| 28
| 1
| 3
| Base.CrispyRiceSquare
|-
| [[File:Croissant.png|32x32px|link=Croissant|Croissant]]
| [[Croissant]]
| 0.1
| -8
| 180
| 32
| 4
| 15
| Base.Croissant
|-
| <span class="cycle-img">[[File:Cucumber.png|32x32px|link=Cucumber|Cucumber]][[File:CucumberRotten.png|32x32px|link=Cucumber|Cucumber]]</span>
| [[Cucumber]]
| 0.3
| -10
| 33
| 6.1
| 2.37
| 0.63
| Base.Cucumber
|-
| [[File:Cupcake.png|32x32px|link=Cupcake|Cupcake]]
| [[Cupcake]]
| 0.2
| -20
| 305
| 67
| 4
| 4
| Base.Cupcake
|-
| <span class="cycle-img">[[File:Daikon.png|32x32px|link=Daikon|Daikon]][[File:DaikonRotten.png|32x32px|link=Daikon|Daikon]]</span>
| [[Daikon]]
| 0.2
| -12
| 54
| 12.59
| 1.34
| 0.27
| Base.Daikon
|-
| [[File:Dandelions.png|32x32px|link=Dandelions|Dandelions]]
| [[Dandelions]]
| 0.1
| -5
| 25
| 5
| 1.5
| 0.5
| Base.Dandelions
|-
| [[File:Danish.png|32x32px|link=Danish|Danish]]
| [[Danish]]
| 0.1
| -7
| 263
| 34
| 4
| 13
| Base.Danish
|-
| <span class="cycle-img">[[File:BirdDead.png|32x32px|link=Dead Bird|Dead Bird]][[File:BirdDeadRotten.png|32x32px|link=Dead Bird|Dead Bird]]</span>
| [[Dead Bird]]
| 0.1
| -15
| 161
| 0.5
| 22
| 2
| Base.DeadBird
|-
| <span class="cycle-img">[[File:MouseDead.png|32x32px|link=Dead Mouse|Dead Mouse]][[File:MouseDeadRotten.png|32x32px|link=Dead Mouse|Dead Mouse]]</span>
| [[Dead Mouse]]
| 0.05
| -10
| 220
| 0.7
| 9.5
| 3.15
| Base.DeadMouse
|-
| [[File:RabbitDead.png|32x32px|link=Dead Rabbit|Dead Rabbit]]
| [[Dead Rabbit]]
| 1
| -45
| 1730
| -
| 330
| 35
| Base.DeadRabbit
|-
| <span class="cycle-img">[[File:DeadRat.png|32x32px|link=Dead Rat|Dead Rat]][[File:DeadRatRotten.png|32x32px|link=Dead Rat|Dead Rat]][[File:DeadRatCooked.png|32x32px|link=Dead Rat|Dead Rat]]</span>
| [[Dead Rat]]
| 0.2
| -22
| 324
| -
| 40
| 16
| Base.DeadRat
|-
| [[File:SquirrelDead.png|32x32px|link=Dead Squirrel|Dead Squirrel]]
| [[Dead Squirrel]]
| 0.4
| -32
| 480
| -
| 84.8
| 15
| Base.DeadSquirrel
|-
| [[File:DehydratedMeatStick.png|32x32px|link=Dehydrated Meat Stick|Dehydrated Meat Stick]]
| [[Dehydrated Meat Stick]]
| 0.1
| -10
| 100
| 5.3
| 21.63
| 5.1
| Base.DehydratedMeatStick
|-
| [[File:Chocolate_Deux.png|32x32px|link=Deux Bar|Deux Bar]]
| [[Deux Bar]]
| 0.2
| -20
| 250
| 34
| 2
| 12
| Base.Chocolate_Deux
|-
| [[File:DoughnutPlain.png|32x32px|link=Donut|Donut]]
| [[Donut]]
| 0.1
| -7
| 180
| 35
| 3
| 15
| Base.DoughnutPlain
|-
| <span class="cycle-img">[[File:Dough.png|32x32px|link=Dough|Dough]][[File:DoughRotten.png|32x32px|link=Dough|Dough]][[File:DoughCooked.png|32x32px|link=Dough|Dough]][[File:DoughBurnt.png|32x32px|link=Dough|Dough]]</span>
| [[Dough]]
| 0.3
| -15
| 532
| 99
| 17.7
| 6.66
| Base.Dough
|-
| [[File:Ramen.png|32x32px|link=Dry Ramen Noodles|Dry Ramen Noodles]]
| [[Dry Ramen Noodles]]
| 0.2
| -10
| 52
| -
| 10
| 14
| Base.Ramen
|-
| [[File:Edamame.png|32x32px|link=Edamame|Edamame]]
| [[Edamame]]
| 0.1
| -5
| 25
| 10.45
| 3.95
| 0.45
| Base.Edamame
|-
| [[File:Egg.png|32x32px|link=Egg|Egg]]
| [[Egg]]
| 0.1
| -7
| 63
| 0.32
| 5.55
| 4.18
| Base.Egg
|-
| [[File:EggBoiled.png|32x32px|link=Egg (Boiled)|Egg (Boiled)]]
| [[Egg (Boiled)]]
| 0.1
| -10
| 63
| 0.32
| 5.55
| 4.18
| Base.EggBoiled
|-
| [[File:EggPoached.png|32x32px|link=Egg (Poached)|Egg (Poached)]]
| [[Egg (Poached)]]
| 0.1
| -10
| 63
| 0.32
| 5.55
| 4.18
| Base.EggPoached
|-
| [[File:EggScrambled.png|32x32px|link=Egg (Scrambled)|Egg (Scrambled)]]
| [[Egg (Scrambled)]]
| 0.1
| -20
| 120
| 0.52
| 10.55
| 6.18
| Base.EggScrambled
|-
| [[File:SushiEgg.png|32x32px|link=Egg Sushi|Egg Sushi]]
| [[Egg Sushi]]
| 0.1
| -8
| 19
| 7
| 12
| 3
| Base.SushiEgg
|-
| <span class="cycle-img">[[File:Eggplant.png|32x32px|link=Eggplant|Eggplant]][[File:EggplantRotten.png|32x32px|link=Eggplant|Eggplant]]</span>
| [[Eggplant]]
| 0.2
| -16
| 114
| 27
| 4.5
| 0.8
| Base.Eggplant
|-
| [[File:FishFried.png|32x32px|link=Fish (Fried)|Fish (Fried)]]
| [[Fish (Fried)]]
| 0.2
| -30
| 210
| 7
| 16
| 12
| Base.FishFried
|-
| <span class="cycle-img">[[File:FishFillet.png|32x32px|link=Fish Fillet|Fish Fillet]][[File:FishFilletRotten.png|32x32px|link=Fish Fillet|Fish Fillet]][[File:FishFilletCooked.png|32x32px|link=Fish Fillet|Fish Fillet]][[File:FishFilletOverdone.png|32x32px|link=Fish Fillet|Fish Fillet]]</span>
| [[Fish Fillet]]
| 0.2
| -25
| 205
| 1
| 28.52
| 12
| Base.FishFillet
|-
| [[File:FishFingers.png|32x32px|link=Fish Fingers|Fish Fingers]]
| [[Fish Fingers]]
| 0.2
| -10
| 230
| 10.2
| 26.441
| 8.1
| Base.FishFingers
|-
| [[File:FishRoe.png|32x32px|link=Fish Roe|Fish Roe]]
| [[Fish Roe]]
| 0.1
| -10
| 63
| 0.32
| 5.55
| 4.18
| Base.FishRoe
|-
| [[File:Fish_EggSack.png|32x32px|link=Fish Roe Sac|Fish Roe Sac]]
| [[Fish Roe Sac]]
| 0.1
| -5
| 56
| 14
| 5.2
| 0.8
| Base.FishRoeSac
|-
| [[File:SushiFish.png|32x32px|link=Fish Sushi|Fish Sushi]]
| [[Fish Sushi]]
| 0.1
| -8
| 19
| 5
| 10
| -
| Base.SushiFish
|-
| [[File:Fish_CatfishFlathead.png|32x32px|link=Flathead Catfish|Flathead Catfish]]
| [[Flathead Catfish]]
| 0.4
| -15
| 159
| 1
| 35
| 1
| Base.FlatheadCatfish
|-
| [[File:Flax_Seeds.png|32x32px|link=Flax Seeds|Flax Seeds]]
| [[Flax Seeds]]
| 0.02
| -1
| 71
| -
| -
| 4.5
| Base.FlaxSeed
|-
| [[File:Flour.png|32x32px|link=Flour|Flour]]
| [[Flour]]
| 2
| -60
| 50
| 21
| 5
| -
| Base.Flour2
|-
| [[File:FourLeafClover.png|32x32px|link=Four Leaf Clover|Four Leaf Clover]]
| [[Four Leaf Clover]]
| 0.1
| -1
| 1
| -
| -
| -
| Base.FourLeafClover
|-
| [[File:Fish_DrumFreshwater.png|32x32px|link=Freshwater Drum|Freshwater Drum]]
| [[Freshwater Drum]]
| 0.4
| -15
| 159
| 1
| 35
| 1
| Base.FreshwaterDrum
|-
| [[File:ChickenFried.png|32x32px|link=Fried Chicken|Fried Chicken]]
| [[Fried Chicken]]
| 0.1
| -15
| 260
| 17
| 16
| 14
| Base.ChickenFried
|-
| [[File:OnionRings.png|32x32px|link=Fried Onion Rings|Fried Onion Rings]]
| [[Fried Onion Rings]]
| 0.1
| -10
| 200
| 22
| 2
| 12
| Base.FriedOnionRings
|-
| [[File:OnionRings.png|32x32px|link=Fried Onion Rings|Fried Onion Rings]]
| [[Fried Onion Rings]]
| 0.1
| -10
| 200
| 22
| 2
| 12
| Base.FriedOnionRingsCraft
|-
| [[File:ShrimpFried.png|32x32px|link=Fried Shrimp|Fried Shrimp]]
| [[Fried Shrimp]]
| 0.1
| -15
| 160
| 17
| 16
| 14
| Base.ShrimpFried
|-
| [[File:ShrimpFried.png|32x32px|link=Fried Shrimp|Fried Shrimp]]
| [[Fried Shrimp]]
| 0.1
| -15
| 160
| 17
| 16
| 14
| Base.ShrimpFriedCraft
|-
| [[File:Fries.png|32x32px|link=Fries|Fries]]
| [[Fries]]
| 0.4
| -10
| 203
| 35.97
| 3.35
| 5.19
| Base.Fries
|-
| [[File:FrenchFries.png|32x32px|link=Fries|Fries]]
| [[Fries]]
| 0.2
| -10
| 203
| 35.97
| 3.35
| 5.19
| Base.FrenchFries
|-
| <span class="cycle-img">[[File:Frogmeat.png|32x32px|link=Frog Meat|Frog Meat]][[File:FrogmeatRotten.png|32x32px|link=Frog Meat|Frog Meat]][[File:FrogmeatCooked.png|32x32px|link=Frog Meat|Frog Meat]][[File:FrogmeatOverdone.png|32x32px|link=Frog Meat|Frog Meat]]</span>
| [[Frog Meat]]
| 0.2
| -10
| 66
| -
| 14.6
| 0.28
| Base.FrogMeat
|-
| [[File:DoughnutFrosted.png|32x32px|link=Frosted Donut|Frosted Donut]]
| [[Frosted Donut]]
| 0.1
| -7
| 180
| 35
| 3
| 15
| Base.DoughnutFrosted
|-
| [[File:JamFruit.png|32x32px|link=Fruit Jam|Fruit Jam]]
| [[Fruit Jam]]
| 0.2
| -30
| 550
| 130
| 1
| -
| Base.JamFruit
|-
| [[File:MuffinFruit.png|32x32px|link=Fruit Muffin|Fruit Muffin]]
| [[Fruit Muffin]]
| 0.1
| -7
| 120
| 10.45
| 14.53
| 12.61
| Base.MuffinFruit
|-
| [[File:FudgeePop.png|32x32px|link=Fudgee Pop|Fudgee Pop]]
| [[Fudgee Pop]]
| 0.2
| -15
| 100
| 18
| 2
| 2.5
| Base.FudgeePop
|-
| [[File:FudgeePop_Melted.png|32x32px|link=Fudgee Pop (Melted)|Fudgee Pop (Melted)]]
| [[Fudgee Pop (Melted)]]
| 0.2
| -15
| 100
| 18
| 2
| 2.5
| Base.FudgeePop_Melted
|-
| [[File:Chocolate_GalacticDairy.png|32x32px|link=Galactic Dairy Bar|Galactic Dairy Bar]]
| [[Galactic Dairy Bar]]
| 0.2
| -20
| 190
| 30
| 2
| 8
| Base.Chocolate_GalacticDairy
|-
| [[File:Garlic.png|32x32px|link=Garlic|Garlic]]
| [[Garlic]]
| 0.2
| -5
| 14
| 3.27
| 0.385
| 0.035
| Base.Garlic
|-
| [[File:GingerPickled.png|32x32px|link=Ginger (Pickled)|Ginger (Pickled)]]
| [[Ginger (Pickled)]]
| 0.1
| -5
| 23
| 0.22
| 2.55
| 1.18
| Base.GingerPickled
|-
| [[File:RootGinger.png|32x32px|link=Ginger Root|Ginger Root]]
| [[Ginger Root]]
| 0.1
| -5
| 46
| 0.44
| 5.1
| 2.36
| Base.GingerRoot
|-
| [[File:Gingerbreadman.png|32x32px|link=Gingerbread Man|Gingerbread Man]]
| [[Gingerbread Man]]
| 0.1
| -5
| 160
| 22
| 1
| 8
| Base.Gingerbreadman
|-
| [[File:Ginseng.png|32x32px|link=Ginseng|Ginseng]]
| [[Ginseng]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.Ginseng
|-
| [[File:GrahamCrackers.png|32x32px|link=Graham Crackers|Graham Crackers]]
| [[Graham Crackers]]
| 0.1
| -5
| 70
| 12
| 1
| 6
| Base.GrahamCrackers
|-
| [[File:GranolaBar.png|32x32px|link=Granola Bar|Granola Bar]]
| [[Granola Bar]]
| 0.2
| -15
| 270
| 120
| 20
| 44
| Base.GranolaBar
|-
| [[File:GrapeLeaves.png|32x32px|link=Grape Leaves|Grape Leaves]]
| [[Grape Leaves]]
| 0.1
| -4
| 73
| 11
| 4
| 2
| Base.GrapeLeaves
|-
| <span class="cycle-img">[[File:Grapefruit.png|32x32px|link=Grapefruit|Grapefruit]][[File:GrapefruitRotten.png|32x32px|link=Grapefruit|Grapefruit]]</span>
| [[Grapefruit]]
| 0.3
| -20
| 15
| 101.11
| 17.56
| 3.78
| Base.Grapefruit
|-
| <span class="cycle-img">[[File:Grapes.png|32x32px|link=Grapes|Grapes]][[File:GrapesRotten.png|32x32px|link=Grapes|Grapes]]</span>
| [[Grapes]]
| 0.2
| -15
| 62
| 15.78
| 0.58
| 0.32
| Base.Grapes
|-
| <span class="cycle-img">[[File:Grasshopper.png|32x32px|link=Grasshopper|Grasshopper]][[File:GrasshopperCooked.png|32x32px|link=Grasshopper|Grasshopper]]</span>
| [[Grasshopper]]
| 0.1
| -1
| 25
| 3
| 5.55
| 0.24
| Base.Grasshopper
|-
| [[File:Gravy.png|32x32px|link=Gravy|Gravy]]
| [[Gravy]]
| 0.2
| -8
| 79
| 5
| 2
| 6
| Base.Gravy
|-
| [[File:HerbChives.png|32x32px|link=Green Onions|Green Onions]]
| [[Green Onions]]
| 0.2
| -3
| 0.1
| -
| -
| -
| Base.GreenOnions
|-
| <span class="cycle-img">[[File:Greenpeas.png|32x32px|link=Green Peas|Green Peas]][[File:GreenpeasRotten.png|32x32px|link=Green Peas|Green Peas]]</span>
| [[Green Peas]]
| 0.2
| -4
| 70
| 13.125
| 3.5
| -
| Base.Greenpeas
|-
| [[File:DriedPeas.png|32x32px|link=Green Peas (Dried)|Green Peas (Dried)]]
| [[Green Peas (Dried)]]
| 0.02
| -1
| 17.5
| 3.25
| 0.875
| -
| Base.GreenpeasSeed
|-
| [[File:Fish_SunfishGreen.png|32x32px|link=Green Sunfish|Green Sunfish]]
| [[Green Sunfish]]
| 0.4
| -15
| 159
| 1
| 35
| 1
| Base.GreenSunfish
|-
| <span class="cycle-img">[[File:MincedMeat.png|32x32px|link=Ground Beef|Ground Beef]][[File:MincedMeatRotten.png|32x32px|link=Ground Beef|Ground Beef]][[File:MincedMeatCooked.png|32x32px|link=Ground Beef|Ground Beef]][[File:MincedMeatBurnt.png|32x32px|link=Ground Beef|Ground Beef]]</span>
| [[Ground Beef]]
| 0.3
| -40
| 300
| -
| 46
| 30
| Base.MincedMeat
|-
| [[File:Guacamole.png|32x32px|link=Guacamole|Guacamole]]
| [[Guacamole]]
| 0.1
| -8
| 182
| 2
| 4.6
| 16.6
| Base.Guacamole
|-
| [[File:Gum.png|32x32px|link=Gum|Gum]]
| [[Gum]]
| 0.1
| -1
| 30
| 10
| -
| -
| Base.Gum
|-
| [[File:GummyBears.png|32x32px|link=Gummy Bears|Gummy Bears]]
| [[Gummy Bears]]
| 0.1
| -5
| 40
| 10
| -
| 0.5
| Base.GummyBears
|-
| [[File:CandyGummyfish.png|32x32px|link=Gummy Fish Candy|Gummy Fish Candy]]
| [[Gummy Fish Candy]]
| 0.1
| -5
| 110
| 27
| -
| -
| Base.CandyGummyfish
|-
| [[File:GummyWorms.png|32x32px|link=Gummy Worms|Gummy Worms]]
| [[Gummy Worms]]
| 0.1
| -5
| 40
| 10
| -
| 0.5
| Base.GummyWorms
|-
| [[File:PepperHabanero.png|32x32px|link=Habanero|Habanero]]
| [[Habanero]]
| 0.1
| -2
| 15
| -
| -
| 0.21
| Base.PepperHabanero
|-
| [[File:PepperHabanero_Dried.png|32x32px|link=Habanero (Dried)|Habanero (Dried)]]
| [[Habanero (Dried)]]
| 0.1
| -1
| 15
| -
| -
| 0.21
| Base.PepperHabaneroDried
|-
| [[File:CandyMolasses.png|32x32px|link=Halloween Candy|Halloween Candy]]
| [[Halloween Candy]]
| 0.1
| -5
| 160
| 33
| 0.1
| 3.5
| Base.CandyMolasses
|-
| <span class="cycle-img">[[File:Ham.png|32x32px|link=Ham|Ham]][[File:HamRotten.png|32x32px|link=Ham|Ham]]</span>
| [[Ham]]
| 1
| -60
| 1560
| 91
| 117
| 78
| Base.Ham
|-
| [[File:HamSlices.png|32x32px|link=Ham Slice|Ham Slice]]
| [[Ham Slice]]
| 0.2
| -10
| 260
| 15.16
| 19.5
| 13
| Base.HamSlice
|-
| [[File:BunsHamburger_single.png|32x32px|link=Hamburger Bun|Hamburger Bun]]
| [[Hamburger Bun]]
| 0.1
| -10
| 177
| 33
| 5.9
| 2.22
| Base.BunsHamburger_single
|-
| [[File:HardCandies.png|32x32px|link=Hard Candies|Hard Candies]]
| [[Hard Candies]]
| 0.1
| -5
| 40
| 10
| -
| 0.5
| Base.HardCandies
|-
| [[File:Snackcake_HiHis.png|32x32px|link=Hi His|Hi His]]
| [[Hi His]]
| 0.2
| -10
| 200
| 30
| 1.8
| 8
| Base.HiHis
|-
| [[File:Honeybottle.png|32x32px|link=Honey|Honey]]
| [[Honey]]
| 0.4
| -20
| 660
| 187
| -
| -
| Base.Honey
|-
| [[File:HotdogCrafted.png|32x32px|link=Hot Dog|Hot Dog]]
| [[Hot Dog]]
| 0.3
| -20
| 100
| 2
| 2
| 12
| Base.Hotdog
|-
| [[File:Hotsauce.png|32x32px|link=Hot Sauce|Hot Sauce]]
| [[Hot Sauce]]
| 0.2
| -16
| 430
| 270
| -
| -
| Base.Hotsauce
|-
| [[File:BunsHotdog_single.png|32x32px|link=Hotdog Bun|Hotdog Bun]]
| [[Hotdog Bun]]
| 0.1
| -10
| 177
| 33
| 5.9
| 2.22
| Base.BunsHotdog_single
|-
| [[File:Hotdog_single.png|32x32px|link=Hotdog Wiener|Hotdog Wiener]]
| [[Hotdog Wiener]]
| 0.15
| -10
| 65
| 1.25
| 1.25
| 2
| Base.Hotdog_single
|-
| [[File:Icecream.png|32x32px|link=Ice Cream|Ice Cream]]
| [[Ice Cream]]
| 0.2
| -30
| 1680
| 180
| 26
| 84
| Base.Icecream
|-
| [[File:IcecreamMelted.png|32x32px|link=Ice Cream|Ice Cream (Melted)]]
| [[Ice Cream|Ice Cream (Melted)]]
| 0.2
| -30
| 1680
| 180
| 26
| 84
| Base.IcecreamMelted
|-
| [[File:ConeIcecream.png|32x32px|link=Ice Cream Cone|Ice Cream Cone]]
| [[Ice Cream Cone]]
| 0.2
| -15
| 470
| 120
| 20
| 44
| Base.ConeIcecream
|-
| [[File:ConeIceCreamTopped.png|32x32px|link=Ice Cream Cone|Ice Cream Cone]]
| [[Ice Cream Cone]]
| 0.2
| -15
| 470
| 120
| 20
| 44
| Base.ConeIcecreamToppings
|-
| [[File:ConeIcecream.png|32x32px|link=Ice Cream Cone|Ice Cream Cone (Melted)]]
| [[Ice Cream Cone|Ice Cream Cone (Melted)]]
| 0.2
| -15
| 470
| 120
| 20
| 44
| Base.ConeIcecreamMelted
|-
| [[File:IcecreamSandwich.png|32x32px|link=Ice Cream Sandwich|Ice Cream Sandwich]]
| [[Ice Cream Sandwich]]
| 0.2
| -15
| 140
| 26
| 2
| 3
| Base.IcecreamSandwich
|-
| [[File:IcecreamSandwich_Melted.png|32x32px|link=Ice Cream Sandwich (Melted)|Ice Cream Sandwich (Melted)]]
| [[Ice Cream Sandwich (Melted)]]
| 0.2
| -15
| 140
| 26
| 2
| 3
| Base.IcecreamSandwich_Melted
|-
| [[File:Icing.png|32x32px|link=Icing|Icing]]
| [[Icing]]
| 0.1
| -10
| 110
| 80
| 16
| 44
| Base.Icing
|-
| <span class="cycle-img">[[File:Popcorn.png|32x32px|link=Instant Popcorn|Instant Popcorn]][[File:PopcornCooked.png|32x32px|link=Instant Popcorn|Instant Popcorn]]</span>
| [[Instant Popcorn]]
| 0.3
| -10
| 120
| 20.41
| 3.57
| 2.69
| Base.Popcorn
|-
| [[File:Jackolantern.png|32x32px|link=Jack-o'-lantern|Jack-o'-lantern]]
| [[Jack-o'-lantern]]
| 1
| -40
| 404
| 20.45
| 34.53
| 20.61
| Base.HalloweenPumpkin
|-
| [[File:PepperJalapeno.png|32x32px|link=Jalapeno|Jalapeno]]
| [[Jalapeno]]
| 0.1
| -2
| 15
| -
| -
| 0.21
| Base.PepperJalapeno
|-
| [[File:PepperJalapeno_Dried.png|32x32px|link=Jalapeno (Dried)|Jalapeno (Dried)]]
| [[Jalapeno (Dried)]]
| 0.1
| -1
| 15
| -
| -
| 0.21
| Base.PepperJalapenoDried
|-
| [[File:JarBrown.png|32x32px|link=Jar of Bell Peppers|Jar of Bell Peppers]]
| [[Jar of Bell Peppers]]
| 0.8
| -48
| 180
| 42
| 6
| -
| Base.CannedBellPepper
|-
| [[File:JarBrown.png|32x32px|link=Jar of Bell Peppers (Open)|Jar of Bell Peppers (Open)]]
| [[Jar of Bell Peppers (Open)]]
| 0.8
| -48
| 180
| 42
| 6
| -
| Base.CannedBellPepper_Open
|-
| [[File:JarGreen.png|32x32px|link=Jar of Broccoli|Jar of Broccoli]]
| [[Jar of Broccoli]]
| 0.8
| -45
| 55
| 10
| 4.5
| 0.5
| Base.CannedBroccoli
|-
| [[File:JarGreen.png|32x32px|link=Jar of Broccoli (Open)|Jar of Broccoli (Open)]]
| [[Jar of Broccoli (Open)]]
| 0.8
| -45
| 55
| 10
| 4.5
| 0.5
| Base.CannedBroccoli_Open
|-
| [[File:JarGreen.png|32x32px|link=Jar of Cabbage|Jar of Cabbage]]
| [[Jar of Cabbage]]
| 0.8
| -48
| 360
| 82
| 18
| 1.4
| Base.CannedCabbage
|-
| [[File:JarGreen.png|32x32px|link=Jar of Cabbage (Open)|Jar of Cabbage (Open)]]
| [[Jar of Cabbage (Open)]]
| 0.8
| -48
| 360
| 82
| 18
| 1.4
| Base.CannedCabbage_Open
|-
| [[File:JarBrown.png|32x32px|link=Jar of Carrots|Jar of Carrots]]
| [[Jar of Carrots]]
| 0.8
| -40
| 125
| 30
| 3
| 0.75
| Base.CannedCarrots
|-
| [[File:JarBrown.png|32x32px|link=Jar of Carrots (Open)|Jar of Carrots (Open)]]
| [[Jar of Carrots (Open)]]
| 0.8
| -40
| 125
| 30
| 3
| 0.75
| Base.CannedCarrots_Open
|-
| [[File:JamPurple.png|32x32px|link=Jar of Eggplants|Jar of Eggplants]]
| [[Jar of Eggplants]]
| 0.8
| -48
| 342
| 81
| 13.5
| 2.4
| Base.CannedEggplant
|-
| [[File:JamPurple.png|32x32px|link=Jar of Eggplants (Open)|Jar of Eggplants (Open)]]
| [[Jar of Eggplants (Open)]]
| 0.8
| -48
| 342
| 81
| 13.5
| 2.4
| Base.CannedEggplant_Open
|-
| [[File:Jar_Roe.png|32x32px|link=Jar of Fish Roe|Jar of Fish Roe]]
| [[Jar of Fish Roe]]
| 0.8
| -48
| 56
| 14
| 5.2
| 0.8
| Base.CannedRoe
|-
| [[File:JarWhite.png|32x32px|link=Jar of Leeks|Jar of Leeks]]
| [[Jar of Leeks]]
| 0.8
| -48
| 216
| 560
| 15.2
| 1.2
| Base.CannedLeek
|-
| [[File:JarWhite.png|32x32px|link=Jar of Leeks (Open)|Jar of Leeks (Open)]]
| [[Jar of Leeks (Open)]]
| 0.8
| -48
| 216
| 560
| 15.2
| 1.2
| Base.CannedLeek_Open
|-
| [[File:JarWhite.png|32x32px|link=Jar of Potatoes|Jar of Potatoes]]
| [[Jar of Potatoes]]
| 0.8
| -48
| 210
| 45
| 9
| 0.45
| Base.CannedPotato
|-
| [[File:JarWhite.png|32x32px|link=Jar of Potatoes (Open)|Jar of Potatoes (Open)]]
| [[Jar of Potatoes (Open)]]
| 0.8
| -48
| 210
| 45
| 9
| 0.45
| Base.CannedPotato_Open
|-
| [[File:JarBrown.png|32x32px|link=Jar of Radishes|Jar of Radishes]]
| [[Jar of Radishes]]
| 0.8
| -45
| 15
| 2.25
| -
| -
| Base.CannedRedRadish
|-
| [[File:JarBrown.png|32x32px|link=Jar of Radishes (Open)|Jar of Radishes (Open)]]
| [[Jar of Radishes (Open)]]
| 0.8
| -45
| 15
| 2.25
| -
| -
| Base.CannedRedRadish_Open
|-
| [[File:JarBrown.png|32x32px|link=Jar of Tomatoes|Jar of Tomatoes]]
| [[Jar of Tomatoes]]
| 0.8
| -48
| 56
| 14
| 5.2
| 0.8
| Base.CannedTomato
|-
| [[File:JarBrown.png|32x32px|link=Jar of Tomatoes (Open)|Jar of Tomatoes (Open)]]
| [[Jar of Tomatoes (Open)]]
| 0.8
| -48
| 56
| 14
| 5.2
| 0.8
| Base.CannedTomato_Open
|-
| [[File:DoughnutJelly.png|32x32px|link=Jelly Donut|Jelly Donut]]
| [[Jelly Donut]]
| 0.1
| -7
| 180
| 35
| 3
| 15
| Base.DoughnutJelly
|-
| [[File:JellyRoll.png|32x32px|link=Jelly Roll|Jelly Roll]]
| [[Jelly Roll]]
| 0.1
| -7
| 230
| 41
| 1
| 7
| Base.JellyRoll
|-
| [[File:JellyBeans.png|32x32px|link=Jellybeans|Jellybeans]]
| [[Jellybeans]]
| 0.1
| -5
| 40
| 10
| -
| 0.5
| Base.JellyBeans
|-
| [[File:Jujujubes.png|32x32px|link=Jujubes|Jujubes]]
| [[Jujubes]]
| 0.1
| -5
| 40
| 10
| -
| 0.5
| Base.Jujubes
|-
| <span class="cycle-img">[[File:Kale.png|32x32px|link=Kale|Kale]][[File:KaleRotten.png|32x32px|link=Kale|Kale]]</span>
| [[Kale]]
| 0.2
| -16
| 178
| 41.41
| 9.14
| 0.71
| Base.Kale
|-
| [[File:Ketchup.png|32x32px|link=Ketchup|Ketchup]]
| [[Ketchup]]
| 0.2
| -20
| 1480
| 370
| -
| -
| Base.Ketchup
|-
| [[File:Pie_Keylime.png|32x32px|link=Key Lime Pie Slice|Key Lime Pie Slice]]
| [[Key Lime Pie Slice]]
| 0.5
| -30
| 404
| 20.45
| 54.53
| 20.61
| Base.PieKeyLime
|-
| [[File:DriedKidneyBeans.png|32x32px|link=Kidney Beans (Dried)|Kidney Beans (Dried)]]
| [[Kidney Beans (Dried)]]
| 2
| -60
| 3265
| 508
| 272
| 13
| Base.DriedKidneyBeans
|-
| [[File:Insect_Ladybug.png|32x32px|link=Ladybug|Ladybug]]
| [[Ladybug]]
| 0.01
| -1
| 1.5
| -
| 0.25
| 0.05
| Base.Ladybug
|-
| [[File:Lard.png|32x32px|link=Lard|Lard]]
| [[Lard]]
| 0.3
| -24
| 4095
| -
| -
| 454
| Base.Lard
|-
| [[File:Fish_BassLargemouth.png|32x32px|link=Largemouth Bass|Largemouth Bass]]
| [[Largemouth Bass]]
| 0.4
| -15
| 159
| 1
| 35
| 1
| Base.LargemouthBass
|-
| [[File:Bouquet_Lavender.png|32x32px|link=Lavender|Lavender]]
| [[Lavender]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.Lavender
|-
| [[File:Petals_Lavender.png|32x32px|link=Lavender Petals (Dried)|Lavender Petals (Dried)]]
| [[Lavender Petals (Dried)]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.LavenderPetalsDried
|-
| [[File:leech.png|32x32px|link=Leech|Leech]]
| [[Leech]]
| 0.1
| -1
| 90
| 2.11
| 17.41
| 1.9
| Base.Leech
|-
| <span class="cycle-img">[[File:Leek.png|32x32px|link=Leek|Leek]][[File:LeekRotten.png|32x32px|link=Leek|Leek]]</span>
| [[Leek]]
| 0.2
| -12
| 54
| 140
| 1.3
| 0.3
| Base.Leek
|-
| <span class="cycle-img">[[File:Lemon.png|32x32px|link=Lemon|Lemon]][[File:LemonRotten.png|32x32px|link=Lemon|Lemon]]</span>
| [[Lemon]]
| 0.2
| -10
| 17
| 5.41
| 0.64
| 0.17
| Base.Lemon
|-
| [[File:LemonBar.png|32x32px|link=Lemon Bar|Lemon Bar]]
| [[Lemon Bar]]
| 0.1
| -7
| 156
| 22
| 2
| 11
| Base.LemonBar
|-
| [[File:Pie_Lemonmeringue.png|32x32px|link=Lemon Meringue Pie Slice|Lemon Meringue Pie Slice]]
| [[Lemon Meringue Pie Slice]]
| 0.5
| -30
| 404
| 20.45
| 54.53
| 20.61
| Base.PieLemonMeringue
|-
| [[File:LemonGrass.png|32x32px|link=Lemongrass|Lemongrass]]
| [[Lemongrass]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.LemonGrass
|-
| [[File:DriedLentils.png|32x32px|link=Lentils (Dried)|Lentils (Dried)]]
| [[Lentils (Dried)]]
| 2
| -60
| 3000
| 540
| 220
| -
| Base.DriedLentils
|-
| <span class="cycle-img">[[File:Lettuce.png|32x32px|link=Lettuce|Lettuce]][[File:LettuceRotten.png|32x32px|link=Lettuce|Lettuce]]</span>
| [[Lettuce]]
| 0.2
| -15
| 54
| 10.33
| 4.9
| 0.54
| Base.Lettuce
|-
| [[File:LicoriceBlack.png|32x32px|link=Licorice|Licorice]]
| [[Licorice]]
| 0.1
| -2
| 22
| 7
| -
| -
| Base.LicoriceBlack
|-
| [[File:LicoriceRed.png|32x32px|link=Licorice|Licorice]]
| [[Licorice]]
| 0.1
| -2
| 22
| 7
| -
| -
| Base.LicoriceRed
|-
| [[File:Allsorts.png|32x32px|link=Licorice Allsorts|Licorice Allsorts]]
| [[Licorice Allsorts]]
| 0.2
| -10
| 16.6
| 4.33
| -
| -
| Base.Allsorts
|-
| <span class="cycle-img">[[File:Lime.png|32x32px|link=Lime|Lime]][[File:LimeRotten.png|32x32px|link=Lime|Lime]]</span>
| [[Lime]]
| 0.2
| -10
| 17
| 5.41
| 0.64
| 0.17
| Base.Lime
|-
| [[File:FishMinnow.png|32x32px|link=Little Bait Fish|Little Bait Fish]]
| [[Little Bait Fish]]
| 0.1
| -3
| 30
| -
| 8.52
| 1.5
| Base.BaitFish
|-
| <span class="cycle-img">[[File:Lobster.png|32x32px|link=Lobster|Lobster]][[File:LobsterRotten.png|32x32px|link=Lobster|Lobster]][[File:LobsterCooked.png|32x32px|link=Lobster|Lobster]][[File:LobsterBurnt.png|32x32px|link=Lobster|Lobster]]</span>
| [[Lobster]]
| 0.4
| -40
| 120
| -
| 28
| 7
| Base.Lobster
|-
| [[File:Lollipop.png|32x32px|link=Lollipop|Lollipop]]
| [[Lollipop]]
| 0.1
| -5
| 40
| 10
| -
| 0.5
| Base.Lollipop
|-
| [[File:Macandcheese.png|32x32px|link=Mac and Cheese|Mac and Cheese]]
| [[Mac and Cheese]]
| 0.5
| -
| 690
| 126
| 21
| 12
| Base.Macandcheese
|-
| <span class="cycle-img">[[File:Macaroni.png|32x32px|link=Macaroni|Macaroni]][[File:MacaroniCooked.png|32x32px|link=Macaroni|Macaroni]]</span>
| [[Macaroni]]
| 2
| -60
| 3360
| 656
| 112
| 16
| Base.Macaroni
|-
| [[File:Insect_Maggots.png|32x32px|link=Maggots|Maggots]]
| [[Maggots]]
| 0.01
| -1
| 1.5
| -
| 0.25
| 0.05
| Base.Maggots
|-
| [[File:Maki.png|32x32px|link=Maki|Maki]]
| [[Maki]]
| 0.1
| -10
| 12
| 5
| 2
| 1
| Base.Maki
|-
| <span class="cycle-img">[[File:Mango.png|32x32px|link=Mango|Mango]][[File:MangoRotten.png|32x32px|link=Mango|Mango]]</span>
| [[Mango]]
| 0.3
| -20
| 252
| 78.7
| 3.89
| 1.09
| Base.Mango
|-
| [[File:MapleSyrup.png|32x32px|link=Maple Syrup|Maple Syrup]]
| [[Maple Syrup]]
| 0.2
| -45
| 1100
| 270
| -
| -
| Base.MapleSyrup
|-
| [[File:Margerine.png|32x32px|link=Margarine|Margarine]]
| [[Margarine]]
| 0.3
| -24
| 3255
| 4
| 1
| 368
| Base.Margarine
|-
| <span class="cycle-img">[[File:Marigold.png|32x32px|link=Marigold|Marigold]][[File:MarigoldRotten.png|32x32px|link=Marigold|Marigold]]</span>
| [[Marigold]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.Marigold
|-
| [[File:Marigold_Dried.png|32x32px|link=Marigold (Dried)|Marigold (Dried)]]
| [[Marigold (Dried)]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.MarigoldDried
|-
| [[File:Marinarai.png|32x32px|link=Marinara|Marinara]]
| [[Marinara]]
| 0.2
| -10
| 350
| 55
| 10
| 7.5
| Base.Marinara
|-
| [[File:JamMarmalade.png|32x32px|link=Marmalade|Marmalade]]
| [[Marmalade]]
| 0.2
| -30
| 550
| 130
| 1
| -
| Base.JamMarmalade
|-
| <span class="cycle-img">[[File:Marshmallows.png|32x32px|link=Marshmallows|Marshmallows]][[File:MarshmallowsCooked.png|32x32px|link=Marshmallows|Marshmallows]][[File:MarshmallowsBurnt.png|32x32px|link=Marshmallows|Marshmallows]]</span>
| [[Marshmallows]]
| 0.1
| -5
| 30
| 8
| 0.5
| -
| Base.Marshmallows
|-
| <span class="cycle-img">[[File:TZ_MayonnaiseFull.png|32x32px|link=Mayonnaise|Mayonnaise]][[File:TZ_MayonnaiseFullRotten.png|32x32px|link=Mayonnaise|Mayonnaise]]</span>
| [[Mayonnaise]]
| 0.5
| -30
| 3000
| -
| -
| 330
| Base.MayonnaiseFull
|-
| [[File:MeatDumpling.png|32x32px|link=Meat Dumpling|Meat Dumpling]]
| [[Meat Dumpling]]
| 0.1
| -10
| 28
| 8
| 15
| 3
| Base.MeatDumpling
|-
| [[File:MeatSteamBun.png|32x32px|link=Meat Steam Bun|Meat Steam Bun]]
| [[Meat Steam Bun]]
| 0.1
| -15
| 35
| 12
| 18
| 4
| Base.MeatSteamBun
|-
| [[File:Chocolate.png|32x32px|link=Milk Chocolate Bar|Milk Chocolate Bar]]
| [[Milk Chocolate Bar]]
| 0.2
| -20
| 850
| 110
| 10
| 66
| Base.Chocolate
|-
| [[File:Insect_Millipede1.png|32x32px|link=Millipede|Millipede]]
| [[Millipede]]
| 0.1
| -1
| 60
| 3.5
| 15.21
| 6.5
| Base.Millipede
|-
| [[File:Insect_Millipede2.png|32x32px|link=Millipede|Millipede]]
| [[Millipede]]
| 0.1
| -1
| 60
| 3.5
| 15.21
| 6.5
| Base.Millipede2
|-
| <span class="cycle-img">[[File:Mint.png|32x32px|link=Mint|Mint]][[File:MintRotten.png|32x32px|link=Mint|Mint]]</span>
| [[Mint]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.MintHerb
|-
| <span class="cycle-img">[[File:Mint.png|32x32px|link=Mint (Dried)|Mint (Dried)]][[File:MintRotten.png|32x32px|link=Mint (Dried)|Mint (Dried)]]</span>
| [[Mint (Dried)]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.MintHerbDried
|-
| [[File:MintCandy.png|32x32px|link=Mint Candy|Mint Candy]]
| [[Mint Candy]]
| 0.1
| -2
| 60
| 15
| -
| -
| Base.MintCandy
|-
| [[File:Modjeska.png|32x32px|link=Modjeska|Modjeska]]
| [[Modjeska]]
| 0.1
| -10
| 60
| 15
| -
| -
| Base.Modjeska
|-
| <span class="cycle-img">[[File:MouseDead.png|32x32px|link=Mouse Pups (Dead)|Mouse Pups (Dead)]][[File:MouseDeadRotten.png|32x32px|link=Mouse Pups (Dead)|Mouse Pups (Dead)]]</span>
| [[Mouse Pups (Dead)]]
| 0.03
| -5
| 110
| 0.35
| 4.2
| 1.58
| Base.DeadMousePups
|-
| [[File:MuffinGeneric.png|32x32px|link=Muffin|Muffin]]
| [[Muffin]]
| 0.1
| -7
| 120
| 10.45
| 14.53
| 12.61
| Base.MuffinGeneric
|-
| [[File:MushroomGeneric1.png|32x32px|link=Mushrooms|Mushrooms]]
| [[Mushrooms]]
| 0.2
| -13
| 30
| 2.12
| 2.04
| 0.24
| Base.MushroomGeneric1
|-
| [[File:MushroomGeneric2.png|32x32px|link=Mushrooms|Mushrooms]]
| [[Mushrooms]]
| 0.2
| -13
| 30
| 2.12
| 2.04
| 0.24
| Base.MushroomGeneric2
|-
| [[File:MushroomGeneric3.png|32x32px|link=Mushrooms|Mushrooms]]
| [[Mushrooms]]
| 0.2
| -15
| 32
| 2.56
| 2.36
| 0.32
| Base.MushroomGeneric3
|-
| [[File:MushroomGeneric4.png|32x32px|link=Mushrooms|Mushrooms]]
| [[Mushrooms]]
| 0.2
| -13
| 30
| 2.12
| 2.04
| 0.24
| Base.MushroomGeneric4
|-
| [[File:MushroomGeneric5.png|32x32px|link=Mushrooms|Mushrooms]]
| [[Mushrooms]]
| 0.2
| -15
| 32
| 2.56
| 2.36
| 0.32
| Base.MushroomGeneric5
|-
| [[File:MushroomGeneric6.png|32x32px|link=Mushrooms|Mushrooms]]
| [[Mushrooms]]
| 0.2
| -13
| 30
| 2.12
| 2.04
| 0.24
| Base.MushroomGeneric6
|-
| [[File:MushroomGeneric7.png|32x32px|link=Mushrooms|Mushrooms]]
| [[Mushrooms]]
| 0.2
| -13
| 32
| 2.12
| 2.04
| 0.24
| Base.MushroomGeneric7
|-
| [[File:MushroomButton.png|32x32px|link=Mushrooms|Mushrooms]]
| [[Mushrooms]]
| 0.2
| -7
| 15
| 1.06
| 1.02
| 0.12
| Base.MushroomsButton
|-
| [[File:Fish_Muskellunge.png|32x32px|link=Muskellunge|Muskellunge]]
| [[Muskellunge]]
| 0.4
| -15
| 159
| 1
| 35
| 1
| Base.Muskellunge
|-
| <span class="cycle-img">[[File:Mussels.png|32x32px|link=Mussels|Mussels]][[File:MusselsCooked.png|32x32px|link=Mussels|Mussels]]</span>
| [[Mussels]]
| 0.1
| -5
| 15
| 10
| 22
| 4
| Base.Mussels
|-
| [[File:Mustard.png|32x32px|link=Mustard|Mustard]]
| [[Mustard]]
| 0.2
| -20
| 510
| -
| -
| -
| Base.Mustard
|-
| <span class="cycle-img">[[File:Mutton.png|32x32px|link=Mutton Chop|Mutton Chop]][[File:MuttonRotten.png|32x32px|link=Mutton Chop|Mutton Chop]][[File:MuttonCooked.png|32x32px|link=Mutton Chop|Mutton Chop]][[File:MuttonOverdone.png|32x32px|link=Mutton Chop|Mutton Chop]]</span>
| [[Mutton Chop]]
| 0.3
| -30
| 234
| 0.08
| 33
| 11
| Base.MuttonChop
|-
| [[File:Dip_NachoCheese.png|32x32px|link=Nacho Cheese|Nacho Cheese]]
| [[Nacho Cheese]]
| 0.2
| -16
| 630
| 56
| 14
| 42
| Base.Dip_NachoCheese
|-
| [[File:Nettle.png|32x32px|link=Nettles|Nettles]]
| [[Nettles]]
| 0.1
| -4
| 50
| 15
| 2
| -
| Base.Nettles
|-
| [[File:CandyNovapops.png|32x32px|link=Novapops Candy|Novapops Candy]]
| [[Novapops Candy]]
| 0.1
| -5
| 120
| 24
| -
| 2.5
| Base.CandyNovapops
|-
| [[File:CookiesOatmeal.png|32x32px|link=Oatmeal Cookie|Oatmeal Cookie]]
| [[Oatmeal Cookie]]
| 0.1
| -5
| 110
| 20
| 1
| 6
| Base.CookiesOatmeal
|-
| [[File:OilOlive.png|32x32px|link=Olive Oil|Olive Oil]]
| [[Olive Oil]]
| 0.2
| -30
| 2480
| -
| -
| 150
| Base.OilOlive
|-
| [[File:Olives.png|32x32px|link=Olives|Olives]]
| [[Olives]]
| 0.1
| -5
| 47
| 2
| -
| 4.7
| Base.Olives
|-
| [[File:EggOmelette.png|32x32px|link=Omelette|Omelette]]
| [[Omelette]]
| 0.1
| -20
| 120
| 0.52
| 10.55
| 6.18
| Base.EggOmelette
|-
| [[File:PanFull.png|32x32px|link=Omelette|Omelette]]
| [[Omelette]]
| 0.5
| -14
| 123
| 2
| 11
| 8.33
| Base.OmeletteRecipe
|-
| <span class="cycle-img">[[File:FryingPan_Forged_Eggs.png|32x32px|link=Omelette|Omelette]][[File:FryingPan_Forged_EggsRotten.png|32x32px|link=Omelette|Omelette]][[File:FryingPan_Forged_EggsCooked.png|32x32px|link=Omelette|Omelette]][[File:FryingPan_Forged_EggsBurnt.png|32x32px|link=Omelette|Omelette]]</span>
| [[Omelette]]
| 0.5
| -14
| 123
| 2
| 11
| 8.33
| Base.OmeletteRecipeForged
|-
| [[File:Onigiri.png|32x32px|link=Onigiri|Onigiri]]
| [[Onigiri]]
| 0.1
| -12
| 25
| 12
| 18
| 4
| Base.Onigiri
|-
| <span class="cycle-img">[[File:Onion.png|32x32px|link=Onion|Onion]][[File:OnionRotten.png|32x32px|link=Onion|Onion]]</span>
| [[Onion]]
| 0.2
| -10
| 28
| 6.54
| 0.77
| 0.07
| Base.Onion
|-
| [[File:Jar_Roe.png|32x32px|link=Opened Jar of Fish Roe|Opened Jar of Fish Roe]]
| [[Opened Jar of Fish Roe]]
| 0.8
| -10
| 150
| -
| 14
| 11
| Base.CannedRoe_Open
|-
| <span class="cycle-img">[[File:Orange.png|32x32px|link=Orange|Orange]][[File:OrangeRotten.png|32x32px|link=Orange|Orange]]</span>
| [[Orange]]
| 0.2
| -12
| 65
| 16.27
| 1
| 0.3
| Base.Orange
|-
| [[File:HerbOregano.png|32x32px|link=Oregano|Oregano]]
| [[Oregano]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.Oregano
|-
| [[File:Seasoning_Oregano.png|32x32px|link=Oregano (Dried)|Oregano (Dried)]]
| [[Oregano (Dried)]]
| 0.2
| -20
| 0.4
| -
| -
| -
| Base.Seasoning_Oregano
|-
| [[File:DriedHerbs_generic.png|32x32px|link=Oregano (Dried)|Oregano (Dried)]]
| [[Oregano (Dried)]]
| 0.1
| -5
| 0.1
| -
| -
| -
| Base.OreganoDried
|-
| <span class="cycle-img">[[File:Oysters.png|32x32px|link=Oysters|Oysters]][[File:OystersCooked.png|32x32px|link=Oysters|Oysters]]</span>
| [[Oysters]]
| 0.1
| -5
| 15
| 10
| 22
| 4
| Base.Oysters
|-
| [[File:OystersFried.png|32x32px|link=Oysters (Fried)|Oysters (Fried)]]
| [[Oysters (Fried)]]
| 0.1
| -6
| 25
| 11
| 20
| 4
| Base.OystersFried
|-
| [[File:BunsHamburger.png|32x32px|link=Pack of Hamburger Buns|Pack of Hamburger Buns]]
| [[Pack of Hamburger Buns]]
| 0.4
| -
| 708
| 132
| 23.6
| 8.88
| Base.BunsHamburger
|-
| [[File:BunsHotdog.png|32x32px|link=Pack of Hotdog Buns|Pack of Hotdog Buns]]
| [[Pack of Hotdog Buns]]
| 0.3
| -
| 532
| 99
| 17.7
| 6.66
| Base.BunsHotdog
|-
| [[File:Hotdog.png|32x32px|link=Pack of Hotdogs|Pack of Hotdogs]]
| [[Pack of Hotdogs]]
| 0.6
| -
| 270
| 5
| 5
| 8
| Base.HotdogPack
|-
| [[File:Frozen_Corn.png|32x32px|link=Packaged Corn|Packaged Corn]]
| [[Packaged Corn]]
| 0.6
| -20
| 396
| 94
| 15
| 5
| Base.CornFrozen
|-
| [[File:Peas.png|32x32px|link=Packaged Peas|Packaged Peas]]
| [[Packaged Peas]]
| 0.6
| -20
| 119
| 20.45
| 7.95
| 0.85
| Base.Peas
|-
| [[File:Frozen_MixedVegetables.png|32x32px|link=Packaged Vegetables|Packaged Vegetables]]
| [[Packaged Vegetables]]
| 0.6
| -20
| 271
| 37
| 9
| -
| Base.MixedVegetables
|-
| [[File:Fish_Paddlefish.png|32x32px|link=Paddlefish|Paddlefish]]
| [[Paddlefish]]
| 0.4
| -15
| 159
| 1
| 35
| 1
| Base.Paddlefish
|-
| [[File:PancakesFruit.png|32x32px|link=Pancakes|Pancakes]]
| [[Pancakes]]
| 0.3
| -20
| 210
| 42
| 6
| 2
| Base.PancakesRecipe
|-
| [[File:Pancakes.png|32x32px|link=Pancakes|Pancakes]]
| [[Pancakes]]
| 0.3
| -16
| 210
| 42
| 6
| 2
| Base.Pancakes
|-
| [[File:Pancakes.png|32x32px|link=Pancakes|Pancakes]]
| [[Pancakes]]
| 0.3
| -20
| 210
| 42
| 6
| 2
| Base.PancakesCraft
|-
| [[File:HerbParsley.png|32x32px|link=Parsley|Parsley]]
| [[Parsley]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.Parsley
|-
| [[File:Seasoning_Parsley.png|32x32px|link=Parsley (Dried)|Parsley (Dried)]]
| [[Parsley (Dried)]]
| 0.2
| -20
| 0.4
| -
| -
| -
| Base.Seasoning_Parsley
|-
| [[File:DriedHerbs_generic.png|32x32px|link=Parsley (Dried)|Parsley (Dried)]]
| [[Parsley (Dried)]]
| 0.1
| -5
| 0.1
| -
| -
| -
| Base.ParsleyDried
|-
| [[File:SpagettiRaw.png|32x32px|link=Pasta|Pasta]]
| [[Pasta]]
| 2
| -60
| 3360
| 656
| 112
| 16
| Base.Pasta
|-
| [[File:SaucepanFilled.png|32x32px|link=Pasta (crafted pan)|Pasta]]
| [[Pasta (crafted pan)|Pasta]]
| 3
| -10
| 560
| 109.3
| 18.66
| 2.66
| Base.PastaPan
|-
| [[File:CopperPot_Pasta.png|32x32px|link=Pasta|Pasta]]
| [[Pasta]]
| 3
| -10
| 560
| 109.3
| 18.66
| 2.66
| Base.PastaPanCopper
|-
| [[File:PotFull.png|32x32px|link=Pasta (crafted pot)|Pasta]]
| [[Pasta (crafted pot)|Pasta]]
| 3
| -10
| 560
| 109.3
| 18.66
| 2.66
| Base.PastaPot
|-
| <span class="cycle-img">[[File:Pot_Forged_Pasta.png|32x32px|link=Pasta|Pasta]][[File:Pot_Forged_PastaRotten.png|32x32px|link=Pasta|Pasta]]</span>
| [[Pasta]]
| 3
| -10
| 560
| 109.3
| 18.66
| 2.66
| Base.PastaPotForged
|-
| <span class="cycle-img">[[File:Peach.png|32x32px|link=Peach|Peach]][[File:PeachRotten.png|32x32px|link=Peach|Peach]]</span>
| [[Peach]]
| 0.2
| -12
| 58
| 14.31
| 1.36
| 0.38
| Base.Peach
|-
| [[File:PeanutButter.png|32x32px|link=Peanut Butter|Peanut Butter]]
| [[Peanut Butter]]
| 0.3
| -25
| 2660
| 128
| 84
| 224
| Base.PeanutButter
|-
| [[File:Peanut.png|32x32px|link=Peanuts|Peanuts]]
| [[Peanuts]]
| 0.2
| -8
| 161
| 4.57
| 7.31
| 13.96
| Base.Peanuts
|-
| <span class="cycle-img">[[File:Pear.png|32x32px|link=Pear|Pear]][[File:PearRotten.png|32x32px|link=Pear|Pear]]</span>
| [[Pear]]
| 0.2
| -16
| 75
| 20.13
| 0.27
| 0.21
| Base.Pear
|-
| [[File:Peppermint.png|32x32px|link=Peppermint Candy|Peppermint Candy]]
| [[Peppermint Candy]]
| 0.1
| -2
| 16.6
| 4.33
| -
| -
| Base.Peppermint
|-
| [[File:Pepperoni.png|32x32px|link=Pepperoni|Pepperoni]]
| [[Pepperoni]]
| 0.1
| -20
| 180
| -
| 15.62
| 4.35
| Base.Pepperoni
|-
| [[File:Perogies.png|32x32px|link=Perogies|Perogies]]
| [[Perogies]]
| 0.1
| -7
| 160
| 31
| 5
| 2
| Base.Perogies
|-
| [[File:Pickles.png|32x32px|link=Pickle|Pickle]]
| [[Pickle]]
| 0.1
| -6
| 5
| 1
| -
| -
| Base.Pickles
|-
| <span class="cycle-img">[[File:PieWhole.png|32x32px|link=Pie (savory)|Pie]][[File:PieWholeCooked.png|32x32px|link=Pie (savory)|Pie]][[File:PieWholeOverdone.png|32x32px|link=Pie (savory)|Pie]]</span>
| [[Pie (savory)|Pie]]
| 0.5
| -15
| 189
| 11.2
| 9.6
| 11.5
| Base.PieWholeRaw
|-
| <span class="cycle-img">[[File:PieWhole.png|32x32px|link=Pie (sweet)|Pie]][[File:PieWholeCooked.png|32x32px|link=Pie (sweet)|Pie]][[File:PieWholeOverdone.png|32x32px|link=Pie (sweet)|Pie]]</span>
| [[Pie (sweet)|Pie]]
| 0.5
| -15
| 189
| 11.2
| 9.6
| 11.5
| Base.PieWholeRawSweet
|-
| <span class="cycle-img">[[File:PieWhole.png|32x32px|link=Pie Preparation|Pie Preparation]][[File:PieWholeCooked.png|32x32px|link=Pie Preparation|Pie Preparation]][[File:PieWholeOverdone.png|32x32px|link=Pie Preparation|Pie Preparation]]</span>
| [[Pie Preparation]]
| 0.5
| -15
| 189
| 11.2
| 9.6
| 11.5
| Base.PiePrep
|-
| [[File:Insect_Pillbug.png|32x32px|link=Pillbug|Pillbug]]
| [[Pillbug]]
| 0.01
| -1
| 1.5
| -
| 0.25
| 0.05
| Base.Pillbug
|-
| <span class="cycle-img">[[File:Pineapple.png|32x32px|link=Pineapple|Pineapple]][[File:PineappleRotten.png|32x32px|link=Pineapple|Pineapple]]</span>
| [[Pineapple]]
| 0.3
| -24
| 452
| 118.7
| 4.89
| 1.09
| Base.Pineapple
|-
| [[File:PizzaWhole.png|32x32px|link=Pizza|Pizza]]
| [[Pizza]]
| 1.5
| -80
| 1529
| 231
| 41.8
| 34
| Base.PizzaRecipe
|-
| [[File:PizzaWhole.png|32x32px|link=Pizza|Pizza]]
| [[Pizza]]
| 1.8
| -150
| 5940
| 720
| 252
| 234
| Base.PizzaWhole
|-
| [[File:Pizza.png|32x32px|link=Pizza Slice|Pizza Slice]]
| [[Pizza Slice]]
| 0.3
| -25
| 990
| 120
| 42
| 39
| Base.Pizza
|-
| [[File:Muffintray_Batter.png|32x32px|link=Plain Muffins|Plain Muffins]]
| [[Plain Muffins]]
| 1.5
| -30
| 520
| 50.45
| 54.53
| 52.61
| Base.BakingTray_Muffin
|-
| [[File:Muffintray_Batter.png|32x32px|link=Plain Muffins|Plain Muffins]]
| [[Plain Muffins]]
| 1.5
| -30
| 520
| 50.45
| 54.53
| 52.61
| Base.BakingTray_Muffin_Recipe
|-
| [[File:Snackcake_Plonkies.png|32x32px|link=Plonkies|Plonkies]]
| [[Plonkies]]
| 0.2
| -10
| 200
| 30
| 1.8
| 8
| Base.Plonkies
|-
| [[File:Bouquet_Poppy.png|32x32px|link=Poppies|Poppies]]
| [[Poppies]]
| 0.1
| -
| 0.1
| -
| -
| -
| Base.Poppies
|-
| [[File:BagelPoppy.png|32x32px|link=Poppy Bagel|Poppy Bagel]]
| [[Poppy Bagel]]
| 0.1
| -10
| 177
| 33
| 5.9
| 2.22
| Base.BagelPoppy
|-
| [[File:PoppySeeds.png|32x32px|link=Poppy Seeds|Poppy Seeds]]
| [[Poppy Seeds]]
| 0.1
| -1
| 31
| 3
| 1.6
| 2
| Base.PoppySeed
|-
| [[File:Popsicle.png|32x32px|link=Popsicle|Popsicle]]
| [[Popsicle]]
| 0.2
| -15
| 80
| 22
| -
| -
| Base.Popsicle
|-
| [[File:Popsicle_Melted.png|32x32px|link=Popsicle (Melted)|Popsicle (Melted)]]
| [[Popsicle (Melted)]]
| 0.2
| -15
| 80
| 22
| -
| -
| Base.Popsicle_Melted
|-
| <span class="cycle-img">[[File:PorkLoin.png|32x32px|link=Pork|Pork]][[File:PorkLoinRotten.png|32x32px|link=Pork|Pork]][[File:PorkLoinCooked.png|32x32px|link=Pork|Pork]][[File:PorkLoinOverdone.png|32x32px|link=Pork|Pork]]</span>
| [[Pork]]
| 0.5
| -60
| 300
| -
| 50
| 12
| Base.Pork
|-
| <span class="cycle-img">[[File:Porkchop.png|32x32px|link=Pork Chop|Pork Chop]][[File:PorkchopRotten.png|32x32px|link=Pork Chop|Pork Chop]][[File:PorkchopCooked.png|32x32px|link=Pork Chop|Pork Chop]][[File:PorkchopOverdone.png|32x32px|link=Pork Chop|Pork Chop]]</span>
| [[Pork Chop]]
| 0.3
| -30
| 150
| -
| 25
| 6
| Base.PorkChop
|-
| [[File:PorkRinds.png|32x32px|link=Pork Rinds|Pork Rinds]]
| [[Pork Rinds]]
| 0.1
| -5
| 240
| 24
| 1.5
| 15
| Base.PorkRinds
|-
| [[File:PotFull.png|32x32px|link=Soup|Pot of Soup]]
| [[Soup|Pot of Soup]]
| 3
| -30
| 202
| 25
| 14
| 4.5
| Base.PotOfSoup
|-
| [[File:PotFull.png|32x32px|link=Soup|Pot of Soup]]
| [[Soup|Pot of Soup]]
| 3
| -40
| 202
| 25
| 14
| 4.5
| Base.PotOfSoupRecipe
|-
| <span class="cycle-img">[[File:Pot_Forged_Soup.png|32x32px|link=Soup|Pot of Soup]][[File:Pot_Forged_SoupRotten.png|32x32px|link=Soup|Pot of Soup]]</span>
| [[Soup|Pot of Soup]]
| 3
| -40
| 202
| 25
| 14
| 4.5
| Base.PotForgedSoupRecipe
|-
| [[File:PotFull.png|32x32px|link=Stew|Pot of Stew]]
| [[Stew|Pot of Stew]]
| 3
| -40
| 310
| 26.3
| 3.8
| 14.5
| Base.PotOfStew
|-
| <span class="cycle-img">[[File:Pot_Forged_Stew.png|32x32px|link=Stew|Pot of Stew]][[File:Pot_Forged_StewRotten.png|32x32px|link=Stew|Pot of Stew]]</span>
| [[Stew|Pot of Stew]]
| 3
| -40
| 310
| 26.3
| 3.8
| 14.5
| Base.PotForgedStew
|-
| <span class="cycle-img">[[File:Potato.png|32x32px|link=Potato|Potato]][[File:PotatoRotten.png|32x32px|link=Potato|Potato]]</span>
| [[Potato]]
| 0.2
| -18
| 70
| 15
| 3
| 0.15
| Base.Potato
|-
| [[File:PotatoPancakes.png|32x32px|link=Potato Pancakes|Potato Pancakes]]
| [[Potato Pancakes]]
| 0.1
| -15
| 268
| 35
| 6
| 15
| Base.PotatoPancakes
|-
| [[File:Pretzel.png|32x32px|link=Pretzel|Pretzels]]
| [[Pretzel|Pretzels]]
| 0.1
| -5
| 80
| 11
| 1
| 2
| Base.Pretzel
|-
| [[File:Processedcheese.png|32x32px|link=Processed Cheese|Processed Cheese]]
| [[Processed Cheese]]
| 0.1
| -5
| 70
| -
| 4
| 6
| Base.Processedcheese
|-
| <span class="cycle-img">[[File:Pumpkin.png|32x32px|link=Pumpkin|Pumpkin]][[File:PumpkinRotten.png|32x32px|link=Pumpkin|Pumpkin]]</span>
| [[Pumpkin]]
| 1
| -40
| 404
| 20.45
| 34.53
| 20.61
| Base.Pumpkin
|-
| <span class="cycle-img">[[File:Pumpkin_Smashed.png|32x32px|link=Pumpkin Chunks|Pumpkin Chunks]][[File:Pumpkin_SmashedRotten.png|32x32px|link=Pumpkin Chunks|Pumpkin Chunks]][[File:Pumpkin_Smashed_Rotten.png|32x32px|link=Pumpkin Chunks|Pumpkin Chunks]]</span>
| [[Pumpkin Chunks]]
| 0.2
| -8
| 80
| 4.09
| 6.9
| 4.12
| Base.PumpkinSmashed
|-
| [[File:PiePumpkin.png|32x32px|link=Pumpkin Pie Slice|Pumpkin Pie Slice]]
| [[Pumpkin Pie Slice]]
| 0.5
| -30
| 404
| 20.45
| 54.53
| 20.61
| Base.PiePumpkin
|-
| <span class="cycle-img">[[File:PumpkinSeeds.png|32x32px|link=Pumpkin Seeds|Pumpkin Seeds]][[File:PumpkinSeedsCooked.png|32x32px|link=Pumpkin Seeds|Pumpkin Seeds]][[File:PumpkinSeedsBurnt.png|32x32px|link=Pumpkin Seeds|Pumpkin Seeds]]</span>
| [[Pumpkin Seeds]]
| 0.1
| -5
| 155
| 14.12
| 4.34
| 5.48
| Base.PumpkinSeed
|-
| <span class="cycle-img">[[File:Pumpkin_Slice.png|32x32px|link=Pumpkin Slice|Pumpkin Slice]][[File:Pumpkin_SliceRotten.png|32x32px|link=Pumpkin Slice|Pumpkin Slice]][[File:Pumpkin_Slice_Rotten.png|32x32px|link=Pumpkin Slice|Pumpkin Slice]]</span>
| [[Pumpkin Slice]]
| 0.1
| -4
| 40
| 2.04
| 3.45
| 2.06
| Base.PumpkinSliced
|-
| [[File:Snackcake_QuaggaCakes.png|32x32px|link=Quagga Cakes|Quagga Cakes]]
| [[Quagga Cakes]]
| 0.2
| -10
| 200
| 30
| 1.8
| 8
| Base.QuaggaCakes
|-
| <span class="cycle-img">[[File:Rabbitmeat.png|32x32px|link=Rabbit Meat|Rabbit Meat]][[File:RabbitmeatRotten.png|32x32px|link=Rabbit Meat|Rabbit Meat]][[File:RabbitmeatCooked.png|32x32px|link=Rabbit Meat|Rabbit Meat]][[File:RabbitmeatOverdone.png|32x32px|link=Rabbit Meat|Rabbit Meat]]</span>
| [[Rabbit Meat]]
| 0.3
| -30
| 969
| 20
| 185
| 20
| Base.Rabbitmeat
|-
| <span class="cycle-img">[[File:Radish.png|32x32px|link=Radish|Radish]][[File:RadishRotten.png|32x32px|link=Radish|Radish]]</span>
| [[Radish]]
| 0.1
| -3
| 1
| 0.15
| -
| -
| Base.RedRadish
|-
| [[File:Dip_Ranch.png|32x32px|link=Ranch|Ranch]]
| [[Ranch]]
| 0.2
| -16
| 867
| 29
| 14.5
| 72
| Base.Dip_Ranch
|-
| [[File:CookieJelly.png|32x32px|link=Raspberry Shortbread Cookie|Raspberry Shortbread Cookie]]
| [[Raspberry Shortbread Cookie]]
| 0.1
| -5
| 160
| 22
| 1
| 8
| Base.CookieJelly
|-
| <span class="cycle-img">[[File:DeadRat.png|32x32px|link=Rat Baby (Dead)|Rat Baby (Dead)]][[File:DeadRatRotten.png|32x32px|link=Rat Baby (Dead)|Rat Baby (Dead)]][[File:DeadRatCooked.png|32x32px|link=Rat Baby (Dead)|Rat Baby (Dead)]]</span>
| [[Rat Baby (Dead)]]
| 0.12
| -12
| 174.6
| -
| 21.6
| 8.6
| Base.DeadRatBaby
|-
| [[File:RatKing.png|32x32px|link=Rat King (Dead)|Rat King (Dead)]]
| [[Rat King (Dead)]]
| 1
| -110
| 1620
| -
| 240
| 96
| Base.RatKing
|-
| [[File:CakeRedVelvet.png|32x32px|link=Red Velvet Cake Slice|Red Velvet Cake Slice]]
| [[Red Velvet Cake Slice]]
| 0.2
| -8
| 80
| 4
| 10
| 12
| Base.CakeRedVelvet
|-
| [[File:Fish_SunfishRedear.png|32x32px|link=Redear Sunfish|Redear Sunfish]]
| [[Redear Sunfish]]
| 0.4
| -15
| 159
| 1
| 35
| 1
| Base.RedearSunfish
|-
| [[File:RefriedBeans.png|32x32px|link=Refried Beans|Refried Beans]]
| [[Refried Beans]]
| 0.2
| -10
| 70
| 25
| 10
| 1.5
| Base.RefriedBeans
|-
| <span class="cycle-img">[[File:TZ_RemouladeFull.png|32x32px|link=Remoulade|Remoulade]][[File:TZ_RemouladeFullRotten.png|32x32px|link=Remoulade|Remoulade]]</span>
| [[Remoulade]]
| 0.5
| -10
| 150
| -
| -
| 50
| Base.RemouladeFull
|-
| [[File:PotFull.png|32x32px|link=Rice (sugar beet)|Rice]]
| [[Rice (sugar beet)|Rice]]
| 3
| -45
| 216
| 27
| 36
| -
| Base.SugarBeetPulpPot
|-
| [[File:PotFull.png|32x32px|link=Rice (sugar beet)|Rice]]
| [[Rice (sugar beet)|Rice]]
| 3
| -30
| 387
| 100
| -
| -
| Base.SugarBeetSyrupPot
|-
| [[File:PotFull.png|32x32px|link=Rice (sugar beet)|Rice]]
| [[Rice (sugar beet)|Rice]]
| 3
| -30
| 387
| 100
| -
| -
| Base.SugarBeetSugarPot
|-
| [[File:RiceRaw.png|32x32px|link=Rice|Rice]]
| [[Rice]]
| 2
| -60
| 2880
| 648
| 72
| -
| Base.Rice
|-
| [[File:SaucepanFilled.png|32x32px|link=Rice (crafted pan)|Rice]]
| [[Rice (crafted pan)|Rice]]
| 3
| -10
| 720
| -
| 78
| 48
| Base.RicePan
|-
| [[File:CopperPot_Pasta.png|32x32px|link=Rice (crafted pan)|Rice]]
| [[Rice (crafted pan)|Rice]]
| 3
| -10
| 720
| -
| 78
| 48
| Base.RicePanCopper
|-
| [[File:PotFull.png|32x32px|link=Rice (crafted pot)|Rice]]
| [[Rice (crafted pot)|Rice]]
| 3
| -10
| 720
| -
| 78
| 48
| Base.RicePot
|-
| <span class="cycle-img">[[File:Pot_Forged_Rice.png|32x32px|link=Rice (crafted pot)|Rice]][[File:Pot_Forged_RiceRotten.png|32x32px|link=Rice (crafted pot)|Rice]]</span>
| [[Rice (crafted pot)|Rice]]
| 3
| -10
| 720
| -
| 78
| 48
| Base.RicePotForged
|-
| [[File:RicePaper.png|32x32px|link=Rice Paper|Rice Paper]]
| [[Rice Paper]]
| 0.1
| -4
| 10
| -
| -
| -
| Base.RicePaper
|-
| [[File:RiceVinegar.png|32x32px|link=Rice Vinegar|Rice Vinegar]]
| [[Rice Vinegar]]
| 0.2
| -20
| 20
| -
| -
| -
| Base.RiceVinegar
|-
| [[File:RoastingpanFull.png|32x32px|link=Roasted Vegetables|Roast]]
| [[Roasted Vegetables|Roast]]
| 1.3
| -10
| 180
| 36
| 6
| 2.5
| Base.PanFriedVegetables2
|-
| [[File:RockCandy.png|32x32px|link=Rock Candy|Rock Candy]]
| [[Rock Candy]]
| 0.1
| -5
| 40
| 60
| -
| -
| Base.RockCandy
|-
| <span class="cycle-img">[[File:Smallanimalmeat.png|32x32px|link=Rodent Meat|Rodent Meat]][[File:SmallanimalmeatRotten.png|32x32px|link=Rodent Meat|Rodent Meat]][[File:SmallanimalmeatCooked.png|32x32px|link=Rodent Meat|Rodent Meat]][[File:SmallanimalmeatOverdone.png|32x32px|link=Rodent Meat|Rodent Meat]]</span>
| [[Rodent Meat]]
| 0.3
| -15
| 201
| 5
| 45
| 7.25
| Base.Smallanimalmeat
|-
| [[File:Rosehips.png|32x32px|link=Rose Hips|Rose Hips]]
| [[Rose Hips]]
| 0.1
| -6
| 81
| 19
| 2
| -
| Base.Rosehips
|-
| [[File:Petals_Rose.png|32x32px|link=Rose Petals (Dried)|Rose Petals (Dried)]]
| [[Rose Petals (Dried)]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.RosePetalsDried
|-
| [[File:HerbRosemary.png|32x32px|link=Rosemary|Rosemary]]
| [[Rosemary]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.Rosemary
|-
| [[File:Seasoning_Rosemary.png|32x32px|link=Rosemary (Dried)|Rosemary (Dried)]]
| [[Rosemary (Dried)]]
| 0.2
| -20
| 0.4
| -
| -
| -
| Base.Seasoning_Rosemary
|-
| [[File:DriedHerbs_generic.png|32x32px|link=Rosemary (Dried)|Rosemary (Dried)]]
| [[Rosemary (Dried)]]
| 0.1
| -5
| 0.1
| -
| -
| -
| Base.RosemaryDried
|-
| [[File:Bouquet_Rose.png|32x32px|link=Roses|Roses]]
| [[Roses]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.Roses
|-
| [[File:Chocolate_RoysPBPucks.png|32x32px|link=Roy's Peanut Butter Pucks|Roy's Peanut Butter Pucks]]
| [[Roy's Peanut Butter Pucks]]
| 0.2
| -20
| 230
| 26
| 5
| 13
| Base.Chocolate_RoysPBPucks
|-
| [[File:HerbSage.png|32x32px|link=Sage|Sage]]
| [[Sage]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.Sage
|-
| [[File:Seasoning_Sage.png|32x32px|link=Sage (Dried)|Sage (Dried)]]
| [[Sage (Dried)]]
| 0.2
| -20
| 0.4
| -
| -
| -
| Base.Seasoning_Sage
|-
| [[File:DriedHerbs_generic.png|32x32px|link=Sage (Dried)|Sage (Dried)]]
| [[Sage (Dried)]]
| 0.1
| -5
| 0.1
| -
| -
| -
| Base.SageDried
|-
| [[File:FruitSalad.png|32x32px|link=Fruit Salad|Salad]]
| [[Fruit Salad|Salad]]
| 0.7
| -60
| 97
| 25
| 1.4
| 0.5
| Base.FruitSalad
|-
| [[File:Salami.png|32x32px|link=Salami|Salami]]
| [[Salami]]
| 0.1
| -20
| 330
| 2
| 22
| 26
| Base.Salami
|-
| [[File:SalamiSlices.png|32x32px|link=Salami Slices|Salami Slices]]
| [[Salami Slices]]
| 0.02
| -4
| 66
| 0.4
| 4.4
| 5.2
| Base.SalamiSlice
|-
| <span class="cycle-img">[[File:Salmon.png|32x32px|link=Salmon|Salmon]][[File:SalmonRotten.png|32x32px|link=Salmon|Salmon]][[File:SalmonCooked.png|32x32px|link=Salmon|Salmon]][[File:SalmonOverdone.png|32x32px|link=Salmon|Salmon]]</span>
| [[Salmon]]
| 0.3
| -30
| 270
| -
| 34.28
| 10.55
| Base.Salmon
|-
| [[File:Dip_Salsa.png|32x32px|link=Salsa|Salsa]]
| [[Salsa]]
| 0.2
| -16
| 140
| 28
| -
| -
| Base.Dip_Salsa
|-
| [[File:BaguetteSandwich.png|32x32px|link=Sandwich (baguette)|Sandwich]]
| [[Sandwich (baguette)|Sandwich]]
| 0.2
| -10
| 360
| 42
| 5.8
| 8.5
| Base.BaguetteSandwich
|-
| [[File:Sandwich.png|32x32px|link=Sandwich (bread)|Sandwich]]
| [[Sandwich (bread)|Sandwich]]
| 0.2
| -10
| 360
| 42
| 5.8
| 8.5
| Base.Sandwich
|-
| [[File:SaucepanFilled.png|32x32px|link=Pasta (crafted pan)|Saucepan with Pasta]]
| [[Pasta (crafted pan)|Saucepan with Pasta]]
| 3
| -10
| 560
| 109.3
| 18.66
| 2.66
| Base.WaterSaucepanPasta
|-
| [[File:SaucepanFilled.png|32x32px|link=Rice (crafted pan)|Saucepan with Rice]]
| [[Rice (crafted pan)|Saucepan with Rice]]
| 3
| -10
| 480
| 108
| 12
| -
| Base.WaterSaucepanRice
|-
| [[File:Fish_Sauger.png|32x32px|link=Sauger|Sauger]]
| [[Sauger]]
| 0.4
| -15
| 159
| 1
| 35
| 1
| Base.Sauger
|-
| <span class="cycle-img">[[File:Sausage.png|32x32px|link=Sausage|Sausage]][[File:SausageCooked.png|32x32px|link=Sausage|Sausage]][[File:SausageBurnt.png|32x32px|link=Sausage|Sausage]]</span>
| [[Sausage]]
| 0.1
| -20
| 180
| -
| 15.62
| 4.35
| Base.Sausage
|-
| [[File:CookieBox.png|32x32px|link=Scout Cookies|Scout Cookies]]
| [[Scout Cookies]]
| 0.2
| -20
| 1200
| 290
| 26
| 13
| Base.ScoutCookies
|-
| [[File:Seaweed.png|32x32px|link=Seaweed|Seaweed]]
| [[Seaweed]]
| 0.2
| -3
| 3
| -
| -
| -
| Base.Seaweed
|-
| [[File:Flax_Paste.png|32x32px|link=Seed Paste|Seed Paste]]
| [[Seed Paste]]
| 0.2
| -30
| 2120
| -
| -
| 130
| Base.SeedPaste
|-
| [[File:BagelSesame.png|32x32px|link=Sesame Bagel|Sesame Bagel]]
| [[Sesame Bagel]]
| 0.1
| -10
| 177
| 33
| 5.9
| 2.22
| Base.BagelSesame
|-
| [[File:SesameOil.png|32x32px|link=Sesame Oil|Sesame Oil]]
| [[Sesame Oil]]
| 0.2
| -10
| 120
| -
| -
| 14
| Base.SesameOil
|-
| [[File:CookiesShortbread.png|32x32px|link=Shortbread Cookie|Shortbread Cookie]]
| [[Shortbread Cookie]]
| 0.1
| -5
| 120
| 22
| 2
| 8
| Base.CookiesShortbread
|-
| <span class="cycle-img">[[File:Shrimp.png|32x32px|link=Shrimp|Shrimp]][[File:ShrimpRotten.png|32x32px|link=Shrimp|Shrimp]][[File:ShrimpCooked.png|32x32px|link=Shrimp|Shrimp]][[File:ShrimpBurnt.png|32x32px|link=Shrimp|Shrimp]]</span>
| [[Shrimp]]
| 0.1
| -10
| 80
| -
| 10
| 7
| Base.Shrimp
|-
| [[File:ShrimpDumpling.png|32x32px|link=Shrimp Dumpling|Shrimp Dumpling]]
| [[Shrimp Dumpling]]
| 0.1
| -15
| 120
| 5
| 15
| 7
| Base.ShrimpDumpling
|-
| [[File:MouseSkinned.png|32x32px|link=Skinned Mouse (Dead)|Skinned Mouse (Dead)]]
| [[Skinned Mouse (Dead)]]
| 0.05
| -10
| 220
| 0.7
| 9.5
| 3.15
| Base.DeadMouseSkinned
|-
| [[File:MouseSkinned.png|32x32px|link=Skinned Mouse Pups (Dead)|Skinned Mouse Pups (Dead)]]
| [[Skinned Mouse Pups (Dead)]]
| 0.03
| -5
| 110
| 0.35
| 4.2
| 1.58
| Base.DeadMousePupsSkinned
|-
| [[File:RatSkinned.png|32x32px|link=Skinned Rat (Dead)|Skinned Rat (Dead)]]
| [[Skinned Rat (Dead)]]
| 0.2
| -22
| 324
| -
| 40
| 16
| Base.DeadRatSkinned
|-
| [[File:RatSkinned.png|32x32px|link=Skinned Rat Baby (Dead)|Skinned Rat Baby (Dead)]]
| [[Skinned Rat Baby (Dead)]]
| 0.12
| -12
| 174.6
| -
| 21.6
| 8.6
| Base.DeadRatBabySkinned
|-
| [[File:Slug1.png|32x32px|link=Slug|Slug]]
| [[Slug]]
| 0.1
| -1
| 90
| 2.11
| 17.41
| 1.9
| Base.Slug
|-
| [[File:Slug2.png|32x32px|link=Slug|Slug]]
| [[Slug]]
| 0.1
| -1
| 90
| 2.11
| 17.41
| 1.9
| Base.Slug2
|-
| <span class="cycle-img">[[File:Smallbirdmeat.png|32x32px|link=Small Bird Meat|Small Bird Meat]][[File:SmallbirdmeatRotten.png|32x32px|link=Small Bird Meat|Small Bird Meat]][[File:SmallbirdmeatCooked.png|32x32px|link=Small Bird Meat|Small Bird Meat]][[File:SmallbirdmeatOverdone.png|32x32px|link=Small Bird Meat|Small Bird Meat]]</span>
| [[Small Bird Meat]]
| 0.3
| -15
| 261
| 5
| 90
| 8.25
| Base.Smallbirdmeat
|-
| [[File:Fish_BassSmallmouth.png|32x32px|link=Smallmouth Bass|Smallmouth Bass]]
| [[Smallmouth Bass]]
| 0.4
| -15
| 159
| 1
| 35
| 1
| Base.SmallmouthBass
|-
| [[File:Chocolate_Smirkers.png|32x32px|link=Smirkers Bar|Smirkers Bar]]
| [[Smirkers Bar]]
| 0.2
| -20
| 280
| 35
| 4
| 14
| Base.Chocolate_Smirkers
|-
| [[File:Smore.png|32x32px|link=Smore|Smore]]
| [[Smore]]
| 0.1
| -10
| 200
| 33
| 3
| 10
| Base.Smore
|-
| [[File:Snail.png|32x32px|link=Snail|Snail]]
| [[Snail]]
| 0.1
| -1
| 90
| 2.11
| 17.41
| 1.9
| Base.Snail
|-
| [[File:Chocolate_SnikSnak.png|32x32px|link=SnikSnak Bar|SnikSnak Bar]]
| [[SnikSnak Bar]]
| 0.2
| -20
| 230
| 29
| 3
| 12
| Base.Chocolate_SnikSnak
|-
| [[File:Snackcake_SnoSpheres.png|32x32px|link=Sno Globes|Sno Globes]]
| [[Sno Globes]]
| 0.2
| -10
| 200
| 30
| 1.8
| 8
| Base.SnoGlobes
|-
| [[File:SourCream.png|32x32px|link=Sour Cream|Sour Cream]]
| [[Sour Cream]]
| 0.2
| -16
| 420
| 370
| 2
| 14
| Base.SourCream
|-
| [[File:Soysauce.png|32x32px|link=Soy Sauce|Soy Sauce]]
| [[Soy Sauce]]
| 0.2
| -10
| 20
| -
| -
| -
| Base.Soysauce
|-
| <span class="cycle-img">[[File:Soybeans.png|32x32px|link=Soybeans|Soybeans]][[File:SoybeansRotten.png|32x32px|link=Soybeans|Soybeans]]</span>
| [[Soybeans]]
| 0.1
| -5
| 25
| 10.45
| 3.95
| 0.45
| Base.Soybeans
|-
| [[File:DriedSoyBeans.png|32x32px|link=Soybeans (Dried)|Soybeans (Dried)]]
| [[Soybeans (Dried)]]
| 0.02
| -1
| 5
| 2
| 0.8
| 0.1
| Base.SoybeansSeed
|-
| <span class="cycle-img">[[File:Spinach.png|32x32px|link=Spinach|Spinach]][[File:SpinachRotten.png|32x32px|link=Spinach|Spinach]]</span>
| [[Spinach]]
| 0.1
| -5
| 24
| 3
| 4
| -
| Base.Spinach
|-
| [[File:DriedSplitPeas.png|32x32px|link=Split Peas (Dried)|Split Peas (Dried)]]
| [[Split Peas (Dried)]]
| 2
| -60
| 2217
| 544
| 221
| -
| Base.DriedSplitPeas
|-
| [[File:Fish_BassSpotted.png|32x32px|link=Spotted Bass|Spotted Bass]]
| [[Spotted Bass]]
| 0.4
| -15
| 159
| 1
| 35
| 1
| Base.SpottedBass
|-
| [[File:Springroll.png|32x32px|link=Spring Roll|Spring Roll]]
| [[Spring Roll]]
| 0.1
| -20
| 180
| 22
| 9
| 17
| Base.Springroll
|-
| <span class="cycle-img">[[File:Squash.png|32x32px|link=Squash|Squash]][[File:SquashRotten.png|32x32px|link=Squash|Squash]]</span>
| [[Squash]]
| 0.5
| -20
| 202
| 10.22
| 17.26
| 10.3
| Base.Squash
|-
| [[File:Squid.png|32x32px|link=Squid|Squid]]
| [[Squid]]
| 0.2
| -30
| 205
| 1
| 32.52
| 13
| Base.Squid
|-
| [[File:SquidCalimari.png|32x32px|link=Squid Calamari|Squid Calamari]]
| [[Squid Calamari]]
| 0.1
| -10
| 105
| 3
| 18
| -
| Base.SquidCalamari
|-
| <span class="cycle-img">[[File:Steak.png|32x32px|link=Steak|Steak]][[File:SteakRotten.png|32x32px|link=Steak|Steak]][[File:SteakCooked.png|32x32px|link=Steak|Steak]][[File:SteakOverdone.png|32x32px|link=Steak|Steak]]</span>
| [[Steak]]
| 0.3
| -40
| 220
| -
| 31.62
| 9.35
| Base.Steak
|-
| <span class="cycle-img">[[File:FryingPan_Forged_Stirfry.png|32x32px|link=Stir Fry (pan)|Stir Fry]][[File:FryingPan_Forged_StirfryRotten.png|32x32px|link=Stir Fry (pan)|Stir Fry]][[File:FryingPan_Forged_StirfryBurnt.png|32x32px|link=Stir Fry (pan)|Stir Fry]]</span>
| [[Stir Fry (pan)|Stir Fry]]
| 1
| -10
| 516
| 36
| 4.8
| 41.5
| Base.PanFriedVegetablesForged
|-
| [[File:PanFull.png|32x32px|link=Stir Fry (griddle)|Stir Fry]]
| [[Stir Fry (griddle)|Stir Fry]]
| 1.5
| -10
| 190
| 25
| 11
| 2
| Base.GriddlePanFriedVegetables
|-
| [[File:PanFull.png|32x32px|link=Stir Fry (pan)|Stir Fry]]
| [[Stir Fry (pan)|Stir Fry]]
| 1.5
| -10
| 516
| 36
| 4.8
| 41.5
| Base.PanFriedVegetables
|-
| <span class="cycle-img">[[File:BerryStraw.png|32x32px|link=Strawberries|Strawberries]][[File:BerryStrawRotten.png|32x32px|link=Strawberries|Strawberries]]</span>
| [[Strawberries]]
| 0.1
| -5
| 4
| 0.92
| 0.08
| 0.04
| Base.Strewberrie
|-
| [[File:CakeStrawberryShortcake.png|32x32px|link=Strawberry Cake Slice|Strawberry Cake Slice]]
| [[Strawberry Cake Slice]]
| 0.2
| -8
| 75
| 4
| 10
| 12
| Base.CakeStrawberryShortcake
|-
| [[File:Fish_BassStriped.png|32x32px|link=Striped Bass|Striped Bass]]
| [[Striped Bass]]
| 0.4
| -15
| 159
| 1
| 35
| 1
| Base.StripedBass
|-
| <span class="cycle-img">[[File:SugarBeets.png|32x32px|link=Sugar Beet|Sugar Beet]][[File:SugarBeetsRotten.png|32x32px|link=Sugar Beet|Sugar Beet]]</span>
| [[Sugar Beet]]
| 0.2
| -9
| 24
| 3
| 4
| -
| Base.SugarBeet
|-
| [[File:CookiesSugar.png|32x32px|link=Sugar Cookie|Sugar Cookie]]
| [[Sugar Cookie]]
| 0.1
| -5
| 120
| 22
| 2
| 8
| Base.CookiesSugar
|-
| [[File:SugarCubes.png|32x32px|link=Sugar Cubes|Sugar Cubes]]
| [[Sugar Cubes]]
| 0.02
| -4
| 44
| 12
| -
| -
| Base.SugarCubes
|-
| [[File:SugarPacket.png|32x32px|link=Sugar Packet|Sugar Packet]]
| [[Sugar Packet]]
| 0.005
| -1
| 11
| 3
| -
| -
| Base.SugarPacket
|-
| [[File:SunflowerSeeds.png|32x32px|link=Sunflower Seeds|Sunflower Seeds]]
| [[Sunflower Seeds]]
| 0.1
| -5
| 355
| -
| -
| 22.5
| Base.SunflowerSeeds
|-
| <span class="cycle-img">[[File:SweetPotato.png|32x32px|link=Sweet Potato|Sweet Potato]][[File:SweetPotatoRotten.png|32x32px|link=Sweet Potato|Sweet Potato]]</span>
| [[Sweet Potato]]
| 0.2
| -18
| 70
| 14.52
| 2.88
| 0.15
| Base.SweetPotato
|-
| <span class="cycle-img">[[File:TVDinner.png|32x32px|link=TV Dinner|TV Dinner]][[File:TVDinnerRotten.png|32x32px|link=TV Dinner|TV Dinner]][[File:TVDinnerCooked.png|32x32px|link=TV Dinner|TV Dinner]][[File:TVDinnerBurnt.png|32x32px|link=TV Dinner|TV Dinner]]</span>
| [[TV Dinner]]
| 0.4
| -23
| 670
| 81
| 30
| 25
| Base.TVDinner
|-
| [[File:Taco.png|32x32px|link=Taco|Taco]]
| [[Taco]]
| 0.3
| -25
| 400
| 80
| 32
| 28
| Base.Taco
|-
| [[File:Taco.png|32x32px|link=Taco|Taco]]
| [[Taco]]
| 0.1
| -5
| 55
| 8.4
| 0.8
| 3
| Base.TacoRecipe
|-
| [[File:TacoShell.png|32x32px|link=Taco Shell|Taco Shell]]
| [[Taco Shell]]
| 0.1
| -5
| 55
| 8.4
| 0.8
| 3
| Base.TacoShell
|-
| [[File:frog_tadpole.png|32x32px|link=Tadpole|Tadpole]]
| [[Tadpole]]
| 0.1
| -1
| 90
| 2.11
| 17.41
| 1.9
| Base.Tadpole
|-
| [[File:TatoDots.png|32x32px|link=Tato Dots|Tato Dots]]
| [[Tato Dots]]
| 0.2
| -10
| 203
| 35.97
| 3.35
| 5.19
| Base.TatoDots
|-
| [[File:Insect_Termite.png|32x32px|link=Termites|Termites]]
| [[Termites]]
| 0.01
| -1
| 2.5
| -
| 0.5
| 0.5
| Base.Termites
|-
| [[File:Thistle.png|32x32px|link=Thistles|Thistles]]
| [[Thistles]]
| 0.1
| -4
| 45
| 18
| 3
| -
| Base.Thistle
|-
| [[File:HerbThyme.png|32x32px|link=Thyme|Thyme]]
| [[Thyme]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.Thyme
|-
| [[File:Seasoning_Thyme.png|32x32px|link=Thyme (Dried)|Thyme (Dried)]]
| [[Thyme (Dried)]]
| 0.2
| -20
| 0.4
| -
| -
| -
| Base.Seasoning_Thyme
|-
| [[File:DriedHerbs_generic.png|32x32px|link=Thyme (Dried)|Thyme (Dried)]]
| [[Thyme (Dried)]]
| 0.1
| -5
| 0.1
| -
| -
| -
| Base.ThymeDried
|-
| [[File:Caviar.png|32x32px|link=Tin of Caviar|Tin of Caviar]]
| [[Tin of Caviar]]
| 0.2
| -10
| 150
| -
| 14
| 11
| Base.Caviar
|-
| [[File:Toast.png|32x32px|link=Toast|Toast]]
| [[Toast]]
| 0.1
| -8
| 177
| 33
| 5.9
| 2.22
| Base.Toast
|-
| <span class="cycle-img">[[File:Tofu.png|32x32px|link=Tofu|Tofu]][[File:TofuRotten.png|32x32px|link=Tofu|Tofu]]</span>
| [[Tofu]]
| 0.3
| -10
| 30
| 1
| 5
| 1
| Base.Tofu
|-
| [[File:TofuFried.png|32x32px|link=Tofu (Fried)|Tofu (Fried)]]
| [[Tofu (Fried)]]
| 0.3
| -15
| 35
| 3
| 5
| 1
| Base.TofuFried
|-
| <span class="cycle-img">[[File:Tomato.png|32x32px|link=Tomato|Tomato]][[File:TomatoRotten.png|32x32px|link=Tomato|Tomato]]</span>
| [[Tomato]]
| 0.2
| -12
| 14
| 3.5
| 1.3
| 0.2
| Base.Tomato
|-
| [[File:TomatoPaste.png|32x32px|link=Tomato Paste|Tomato Paste]]
| [[Tomato Paste]]
| 0.2
| -15
| 120
| 32
| -
| 8
| Base.TomatoPaste
|-
| [[File:Tortilla.png|32x32px|link=Tortilla|Tortilla]]
| [[Tortilla]]
| 0.1
| -5
| 40
| -
| 2
| 2
| Base.Tortilla
|-
| [[File:CornChips.png|32x32px|link=Tortilla Chips|Tortilla Chips]]
| [[Tortilla Chips]]
| 0.2
| -15
| 420
| 42
| 2.5
| 40
| Base.TortillaChips
|-
| [[File:TortillaChips.png|32x32px|link=Tortilla Chips|Tortilla Chips]]
| [[Tortilla Chips]]
| 0.2
| -15
| 120
| -
| 6
| 6
| Base.TortillaChipsBaked
|-
| <span class="cycle-img">[[File:TurkeyWhole.png|32x32px|link=Turkey (Whole)|Turkey (Whole)]][[File:TurkeyWholeRotten.png|32x32px|link=Turkey (Whole)|Turkey (Whole)]][[File:TurkeyWholeCooked.png|32x32px|link=Turkey (Whole)|Turkey (Whole)]][[File:TurkeyWholeOverdone.png|32x32px|link=Turkey (Whole)|Turkey (Whole)]]</span>
| [[Turkey (Whole)]]
| 1.3
| -224
| 1821
| -
| 104.2
| 53.3
| Base.TurkeyWhole
|-
| [[File:Egg_Turkey.png|32x32px|link=Turkey Egg|Turkey Egg]]
| [[Turkey Egg]]
| 0.1
| -10
| 71
| 0.37
| 5.78
| 4.54
| Base.TurkeyEgg
|-
| <span class="cycle-img">[[File:TurkeyFilet.png|32x32px|link=Turkey Fillet|Turkey Fillet]][[File:TurkeyFiletRotten.png|32x32px|link=Turkey Fillet|Turkey Fillet]][[File:TurkeyFiletCooked.png|32x32px|link=Turkey Fillet|Turkey Fillet]][[File:TurkeyFiletOverdone.png|32x32px|link=Turkey Fillet|Turkey Fillet]]</span>
| [[Turkey Fillet]]
| 0.3
| -50
| 230
| -
| 32
| 10
| Base.TurkeyFillet
|-
| <span class="cycle-img">[[File:TurkeyLeg.png|32x32px|link=Turkey Leg|Turkey Leg]][[File:TurkeyLegRotten.png|32x32px|link=Turkey Leg|Turkey Leg]][[File:TurkeyLegCooked.png|32x32px|link=Turkey Leg|Turkey Leg]][[File:TurkeyLegOverdone.png|32x32px|link=Turkey Leg|Turkey Leg]]</span>
| [[Turkey Leg]]
| 0.3
| -42
| 230
| -
| 38
| 9
| Base.TurkeyLegs
|-
| <span class="cycle-img">[[File:TurkeyWing.png|32x32px|link=Turkey Wing|Turkey Wing]][[File:TurkeyWingRotten.png|32x32px|link=Turkey Wing|Turkey Wing]][[File:TurkeyWingCooked.png|32x32px|link=Turkey Wing|Turkey Wing]][[File:TurkeyWingOverdone.png|32x32px|link=Turkey Wing|Turkey Wing]]</span>
| [[Turkey Wing]]
| 0.3
| -30
| 200
| -
| 32
| 10
| Base.TurkeyWings
|-
| <span class="cycle-img">[[File:Turnip.png|32x32px|link=Turnip|Turnip]][[File:TurnipRotten.png|32x32px|link=Turnip|Turnip]]</span>
| [[Turnip]]
| 0.2
| -18
| 70
| 14.52
| 2.88
| 0.15
| Base.Turnip
|-
| [[File:OilVegetable.png|32x32px|link=Vegetable Oil|Vegetable Oil]]
| [[Vegetable Oil]]
| 0.2
| -30
| 2120
| -
| -
| 130
| Base.OilVegetable
|-
| <span class="cycle-img">[[File:Venison.png|32x32px|link=Venison|Venison]][[File:VenisonRotten.png|32x32px|link=Venison|Venison]][[File:VenisonCooked.png|32x32px|link=Venison|Venison]][[File:VenisonOverdone.png|32x32px|link=Venison|Venison]]</span>
| [[Venison]]
| 0.5
| -80
| 440
| -
| 62.62
| 18.7
| Base.Venison
|-
| [[File:Violets.png|32x32px|link=Violets|Violets]]
| [[Violets]]
| 0.1
| -2
| 27
| 7
| 1
| -
| Base.Violets
|-
| [[File:SafflesFruit.png|32x32px|link=Waffles|Waffles]]
| [[Waffles]]
| 0.3
| -15
| 80
| 13
| 3
| 4
| Base.WafflesRecipe
|-
| [[File:Waffles.png|32x32px|link=Waffles|Waffles]]
| [[Waffles]]
| 0.3
| -15
| 80
| 13
| 3
| 4
| Base.Waffles
|-
| [[File:Fish_Walleye.png|32x32px|link=Walleye|Walleye]]
| [[Walleye]]
| 0.4
| -15
| 159
| 1
| 35
| 1
| Base.Walleye
|-
| <span class="cycle-img">[[File:Watermelon.png|32x32px|link=Watermelon|Watermelon]][[File:WatermelonRotten.png|32x32px|link=Watermelon|Watermelon]]</span>
| [[Watermelon]]
| 3
| -60
| 1355
| 341.11
| 27.56
| 6.78
| Base.Watermelon
|-
| [[File:WatermelonSmashed.png|32x32px|link=Watermelon Chunks|Watermelon Chunks]]
| [[Watermelon Chunks]]
| 0.6
| -12
| 271
| 68.2
| 5.51
| 1.35
| Base.WatermelonSmashed
|-
| [[File:WatermelonSliced.png|32x32px|link=Watermelon Slice|Watermelon Slice]]
| [[Watermelon Slice]]
| 0.3
| -6
| 135.5
| 34.11
| 2.75
| 0.67
| Base.WatermelonSliced
|-
| [[File:Fish_BassWhite.png|32x32px|link=White Bass|White Bass]]
| [[White Bass]]
| 0.4
| -15
| 159
| 1
| 35
| 1
| Base.WhiteBass
|-
| [[File:DriedWhiteBeans.png|32x32px|link=White Beans (Dried)|White Beans (Dried)]]
| [[White Beans (Dried)]]
| 2
| -60
| 2823
| 527
| 188
| 10
| Base.DriedWhiteBeans
|-
| [[File:Fish_CrappieWhite.png|32x32px|link=White Crappie|White Crappie]]
| [[White Crappie]]
| 0.4
| -15
| 159
| 1
| 35
| 1
| Base.WhiteCrappie
|-
| [[File:Sugar.png|32x32px|link=White Sugar|White Sugar]]
| [[White Sugar]]
| 0.6
| -30
| 387
| 100
| -
| -
| Base.Sugar
|-
| <span class="cycle-img">[[File:WildEggs.png|32x32px|link=Wild Eggs|Wild Eggs]][[File:WildEggsCooked.png|32x32px|link=Wild Eggs|Wild Eggs]]</span>
| [[Wild Eggs]]
| 0.1
| -7
| 63
| 0.32
| 5.55
| 4.18
| Base.WildEggs
|-
| [[File:WildGarlic.png|32x32px|link=Wild Garlic|Wild Garlic]]
| [[Wild Garlic]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.WildGarlic2
|-
| [[File:WildGarlic.png|32x32px|link=Wild Garlic (Dried)|Wild Garlic (Dried)]]
| [[Wild Garlic (Dried)]]
| 0.1
| -1
| 0.1
| -
| -
| -
| Base.WildGarlicDried
|-
| [[File:Worm.png|32x32px|link=Worm|Worm]]
| [[Worm]]
| 0.01
| -1
| 3
| -
| 0.5
| 0.1
| Base.Worm
|-
| [[File:Fish_PerchYellow.png|32x32px|link=Yellow Perch|Yellow Perch]]
| [[Yellow Perch]]
| 0.4
| -15
| 159
| 1
| 35
| 1
| Base.YellowPerch
|-
| [[File:Yoghurt.png|32x32px|link=Yogurt|Yogurt]]
| [[Yogurt]]
| 0.3
| -10
| 30
| 1
| 5
| 1
| Base.Yoghurt
|-
| <span class="cycle-img">[[File:Zucchini.png|32x32px|link=Zucchini|Zucchini]][[File:ZucchiniRotten.png|32x32px|link=Zucchini|Zucchini]]</span>
| [[Zucchini]]
| 0.3
| -10
| 33
| 6.1
| 2.37
| 0.63
| Base.Zucchini
|}
</div><!-- Bot_flag_end|type=food_item_list|id=nutrition -->

== See also ==
* {{ll|Nutrition}}
{{ll|Category:Food}}
```
