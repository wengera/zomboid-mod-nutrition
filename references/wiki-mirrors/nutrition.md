# Wiki mirror — Nutrition

**Source:** https://pzwiki.net/wiki/Nutrition
**Fetched:** 2026-09-09
**Wiki page version:** 42.11.0
**License:** CC BY-NC-SA 3.0 — attribution: PZwiki contributors

## Digest

- Nutrition as a game mechanic: the four macros, the weight scale they drive, and the traits/occupations bolted to it. Stamped `{{Page version|42.11.0}}` — the oldest of these mirrors, and the only page that writes the weight math out.
- Weight bands: Very High >= 100, High 85-99.9, normal 75.1-84.9, Low 65.1-75, Very Low 50.1-65, Emaciated <= 50, plus damage ("degeneration") at 35; default start 80, and any band but normal caps fitness XP at level 6.
- Gain: calories must clear `base + (weight - 80) * 40`, base 1000 (700 with Slow Metabolism under 90, 1800 with Fast Metabolism over 70); then `dWeight = factor * min(1, calories/4000) * gameSeconds`, factor 1.3e-5, x2 above 400 and x3 above 700 carbs-or-fats.
- Loss: below `(weight - 70) * 30` (capped at 0), `dWeight = 8.5e-6 * min(1, calories/2500) * gameSeconds`. Store ceilings: calories 3700 / -2200; carbohydrates, proteins and fats 1000 / -500 each.
- `docs/superpowers/plans/01-notes.md` Q5 re-read `Nutrition.updateWeight()` off the 42.20.4 jar and found this gain/loss model unchanged, so the formulas are safe to cite even though the page stamp is nine minors stale.
- Claims proteins between 50 and 300 give a x1.5 Strength XP multiplier and below -300 a x0.7 penalty, self-dated "Build 34.5" — verify against `zombie.characters.BodyDamage.Nutrition` and the XP award path before repeating.
- Presents the weight sim as always-on and never mentions the sandbox `Nutrition` option, which 01-notes.md Q5 shows gates `Nutrition.update()` and nothing else: with it off, `Eat` still fills the stores while drain, calorie burn and weight all stop — verify against `SandboxOptions`/`Nutrition.update()`.

## Wikitext

