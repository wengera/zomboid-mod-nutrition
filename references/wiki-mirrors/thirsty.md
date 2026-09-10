# Wiki mirror — Thirsty

**Source:** https://pzwiki.net/wiki/Thirsty
**Fetched:** 2026-09-10
**Wiki page version:** 42.12.3
**License:** CC BY-NC-SA 3.0 — attribution: PZwiki contributors

## Digest

- The Thirsty moodle page, stamped `{{Page version|42.12.3}}`: four levels with their per-level penalties, the base thirst rate, the activity/temperature modifiers on it, and the auto-drink floor.
- The base rate checks out. `2.875%` per in-game hour is `ThirstIncrease` 8.0e-6 /game-s x 3600 = 2.88 %, and thirst really is linear — there is no `(1 - T)` damping term, unlike hunger. Its sleeping x0.125 row is exactly `ThirstSleepingIncrease` 1.0e-6 / 8.0e-6. (Its `0.000213%` per tick figure is inconsistent with both its own per-hour number and `defines.lua:9`.)
- The penalty columns match the jar where the code was read: carry capacity 0 / -1 / -2 / -2 (`BodyDamage.UpdateStrength`, the THIRST branch being identical to HUNGER) and health regeneration normal / -35 % / -60 % / -100 %, which is exactly `0.002 / 0.0013 / 0.0008 / 0.0` — useful external corroboration of the tier mapping `docs/superpowers/plans/03-notes.md` marks Ev I.
- Thresholds are off by a point at both ends: the page says above 13 % and above 85 %, `MoodleStat.<clinit>`'s `THIRST` row is 0.12 / 0.25 / 0.70 / **0.84**, strict `>`. Verify against `MoodleStat.<clinit> @172-@187`.
- Claims sprinting carries the same x1.2 as running. `getRunningThirstReduction` returns 1.2 only for `IsoPlayer.getInstance().IsRunning()` — a different flag from `isSprinting()`, and gated on the local instance, so on a dedicated server it may never fire at all; the asleep branch applies neither it nor the heat multiplier, only the trait factor. Verify against `IsoGameCharacter.getRunningThirstReduction @0-@21` and `updateThirst @74-@175`.
- Claims health drains `22%` per in-game hour at Dying of Thirst, and 10–70 % reductions in "heat dissipation" per level. The health drain is **right in kind, wrong in number**: `BodyDamage.Update` does have a `THIRST == 4` branch, `healthReductionFromSevereBadMoodles / 10` = 1.65e-3 per multiplier unit (`@1320-@1358 L2377-L2379`) — five times the `HUNGRY == 4` branch's `/50` — but it carries `getMultiplier()` without `getDeltaMinutesPerDay()`, so its rate is day-length dependent: **11.88 %/game-hour on the 60-minute default, 17.82 % on a 90-minute day** (measured −17.820029, run `scenario-20260910-052624`), matching 22 % at no standard day length. *(Slice 03 originally recorded "a `HUNGRY == 4` branch only"; that was wrong and was corrected in slice 04.)* No thermoregulator read of `THIRST` exists anywhere. Verify against `BodyDamage.Update @1134-@1172` (hunger), `@1320-@1358` (thirst) and `Thermoregulator`.
- Auto-drink at 10 % is right (`ThirstLevelToAutoDrink` 0.1; `autoDrink` requires `THIRST > 0.1`) but the page omits every gate around it: `Core.getOptionAutoDrink()`, `player.getAutoDrink()`, the `"AutoDrink"` Lua hook, and server-side-only execution.

## Wikitext

```wikitext
{{LangSwitch}}
{{Navbar player}}
{{Page version|42.12.3}}
{{Infobox moodle
|name=Thirsty
|icon=Status_Thirst.png
|type=Negative
|influence=Drinking [[Fluid|liquid]]<br>Eating some [[food]]s
|moodle_id=Thirst
}}
'''Thirsty''' is a [[moodle]] that represents the character's thirst state.

== Overview ==
This moodle occurs when the [[player]] has gone a while without drinking water or other [[fluid]]s. Dehydration leads to weakness, reduced carrying capacity, increased heat generation, and can be fatal.

Thirst is reduced primarily through bottles, or by eating [[food]], most of which will decrease thirst. At 10% thirst, the player can auto-drink out of [[fluid container]]s that have at least 120mL, where [[Water (fluid)|water]], [[Seltzer Water (fluid)|seltzer water]], or [[Water (Tainted) (fluid)|tainted water]] are the primary fluid.

Tainted water can cause the player [[sick]]ness if not cleaned first through boiling.

Thirst ticks at a base rate of <code>0.000213%</code> per tick, or <code>2.875%</code> per in game hour on ''Apocalypse'' settings.
A modifier is applied to this rate based on the actions of the player:
* Standing still - 1.0x
* Walking - 1.0x
* Running - 1.2x
* Sprinting - 1.2x
* Sleeping - 0.125x

Thirst is further modified by skin temperature, core temperature, and insulation. It also effects the 'body fluids' system, which influences how much the character can sweat. As fluids reduce the players ability to sweat is reduced, inhibiting their ability to cool down efficiently, increasing body temperature and thus thirst rate. This can be a fatal feedback loop.

The [[Low Thirst|low thirst]] trait slows down the thirst rate by 50%; conversely, [[High Thirst|high thirst]] increases it by 100%.

== Moodle levels ==

=== Slightly Thirsty ===
{{Quote|text=Dry Mouth.}}
* Moodle appears when thirst is above 13%
* Health regenerates normally.
* No effect on carrying capacity.
* Heat dissipation reduced by 10%.

=== Thirsty ===
{{Quote|text=Dehydrated.}}
* Occurs when thirst is above 25%.
* Carrying capacity reduced by 1 point.
* Heat dissipation reduced by 20%.
* Health regeneration reduced by 35%.

=== Parched ===
{{Quote|text=Feeling faint and dizzy.}}
* Occurs when thirst is above 70%.
* Carrying capacity reduced by 2 points.
* Heat dissipation reduced by 60%.
* Health regeneration reduced by 60%.

=== Dying of Thirst ===
{{Quote|text=Water... water...}}
* Occurs when thirst is above 85%.
* Carrying capacity reduced by 2 points.
* Heat dissipation reduced by 70%.
* Health regeneration reduced by 100%.
* Health slowly decreases (22% per in game hour) until the character either dies, or quenches their thirst.

== Gallery ==
<gallery>
File:Status_Thirst_32.png|32 px version of the icon
File:Moodle_Icon_Thirsty.png|Moodle icon prior to [[Build 42]]
</gallery>

== See also ==
* {{ll|Hungry}}
* {{ll|Fluid}}

== Navigation ==
{{Navbox stats|moodles}}

{{ll|Category:Moodles}}
```
