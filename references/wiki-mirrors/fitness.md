# Wiki mirror — Fitness

**Source:** https://pzwiki.net/wiki/Fitness
**Fetched:** 2026-09-10
**Wiki page version:** 42.18.0
**License:** CC BY-NC-SA 3.0 — attribution: PZwiki contributors

## Digest

- The Fitness skill page, stamped `{{Page version|42.18.0}}`: what Fitness modifies, a per-level multiplier table (block chance, fatigue gain, endurance loss and recovery, attack speed, trip reduction, tall-fence climb), how it is levelled, and the occupations and traits that offset it. Slice 03 uses it for the weight/fitness coupling and the endurance curves.
- Two of its columns match the jar. The endurance **recovery** multiplier 70 % -> 160 % across levels 0–10 is exactly `IsoGameCharacter.getRecoveryMod`'s 0.7 -> 1.6 curve, and the "with athletic" row (36.8 % / 34.4 %) is the loss column x 0.8, consistent with the Athletic 0.8 factor in `IsoPlayer.updateEndurance`.
- Its trait offsets match `character_traits.txt`: Fit +2, Athletic +4, Out of Shape -2, Unfit -4, Low Weight -1, High Weight -1, Very Low Weight -2, Very High Weight -2 — and **Emaciated is absent**, which the jar agrees with, `base:emaciated` carrying no `XPBoosts` at all.
- Claims a per-level endurance **loss** multiplier of 90 % -> 43 %. `updateEndurance` composes a base 1.4, Overweight 2.9, Athletic 0.8 and a x2.3 stage (then pacing and hyperthermia); the only per-level Fitness curve slice 03 read in that area is on recovery, and the page's own footnote hedges the column. Verify against `IsoPlayer.updateEndurance @109-@165` before citing it.
- Claims Fitness reduces "damage taken from long falls" and gives a flat 2 %/level trip reduction. The only trait terms slice 03 found in `handleLandingImpact` are the weight ones (x1.4 / x1.2 and +20 / +10); Fitness instead enters `ClimbOverFenceState.shouldFallAfterVaultOver` as `Rand.Next(100) < n - Fitness` — a chance, not a damage multiplier — and `IsoMovingObject.separate` additively inside a `[1, 80]`-clamped score. Neither is a percentage. Verify against `handleLandingImpact @210-@280` and `IsoMovingObject.separate @694-@897`.
- Silent on the gate that actually stops levelling: `Nutrition.canAddFitnessXp` blocks all Fitness and Strength XP from level 6 with Obese / Emaciated / Very Underweight, and from level 9 with Overweight, so the page's "gain Athletic at 9–10" path is closed to any character outside the (75, 85) weight band — and, thanks to the duplicate test in `characterHaveWeightTrouble`, is *not* closed by plain Underweight. Verify against `Nutrition.canAddFitnessXp @0-@85`.

## Wikitext