```wikitext
{{LangSwitch}}
{{Navbar player}}
{{Page version|42.11.0}}
{{About|nutrition as a game mechanic|a list of item's nutritional values|Nutritional values}}
'''Nutrition''' is a game mechanic in [[Project Zomboid]] redesigned and implemented in [[Build 34]]. Each item of food has a quality known as [[#Nutritional value|''nutritional value'']] which is defined by four variables: [[#Carbohydrates|carbohydrates]], [[#Proteins|proteins]], [[#Fats|fats]], and [[#Calories|calories]]. Each of these variables currently only has an impact on the player's weight, which can affect fitness experience gain, endurance, speed, and fragility, while proteins give the “Protein Boost” for [[exercise]]. However, there were previous mentions that it would change the player in various other ways, such as [[strength]] and [[Unhappiness|mental state]], which are not currently implemented.<ref>[https://projectzomboid.com/blog/2016/01/co-op-n-carbs/ Co-op n' Carbs - Project Zomboid]</ref>

== Occupations & traits ==

=== Occupations ===
{| class="wikitable theme-red sortable" style="text-align: center;"
|-
! class="sortable" | Name
! class="sortable" | Starting points
! class="unsortable" | Major skills
! class="unsortable" | Description
|-
| [[File:profession_fitnessinstructor.png|link=|Fitness Instructor]] [[Fitness Instructor]]
| -6
| +2 [[Running]]<br>+3 [[Fitness]]
| Starts with the [[File:trait_nutritionist.png|link=Nutritionist]] [[Nutritionist (occupation trait)|Nutritionist]] trait
|}

=== Traits ===
{| class="wikitable theme-red sortable" style="text-align: center;"
|-
! class="sortable" | Name
! class="sortable" | Cost
! class="sortable" | Starting weight
! class="unsortable" | Description
|-
| [[File:trait_nutritionist.png|link=Nutritionist|left]] [[Nutritionist]]
| -2
| N/A
| Can see the nutritional values of any food
|-
| [[File:trait_weightgain.png|link=Slow Metabolism|left]] [[Slow Metabolism]]
| +2
| N/A
| Permanent tendency to gain weight. Starts with High Weight trait. 
|-
| [[File:trait_weightloss.png|link=Fast Metabolism|left]] [[Fast Metabolism]]
| +2
| N/A
| Permanent tendency to lose weight. Starts with Low Weight trait. 
|-
| [[File:trait_obese.png|link=Very High Weight|left]] [[Very High Weight]]
| +10
| 105
| Slower running speed. Tire from running more easily, -2 [[Fitness]]
|-
| [[File:trait_overweight.png|link=High Weight|left]] [[High Weight]]
| +6
| 95
| Slower running speed. Tire from running more easily, -1 [[Fitness]]
|-
| [[File:trait_underweight.png|link=Low Weight|left]] [[Low Weight]]
| +6
| 70
| Low strength, low endurance, and prone to injury
|-
| [[File:trait_very underweight.png|link=Very Low Weight|left]] [[Very Low Weight]]
| +10
| 60
| Very low strength, very low endurance, and prone to injury
|-
| [[File:trait_emaciated.png|link=Emaciated|left]] [[Emaciated]]
| N/A
| 50
| Low strength, low endurance, and prone to injury<br>''Not available during character creation''
|}

The [[File:trait_nutritionist.png|link=|Nutritionist: Can see the nutritional values of any food.]] nutritionist trait is only available during [[Player#Character creation|character creation]], costing 2 trait points, or can be picked up for free when choosing the fitness instructor [[occupation]]. The nutritionist trait allows the player to "see the nutritional values of any food", which can normally only be seen on food that is ''packaged''.


== Nutritional value ==
Nutritional value defines how ''healthy'' a particular food is and the effects they'll have on the player's weight. By consuming just one type of food, the player may find themselves suffering from weight loss or weight gain, therefore altering their effectiveness to perform certain actions.
{{See|Nutritional values}}

=== Weight ===
Weight is a player statistic presented on the ''Info'' panel, which can be toggled with the {{Key|J}} key by default. During character creation, the player can choose between one of four traits, which will determine their starting weight; if none are chosen, they will begin with the default weight of 80. Over time the player's weight may begin to vary from its starting value, which depends on the nutritional value of the food they have been consuming and the level of exercise they've been doing. As the player's weight fluctuates, their traits will also change depending on their current weight. The game recognizes that there are actually five different traits relating to weight, rather than just the four that can be picked up during character creation, whereas the default/normal weight is considered the ''absence of a trait''.

The different effects caused on the player, along with their weight ranges, can be seen in the table below.

{| class="wikitable theme-red" style="text-align: center;"
!Name
!Weight range
|-
|[[File:trait_obese.png|link=Very High Weight|left|Very High Weight]] Very High Weight || 100 or more
|-
|[[File:trait_overweight.png|link=High Weight|left|High Weight]] High Weight || 85 - 99.9
|-
|Normal || 75.1 - 84.9
|-
|[[File:trait_underweight.png|link=Low Weight|left|Low Weight]] Low Weight || 65.1 - 75
|-
|[[File:trait_very underweight.png|link=Very Low Weight|left|Very Low Weight]] Very Low Weight || 50.1 - 65
|-
|[[File:trait_emaciated.png|link=Emaciated|left|Emaciated]] Emaciated || 50 or less
|-
|[[File:Moodle_Icon_Injured.png|link=|left|26px|Degeneration]] Degeneration<br>(Damage) || 35
|}
''Note that the emaciated trait and degeneration currently only exist in the game mechanics and therefore have no visual representation in-game.''<br>
''Also note that the game rounds values ​​to whole numbers, e.g., 99.7 will be displayed as 100.''

Having any of the five traits listed above (excluding ''normal'') gives the player an attribute recognized as “has weight trouble.” A player with this attribute will not gain any [[fitness]] experience beyond level 6, whereas having the emaciated, very high weight, or very low weight trait, they will lose the ability to gain fitness experience altogether, regardless of the current level. Experience will return to normal upon losing/gaining some weight, i.e., removing the trait.

''The game files (<code>Nutrition.class</code>) contain a base weight of 60 for females, with varying values for gaining and losing weight; however, this has not been implemented.''

==== Gaining weight ====
Gaining weight is usually undesirable, as it grants the player slower movement speed and loss of fitness. However, weight gain may be needed if the player is already underweight, which has its set of negative effects. While exercise doesn't directly affect weight gain, it does contribute to burning calories and thus reducing weight. Therefore, gaining weight can be assisted by walking instead of running or sprinting, not climbing (either over fences or through windows), and sleeping often. Sleeping will expend the least amount of calories compared to any other activity. For this reason, taking the [[Restless Sleeper|restless sleeper]] or [[sleepyhead]] [[traits]] is recommended for players that often have trouble with losing too much weight.

===== Food consumption for weight gain =====
The foods consumed by the player are the main contributor to weight gain. Calories must be above the <code>minimumThreshold</code>, which will scale with the player's current weight, thus making it more difficult to gain weight the higher their weight is. The <code>minimumThreshold</code> can be calculated with the following equation.

<code class="equation">baseCalorieThreshold + ((currentWeight − 80) × 40)</code>

;<code>baseCalorieThreshold</code>
:700 with [[Slow Metabolism|slow metabolism]] and if weight &lt; 90.
:1800 with [[Fast Metabolism|fast metabolism]] and if weight &gt; 70.
:1000 otherwise.

The amount of weight gained is affected by the amount of calories, carbohydrates, and fats consumed along with the time that has passed. This can be presented as the following equation.

<code class="equation">△Weight = weightGainFactor × calorieProportion × timeElapsed</code>

;<code>weightGainFactor</code>
:The carbohydrates and fats that the player consumes will accumulate and decrease slowly over time. If the player's consumed carbohydrates or fats are 400 or less, <code>weightGainFactor</code> will be 0.000013, but between 400 and 700, it'll become 0.000026, and above 700, will be 0.000039.

;<code>calorieProportion</code>
:Like carbohydrates and fats, calories will accumulate and decrease slowly over time, which is directly affected by the amount of exercise and type of exercise performed. <code>calorieProportion</code> is calculated by dividing the <code>currentCalories</code> by 4000. 4000 is the maximum number of calories. Therefore, if the <code>currentCalories</code> is above 4000, the <code>calorieProportion</code> will be 1.

;<code>timeElapsed</code>
:This value is the amount of in-game seconds that have passed. Therefore, 1 hour would be 3600.

;Example
:A player with a weight of 85 maintains 3000 calories, 500 carbohydrates and 200 fats over 1 day.
:<code class="equation">minimumThreshold = 1000 + ((85 − 80) × 40) = 1200</code>
:Calories (3000) exceed the <code>minimumThreshold</code> (1200), so weight gain occurs.
:The amount of weight gained is calculated:
:<code class="equation">△Weight = 0.000026 × (3000/4000) × 86400 = 1.6848</code>
:Therefore, they will gain 1.68 weight if these values can be maintained (the <code>weightGainFactor</code> is 0.000026 due to carbohydrates >400).
''It should be noted that these values are after calculating for calories burned from exercise, and are not taken directly from the foods consumed, nor is it realistic that these values will remain static over a day. These values are constantly changing, and thus the weight gained is also updating constantly.''

==== Losing weight ====
Too much weight loss can lead to reduced strength and endurance, and the player can become more prone to injury. Losing weight is desirable if the player happens to be of high weight. Weight can be lowered by climbing over fences and through windows, chopping trees, sprinting instead of walking, and avoiding sleep, which can be helped with the [[wakeful]] trait. The biggest factor in losing weight is the type of food eaten; avoiding food would lead to death. The best foods to eat are those low in calories and high in hunger, such as the following fruits and vegetables: [[radish]]es, [[tomato]]es, [[broccoli]], [[carrot]]s, [[onion]]s, [[Strawberry|strawberries]], [[berries]], and [[Cherry|cherries]]. It will often take the player a while before they begin to lose weight after dieting. This is due to any excess calories that were consumed previously being used first. In addition to gaining underweight traits from losing too much weight, if the player reaches a weight of 35, they will begin taking damage until some weight is gained. This is usually very rare. However, it can be caused by eating only fruits/vegetables for long periods of time.

The weight loss occurs if <code>currentCalories</code> are less than <code>calorieDeficitThreshold</code>.

;<code>calorieDeficitThreshold</code>
:This is calculated as <code>(currentWeight − 70) × 30</code>. This value is capped at 0.

<code class="equation">△Weight_Loss = 0.0000085 × calorieDeficitProportion × timeElapsed</code>

;<code>calorieDeficitProportion</code>
:This is calculated as <code>currentCalories</code> / 2500. This proportion is capped at 1.

=== Nutrients ===
;<span id="Carbohydrates">Carbohydrates</span>: Carbohydrates are used in determining potential weight gain. This value is ignored unless the player has consumed more than 400 or 700 carbohydrates, resulting in a multiplier of 2 or 3, respectively. ''If consumed carbohydrates <400, it still may be a multiplier of 2 or 3 based on fats.''
:Maximum: 1000
:Minimum: -500
;<span id="Proteins">Proteins</span>: Protein surplus or malus affects the amount of strength experience gained by various tasks such as exercise.
:Maximum: 1000
:Minimum: -500
(As of Build 34.5, Protein values between 50 and 300 provide a 1.5 multiplier to Str XP gain. Likewise, values below -300 apply a .7 gain penalty.)
;<span id="Fats">Fats</span>: Fats, previously called lipids, are used in determining potential weight gain. This value is ignored unless the player has consumed more than 400 or 700 fats, resulting in a multiplier of 2 or 3, respectively. ''If consumed fats &lt;400, it still may be a multiplier of 2 or 3 based on carbohydrates.''
:Maximum: 1000
:Minimum: -500
;<span id="Calories">Calories</span>: Calories are the main weight-determining nutrient. This value must be balanced with hunger consistently, or else obesity or starvation may sneak up on the player.
:Maximum: 3700
:Minimum: -2200

== See also ==
* {{ll|Agriculture}}
* {{ll|Cooking}}
* {{ll|Evolved recipes}}
* {{ll|Fishing}}
* {{ll|Food}}
* {{ll|Health}}
* {{ll|Trapping}}

== References ==
<references/>

{{ll|Category:Character}}
```
