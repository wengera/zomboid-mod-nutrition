# Wiki mirror — Hungry

**Source:** https://pzwiki.net/wiki/Hungry
**Fetched:** 2026-09-10
**Wiki page version:** 42.12.3
**License:** CC BY-NC-SA 3.0 — attribution: PZwiki contributors

## Digest

- The Hungry moodle page, stamped `{{Page version|42.12.3}}`: the four negative levels (Peckish -> Starving to Death), the four positive `FoodEaten` levels (Satiated -> Full to Bursting), and the base hunger rate with its two traits.
- Thresholds match the jar exactly: >15 / >25 / >45 / >70 % is `MoodleStat.<clinit>`'s `HUNGRY` row 0.15 / 0.25 / 0.45 / 0.70, evaluated with strict `>`. So do the carry-capacity penalties (level 2 -1, levels 3 and 4 -2, `BodyDamage.UpdateStrength`) and the trait factors (Light Eater x0.75, Hearty Appetite x1.5 in `getAppetiteMultiplier`).
- Its headline "nutrition and hunger are entirely separate mechanics ... burning or gaining calories has no effect on this moodle" is confirmed in both directions: `Nutrition.updateCalories` never touches `Stats`, and `updateStats_Awake` never reads `Nutrition` (`docs/superpowers/plans/03-notes.md` Q3).
- Claims a flat `4.32%` per in-game hour base rate. Coded rate is `HungerIncrease` 9.6e-6 /game-s x `StatsDecrease` x `(1 - hunger)` = 3.456 %/game-hour at H = 0 and falling as hunger rises — a first-order approach, not a linear fill; the page's `0.00032%` per tick is `defines.lua:14`'s literal `0.0000032` *before* its `* 3`. Verify against `defines.lua:14` and `IsoGameCharacter.getAppetiteMultiplier @0-@50`.
- Claims health regeneration is cut ~25 % at Peckish, then ~25 / 55 / 100 %. The coded tier fires only from `HUNGRY == 2` and runs `0.002 -> 0.0013 -> 0.0008 -> 0.0`, i.e. -35 / -60 / -100 %, with level 1 having no effect at all — the sister page `thirsty.md` quotes that -35 / -60 / -100 set. Verify against `BodyDamage.Update` and `BodyDamage.<init>` (`standardHealthAddition` etc.).
- Claims each level decreases "body heat generation" and that every positive level heals 750 % faster. Slice 03's jar-wide scan puts `HUNGRY`'s whole mechanical footprint in four `BodyDamage` rows (carry capacity, regen tier, the zeroed sleeping health addition at level 4, level-4 health loss at `healthReductionFromSevereBadMoodles / 50`) and `FOOD_EATEN`'s in the hunger gate, an additive `1.5e-4 x level` poison-decay bonus and the `FOOD_EATEN >= 3` eat block — no thermoregulator read and no healing multiplier. Verify against `BodyDamage.Update` and `Thermoregulator`.
- "While the positive moodle is active, hunger will not increase" holds only while *not* exercising: with `FOOD_EATEN >= 1` and running or swiping, `updateStats_Awake` switches to `HungerIncreaseWhenExercise` 1.92e-5 /game-s, twice the idle rate. Verify against `IsoGameCharacter.updateStats_Awake @211-@300`.

## Wikitext

```wikitext
{{LangSwitch}}
{{Navbar player}}
{{Page version|42.12.3}}
{{Infobox moodle
|name=Hungry
|icon=Status_Hunger.png
|type=Mixed
|influence=Eating food
|moodle_id=Hungry
|moodle_id2=FoodEaten
}}
'''Hungry''' is a [[moodle]] that represents the character's hunger state.

== Overview ==
A red background indicates that the player needs to eat [[food]]. A green background shows that the character is well-fed.

Being fed boosts healing rate, whereas being hungry reduces carry capacity, healing rate, and body heat generation.

[[Nutrition]] and hunger are entirely separate mechanics. Burning or gaining calories has no effect on this moodle. An emaciated character can still die when ''Full to Bursting''; conversely, a starving character can die even if well overweight.

Hunger increases at a base rate of <code>0.00032%</code> per tick, or <code>4.32%</code> per in game hour on ''Apocalypse'' settings.

The [[Light Eater|light eater]] trait slows down the hunger rate by 25%, whereas the [[Hearty Appetite|hearty appetite]] trait increases it by 50%.

While the positive moodle is active, hunger will not increase. The positive moodle appears when the player eats enough food to exceed their hunger value.

== Moodle levels ==

=== Negative ===
As hunger increases, the players foraging chance to find food increases up to a 50% increase in search radius.

==== Peckish ====
{{Quote|author=Could do with a bite to eat.}}
* Occurs when hunger is above 15%.
* Health regeneration reduced by ~25%%

==== Hungry ====
{{Quote|author=Could eat a horse right now. Growing weaker.}}
* Occurs when hunger is above 25%.
* Carrying capacity reduced by 1 point.
* Body heat generation slightly decreased.
* Health regeneration reduced by ~25%.

==== Very Hungry ====
{{Quote|author=Weak with hunger.}}
* Occurs when hunger is above 45%.
* Carrying capacity reduced by 2 points.
* Body heat generation further decreased.
* Health regeneration reduced by 55%

==== Starving to Death ====
{{Quote|author=Just a crumb, a berry, a cockroach, anything...}}
* Occurs when hunger is above 70%.
* Body heat generation moderately decreased.
* Carrying capacity reduced by 2 points.
* Health regeneration reduced by 100%
* Health slowly decreases (4.4% per hour) until the character either dies, or consumes enough food to stop starving.

=== Positive ===
Having a positive increases health speed rate of 0.72/s. The character will not gain any hunger until the moodle disappears. The buffs last a short period of time, requiring constant nourishment to maintain them.

==== Satiated ====
{{Quote|author=Gnawing hunger entirely absent.}}
* The player heals 750% faster.
* Poison level decreases 15% faster.

==== Well Fed ====
{{Quote|author=Tummy full. Goodness is making its way through your system.}}
* The player heals 750% faster.
* Poison level decreases 30% faster.

==== Stuffed ====
{{Quote|author=Stomach contented. Health and strength aided.}}
* The player heals 750% faster.
* The player can't eat anymore.
* Poison level decreases 45% faster.

==== Full to Bursting ====
{{Quote|author=Couldn't take another single, solitary bite.}}
* The character is completely full and will not be hungry for a while.
* The player heals 750% faster.
* The player can't eat anymore.
* Poison level decreases 60% faster.

== Trivia ==
* In [[Build 41]], having a positive hunger moodle increased the character's carrying capacity. This is not the case in [[Build 42]] anymore.

== Gallery ==
<gallery>
File:Status_Hunger_32.png|32 px version of the icon
File:Moodle_Icon_Hungry.png|Moodle icon prior to [[Build 42]]
</gallery>

== See also ==
* {{ll|Thirsty}}

== Navigation ==
{{Navbox stats|moodles}}

{{ll|Category:Moodles}}
```
