# Wiki mirror — Moodle

**Source:** https://pzwiki.net/wiki/Moodle
**Fetched:** 2026-09-10
**Wiki page version:** 42.13.2
**License:** CC BY-NC-SA 3.0 — attribution: PZwiki contributors

## Digest

- The moodle index, stamped `{{Page version|42.13.2}}`: one paragraph per moodle (24 live, 5 removed or unimplemented) saying what causes it and roughly what it does. No thresholds, rates or per-level numbers anywhere — those live on the per-moodle pages (`hungry.md`, `thirsty.md`).
- Confirmed negative result we rely on: there is **no weight moodle**. `MoodleType`'s registered statics contain nothing body-weight-related, and this page's "Heavy load" is inventory encumbrance — `MoodleStat.HEAVY_LOAD`, thresholds 1.0 / 1.25 / 1.5 / 1.75 on the carry-weight ratio, not on kilograms of body mass.
- Repeats the Hungry page's "nutrition and hunger are entirely separate; burning or gaining calories has no effect on this moodle", which slice 03 confirms in both directions (`docs/superpowers/plans/03-notes.md` Q3).
- Its roster is short of the jar and mis-frames the one moodle that matters most to the body model: the list has no `FoodEaten` entry, folding the green/well-fed state into Hungry, whereas `MoodleType.<clinit>` registers 27 statics including a distinct `FOOD_EATEN` that is not threshold-driven at all — `Moodle.Update` reads `BodyDamage.healthFromFoodTimer` against `standardHealthFromFoodTime` 1600 (levels at >0 / 1600 / 3200 / 4800), and that timer is filled from `|getHungerChange()| x f x 13000`, i.e. from hunger change and never from calories. It is `FOOD_EATEN`, not `HUNGRY`, that gates the hunger rate. Verify against `MoodleType.<clinit>` and `Moodle.Update @2306-@2454`.
- Hyperthermia "primarily increases dehydration and fatigue rates" matches `Thermoregulator.updateBodyMultipliers` (the heat side raises `fluidsMultiplier` and `fatigueMultiplier`), but the page never mentions the cold side's only body-model effect: `energyMultiplier` (`1 + 0.05*prim^2 + 0.10*sec^2`, cold only) multiplies **resting and sleeping calorie burn** and nothing else — the three moving branches never read it. Verify against `Nutrition.updateCalories @268-@316`.
- Presents moodles as a pure display layer. For the mod the load-bearing details are that thresholds are Java statics registered in `MoodleStat.<clinit>` (there is no moodle script under `media/scripts`) and retunable at runtime via `MoodleStat.setLowestThreshold` and friends, and that `Moodles.Update` has no MP side guard: both sides recompute levels from their own stats, so a client-side moodle read taken right after a server stat write can lag the 1 Hz `PlayerStatsPacket`.

## Wikitext