```wikitext
{{LangSwitch}}
{{Navbar player}}
{{Page version|42.18.0}}
{{Infobox skill
|name=Fitness
|icon=trait_athletic.png
|type=Physical
|modifies=Melee speed, [[endurance]], [[fatigue]], climbing, damage from falls
|skill_id=Fitness
}}
{{Quote|text=Increases melee attack speed, and speed and success chance of climbing. Decreases exhaustion rate.|author=In-game tooltip.}}
'''Fitness''' is a physical [[skill]].

== Overview ==
Fitness, along with [[strength]], is one of the most important skills that affects many things, previously classified as ''passive''.

It requires significantly more experience points to gain a level, does not benefit from an XP boost, and by default starts at level 5 instead of 0.

== Effects ==
Fitness affects several of the player's physical abilities, including:
* Some combat elements, including the player's attack speed, chance of automatically pushing a zombie away when attacked, and chance of tripping when a zombie that has just fallen over a window or fence lunges at the player's feet.
* The rate of [[endurance]] loss and recovery.
* The player's [[exercise]] speed.
* Damage taken from long falls.

{| class="wikitable theme-red"
|-
! Fitness
| 0
| 1
| 2
| 3
| 4
| 5
| 6
| 7
| 8
| 9
| 10
|-
! Block chance
| +0%
| +2%
| +4%
| +6%
| +8%
| +10%
| +12%
| +14%
| +16%
| +18%
| +20%
|-
! [[Tired|Fatigue]] gain multiplier
| 100%
| 95%
| 92%
| 89%
| 87%
| 85%
| 83%
| 81%
| 79%
| 77%
| 75%
|-
! [[Endurance]] loss multiplier<ref name=":1">Actual endurance loss multipliers may not be exactly what is listed here, as endurance loss has multiple calculations and the multiplier provided by a character's fitness level does not affect [[exercise]]s. The multiplier for endurance loss when using a [[weapon]] has its own calculation.</ref>
| 90%
| 80%
| 75%
| 70%
| 65%
| 60%
| 57%
| 53%
| 49%
| 46%<ref name=":2">These values shouldn't be possible in the base game without bugs or [[Debug mode|debug/admin mode]], as the respective [[Trait#Fitness traits|traits for low or high fitness]] levels should be automatically gained.</ref>
| 43%<ref name=":2" />
|-
! Actual [[endurance]] loss multiplier with [[athletic]]
| -
| -
| -
| -
| -
| -
| -
| -
| -
| 36.8%
| 34.4%
|-
! [[Endurance]] recovery multiplier
| 70%
| 80%
| 90%
| 100%
| 110%
| 120%
| 130%
| 140%
| 150%
| 155%
| 160%
|-
! Attack speed increase
| 0%
| 2%
| 4%
| 6%
| 8%
| 10%
| 12%
| 14%
| 16%
| 18%
| 20%
|-
! Trip reduction
| 0%
| 2%
| 4%
| 6%
| 8%
| 10%
| 12%
| 14%
| 16%
| 18%
| 20%
|-
! Chance to climb tall fences bonus multiplier
| 0%
| 2%
| 4%
| 6%
| 8%
| 10%
| 12%
| 14%
| 16%
| 18%
| 20%
|}

== Leveling ==
Fitness experience is gained by performing fitness [[exercise]]s and hitting enemies with melee attacks while not [[Endurance|overexerted]]. It can also be gained in random intervals while running or sprinting, with an equal chance of receiving either fitness or [[running]] experience whenever experience is gained this way.

=== Occupations ===
The following [[occupation]]s determine a character's initial skill levels.
* [[File:profession_fireofficer2.png]] [[Fire Officer]] (+1)
* [[File:profession_fitnessinstructor.png]] [[Fitness Instructor]] (+3)
* [[File:profession_nurse.png]] [[Nurse]] (+1)
* [[File:profession_rancher.png]] [[Rancher]] (+1)

=== Traits ===
The following [[trait]]s determine a character's initial skill levels.
* [[File:trait_fit.png]] [[Fit]] (+2)
* [[File:trait_athletic.png]] [[Athletic]] (+4)
* [[File:trait_out_of_shape.png]] [[Out of Shape]] (-2)
* [[File:trait_unfit.png]] [[Unfit]] (-4)
* [[File:trait_underweight.png]] [[Low Weight]] (from [[Fast Metabolism]]) (-1)
* [[File:trait_overweight.png]] [[High Weight]] (from [[Slow Metabolism]]) (-1)
* [[File:trait_very_underweight.png]] [[Very Low Weight]] (-2) (not available normally during character creation)
* [[File:trait_obese.png]] [[Very High Weight]] (-2) (not available normally during character creation)

As a character gains levels in fitness, they will gain or lose certain [[trait]]s.

Negative traits [[File:trait_out_of_shape.png]] [[Out of Shape|out of shape]] and [[File:trait_unfit.png]] [[unfit]] can be removed by leveling up fitness.<br>
Positive traits [[File:trait_fit.png]] [[fit]] and [[File:trait_athletic.png]] [[athletic]] can be gained by leveling up fitness.

{| class="wikitable theme-red sortable"
|-
! Fitness
| 0-1
| 2-4
| 5
| 6-8
| 9-10
|-
! Trait
| [[File:trait_unfit.png]] [[Unfit]]
| [[File:trait_out_of_shape.png]] [[Out of Shape]]
| None
| [[File:trait_fit.png]] [[Fit]]
| [[File:trait_athletic.png]] [[Athletic]]
|}

Players should note that fitness levels gained as a result of the [[fit]] and [[athletic]] traits, as well as fitness levels lost as a result of the [[Out of Shape|out of shape]] and [[unfit]] traits, only affect the character's respective skill levels when they are selected during [[Player#Character creation|character creation]].

For example, if a character gains the [[athletic]] trait as a result of reaching level 9 fitness during gameplay, they will receive the trait's icon ([[File:trait_athletic.png]]) in their traits list and the trait's boost to knockback power, but ''not'' the +4 to fitness that the trait offered during character creation.

== Trivia ==
* With 3 or above fitness, a 125% experience boost indicator is shown. However, the bonus is not applied. [[Strength]] and fitness never get any experience boost.{{Bug|XP boost is shown when not applied|42.16.1}}

== See also ==
* {{ll|Exercise}}
* {{ll|Nutrition}}

== References ==
<references />

== Navigation ==
{{Navbox stats|skills}}

{{ll|Category:Physical skills}}
{{ll|Category:Skills}}
```