```wikitext
{{LangSwitch}}
{{Navbar player}}
{{Page version|42.13.2}}
A '''moodle''' is an indicator of the current emotional and physical state of the [[player]], similar to [[Wikipedia:Status effect|''status effects'']] in [[Wikipedia:Role-playing game|role-playing games]]. Moodles are displayed in the top right-hand corner of the screen, and hovering the cursor over an individual moodle provides further information.
{{toc|right}}

== List of moodles ==

=== [[File:Status_Hunger.png|32x32px]]Hungry ===
{{Main|Hungry}}
This moodle represents the character's hunger state. A red background indicates that the player needs to eat [[food]]. A green background shows that the character is well-fed.
Being fed boosts healing rate whereas being hungry reduces carry capacity, healing hate and body heat generation.

Currently, [[nutrition]] and hunger are entirely separate. Burning or gaining calories has no effect on this moodle. An emaciated character can still die when ''Full to Bursting''; conversely, a starving character can die even if well overweight.

=== [[File:Status_Thirst.png|32x32px]]Thirsty ===
{{Main|Thirsty}}
This moodle appears after the character had gone for a while without drinking some beverage. Dehydration leads to weakness, reduced carrying capacity, slightly increased heat generation, and eventual death.
Thirst can be quenched primarily through bottles filled with clean water; many other [[Food|consumables]] help influence thirst as well, usually by decreasing it.
Sources of hydration must be clean and the water itself must be boiled, lest [[sick]]ness can occur.

=== [[File:Mood_Panicked.png|32x32px]]Panic ===
{{Main|Panic}}
This moodle represents the character's panic state, usually due to the sight of nearby zombies. Panic penalizes many combat abilities, but also provides occasional boons.

Panic can be controlled by consuming [[beta blockers]] or [[Items#Alcohol|alcohol]]. Certain [[trait]]s influence panic rates, and characters gradually become resistant to panic the longer they survive.

=== [[File:Mood_Bored.png|32x32px]]Bored ===
{{Main|Bored}}
This moodle appears generally when the character is inactive indoors, though certain consumables and activities may also cause it. Boredom dissipates when outdoors or when panicking. Boredom in itself serves as a warning for another moodle, [[#Unhappy|Unhappiness]], but has no direct bearing on the character otherwise.

=== [[File:Mood_Stressed.png|32x32px]]Stressed ===
{{Main|Stressed}}
This moodle represents the character's stress from a variety of circumstances, chief among them are the [[Sick|fear of infection]] and the [[smoker]] trait. Accumulated stress negatively impacts combat ability, and chronic stress can lead to [[#Unhappiness|unhappiness]]. Stress can be managed through consumables such as [[cigarettes]] or by reading [[Literature|literature]].

=== [[File:Mood_Sad.png|32x32px]]Unhappy ===
{{Main|Unhappy}}
This moodle appears when sources of unhappiness accumulate for long enough to cause the negative emotional state. Unhappiness has a minor effect on item interaction speeds, and can be controlled with various medicinal or recreation items, or through eating quality food items.

=== [[File:Mood_Drunk.png|32x32px]]Drunk ===
{{Main|Drunk}}
This moodle appears when the character has consumed sufficient [[Items#Alcohol|alcohol]] to become intoxicated. Progressive levels of inebriation cause drowsiness and delayed vehicle controls, as well as penalties to Search Mode. Drunkenness fades over time.

=== [[File:Status_HeavyLoad.png|32x32px]]Heavy load ===
{{Main|Heavy load}}
This moodle alerts the player that the character is overloaded with too many, or too cumbersome items. Progressive overencumberance greatly reduces movement and attack speed, increases endurance loss, and eventually damages the character for up to 25% of their health. Overencumbrance can be remedied in several ways, most frequently by dropping or transferring items out of the inventory or into equipped bags.

=== [[File:Status_DifficultyBreathing.png|32x32px]]Endurance ===
{{Main|Endurance}}
The Endurance moodle alerts the player that the character is becoming fatigued from excessive physical activity, such as running, swinging weapons, or carrying a heavy load. As the endurance moodle progresses, the character will experience rapidly decreasing combat ability, reduced movement speed, limitations on sprinting and running, and a more rapid rate of [[Tired|tiredness]]. Staying idle, sitting on the ground, or resting on furniture are the most accessible ways of recovering endurance.

=== [[File:Mood_Sleepy.png|32x32px]]Tired ===
{{Main|Tired}}
This moodle occurs when the character has stayed awake for an extended period of time, and is becoming tired. Being tired rapidly penalizes combat ability, the vision cone and awareness, and linearly decreases [[Endurance]] recovery. Tiredness can be remedied by sleep, or by caffeinated beverages.

=== [[File:Status_TemperatureHot.png|32x32px]]Hyperthermia ===
{{Main|Hyperthermia}}
This moodle appears when the character's body reaches an above-normal temperature range. Possible causes include hot weather, physical activity, insulated clothing, and zombie infection. Hyperthermia primarily increases dehydration and fatigue rates.

=== [[File:Status_TemperatureLow.png|32x32px]]Hypothermia ===
{{Main|Hypothermia}}
This moodle warns the player of unfavorably low body temperatures in the character. Weather conditions, inadequate clothing, and being wet are primary factors that may cause this moodle. Hypothermia sharply reduces movement and attack speeds, and may eventually bring the character to the brink of death.

=== [[File:Status_Windchill.png|32x32px]]Windchill ===
{{Main|Windchill}}
This moodle appears occasionally when outdoors, in weather such as blizzards or other cold storms. It serves to reduce the character's perceived outside temperature and increase the risk of hypothermia, as long as they remain outside a building.

=== [[File:Status_Wet.png|32x32px]]Wet ===
{{Main|Wet}}
The wet moodle notifies the player of accumulated moisture on the character. Sources of wetness are rain and sweat from exerting physical activity. Wetness slightly penalizes character movement speed and can risk them catching a cold. It can be avoided or prevented through seeking shelter, wearing insulated clothes, drying oneself with a towel, or having traits like an [[outdoorsman]].

=== [[File:Status_InjuredMinor.png|32x32px]][[File:Status_InjuredMajor.png|32x32px]]Injured ===
{{Main|Injured}}
At certain levels of health remaining, the Injured moodle appears on-screen with a different severity level, serving to alert the player of the character's health state. In itself it doesn't represent the presence of [[Health#Types of injuries|injury]], as some wounds do not lower health enough to show the moodle. Progressive levels of the moodle penalize carrying capacity.

=== [[File:Mood_Pained.png|32x32px]]Pain ===
{{Main|Pain}}
This moodle frequently accompanies the character sustaining an [[Health#Types of injuries|injury]] of some description. Another possible cause, currently, is exercise fatigue. Pain gradually decreases combat ability and can prevent the character from sleeping if high enough. Pain dissipates as wounds heal, or can be temporarily controlled with [[painkillers]] or [[fluid|alcohol]].

=== [[File:Status_Bleeding.png|32x32px]]Bleeding ===
{{Main|Bleeding}}
The bleeding moodle may appear at the same time as the character suffers an injury that breaks the skin. The moodle warns of the number of active, bleeding wounds on the body. Bleeding is remedied by applying bandages.

=== [[File:Status_MovementRestricted.png|32x32px]]Restricted movement ===
{{Main|Restricted movement}}
The restricted movement moodle indicates the character is unable to sprint due to being barefoot, having leg injuries, being [[Heavy Load|overloaded]], wearing heavy clothes, or suffering from moodles that impact speed.

If the character is barefoot and has less than 5 in physical fitness, the restricted movement moodle will appear; otherwise, if the character has more than 5 in physical fitness, the moodle will not appear.

=== [[File:Mood_Ill.png|32x32px]]Has a cold ===
{{Main|Has a cold}}
If the character is [[wet]] or [[Hypothermia|cold]] for long enough, they may contract this disease and have this moodle appear. Having a cold can periodically result in sneezing and coughing, which attract [[zombies]] nearby. A cold can be cured by staying indoors, well fed, hydrated, and not fatigued.

=== [[File:Mood_Nauseous.png|32x32px]]Sick ===
{{Main|Sick}}
The sickness moodle has several possible causes, but the most prevalent is infection through a [[zombie]] attack. Other sources include poisoning, ingesting rotten or dangerous foods, and proximity to decaying corpses. As sickness worsens, the character suffers decreased carrying capacity, higher body temperatures, and diminished healing rates. Non-fatal sickness may dissipate over time, with [[lemongrass]] aiding the process. However, in an unmodified or uncustomized game, zombie infection is always fatal.

=== [[File:Mood_NoxiousSmell.png|32px]]Noxious smell ===
{{Main|Noxious smell}}
Noxious smell is a moodle with 2 distinct types: corpse sickness and toxic fumes. The corpse sickness type is obtained while being near the rotting corpses, making the character get the [[sick]] moodle slowly. The toxic fumes type is obtained when a generator is running indoors, which damages the player up to 5% of [[health]].

A [[GasMask (tag)|gas mask]] or [[SCBA (tag)|full suit]] can help reduce or prevent the effects of noxious smells.

=== [[File:Mood_Discomfort.png|32px]]Discomfort ===
{{Main|Discomfort}}
Discomfort moodle appears when a character is wearing too many clothes that affect the discomfort value. Discomfort increases the player's [[unhappiness]].

=== [[File:Mood_Dead.png|32x32px]]Dead ===
{{Main|Dead}}
The only moodle that remains on-screen once the character reaches 0 health is the Dead moodle. This appears when the death occurs without suffering the zombie infection.

=== [[File:Mood_Zombified.png|32x32px]]Zombie ===
{{Main|Zombie (moodle)}}
An alternative to the Dead moodle is the Zombie moodle, which appears in the same circumstance of reaching 0 health, but requires the character to have been infected by a zombie.

== Removed, future, or unobtainable moodles ==

=== [[File:Mood_Angry.png|32x32px]]Angry ===
{{Main|Angry}}
In previous versions of [[Project Zomboid]], the anger moodle pops up for both sides when [[Survivor|NPC]]s reject team requests made by a player or another NPC. Each level of the Anger moodle beyond irritated progressively blocks interaction attitudes, culminating in open hostility with the risk of combat at the most intense stage.

This moodle is disabled due to there being no NPCs in the current game build, although it is expected to return when they're reintroduced. Players can trigger it by enabling the [[debug mode]], and increasing the anger slider from the moodles menu; even so, anger has absolutely zero effect on character actions or abilities.

=== [[File:Mood_Hungover.png|32x32px]]Hungover ===
{{Main|Hungover}}
This moodle was used to indicate that the character had been staying too long outside, after or during intoxication. The only solution was to stay indoors. It is currently not possible to obtain it.

=== Fear ===
{{Main|Fear}}
Fear has yet to be implemented, but the value can be seen in debug mode, and is affected by some [[television]] and [[radio]] shows. Changing the ''Fear'' value has no effects currently.

=== Morale ===
{{Main|Morale}}
Morale has yet to be implemented, but the value can be seen in debug mode. Changing the ''Morale'' value has no effects currently.

=== Sanity ===
{{Main|Sanity}}
Sanity has yet to be implemented, but the value can be seen in debug mode. Some game files with the sanity sound files can still be found, indicating sanity was supposed to be added at one point. Changing the ''Sanity'' value has no effects currently.

== Gallery ==
<gallery>
File:Mood_Concentrating.png|<code>Concentrating</code> moodle icon added in [[Build 42]], currently unavailable
File:Mood_Concentrating_32.png|32px <code>Concentrating</code> moodle icon added in Build 42, currently unavailable
File:Mood_Dizzy.png|<code>Dizzy</code> moodle icon added in Build 42, currently unavailable
File:Mood_Dizzy_32.png|32px <code>Dizzy</code> moodle icon added in Build 42, currently unavailable
File:Mood_Exhausted.png|<code>Exhausted</code> moodle icon added in Build 42, currently unavailable
File:Mood_Exhausted_32.png|32px <code>Exhausted</code> moodle icon added in Build 42, currently unavailable
File:Mood_Happy.png|<code>Happy</code> moodle icon added in Build 42, currently unavailable
File:Mood_Happy_32.png|32px <code>Happy</code> moodle icon added in Build 42, currently unavailable
File:Mood_Scared.png|<code>Scared</code> moodle icon added in Build 42, currently unavailable
File:Mood_Scared_32.png|32px <code>Scared</code> moodle icon added in Build 42, currently unavailable
File:Status_HearingImpaired.png|<code>HearingImpaired</code> moodle (status) icon added in Build 42, currently unavailable
File:Status_HearingImpaired_32.png|32px <code>HearingImpaired</code> moodle (status) icon added in Build 42, currently unavailable
File:Status_Sedated.png|<code>Sedated</code> moodle (status) icon added in Build 42, currently unavailable
File:Status_Sedated_32.png|32px <code>Sedated</code> moodle (status) icon added in Build 42, currently unavailable
File:Status_VisionImpaired.png|<code>VisionImpaired</code> moodle (status) icon added in Build 42, currently unavailable
File:Status_VisionImpaired_32.png|32px <code>VisionImpaired</code> moodle (status) icon added in Build 42, currently unavailable
File:Status_Wired.png|<code>Wired</code> moodle (status) icon added in Build 42, currently unavailable
File:Status_Wired_32.png|32px <code>Wired</code> moodle (status) icon added in Build 42, currently unavailable
File:Moodle_Bkg_Good_1.png|Old moodles "good 1" background
File:Moodle_Bkg_Good_2.png|Old moodles "good 2" background
File:Moodle_Bkg_Good_3.png|Old moodles "good 3" background
File:Moodle_Bkg_Bad_1.png|Old moodles "bad 1" background
File:Moodle_Bkg_Bad_2.png|Old moodles "bad 2" background
File:Moodle_Bkg_Bad_3.png|Old moodles "bad 3" background
File:Moodle_Bkg_Bad_4.png|Old moodles "bad 4" background
</gallery>

== See also ==
* {{ll|Food}}
* {{ll|Health}}
* {{ll|Literature}}
* {{ll|Medical}}
* {{ll|Nutrition}}

== References ==
<references/>

== Navigation ==
{{Navbox stats|moodles}}

{{ll|Category:User interface}}
```
