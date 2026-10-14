# Nutrition Revamp — operator guide

Nutrition Revamp 1.0.0 is a realism nutrition overhaul for Project Zomboid Build 42 dedicated servers, game build 42.21 and newer.
It tracks 27 nutrients beyond the four vanilla macros and re-bases 522 vanilla foods on published food-composition data.
From its own body model it drives hunger, thirst, body fat and lean mass, weight, strength, and a table of deficiency and excess effects, with caffeine, alcohol and sleep debt beside them.
This guide is for the person running the server: what to install and set, what players will see, what the mod models and where it falls short.
The release notes are `CHANGELOG.md` and the neighbour mods are `COMPATIBILITY.md`, both beside this file.

## Install

- The mod id is `NutritionRevamp`. Add it to the server's `Mods=` line by that id, and add the Workshop item to the server's `WorkshopItems=` line.
- The server's mod list is the one that counts: a joining client loads what the server lists, whatever its own mod menu holds.
- The mod declares no dependency. MoodleFramework is optional: when a client has it, the mod's moodles use it; without it the mod draws its own icon column.
- The mod is built and tested for game build 42.21. Its folder has one version directory, `42.21/`, holding `mod.info` and the sandbox options, and `common/` holding everything else.
- Turn the server options `SleepAllowed` and `SleepNeeded` on if you want the mod's sleep model. With either off, the game resets fatigue itself and the mod's sleep state stays at rested.

## Set the vanilla Nutrition option off

Set the vanilla sandbox option `Nutrition = false` before the first boot.
The mod owns the macro stores and body weight. With vanilla's nutrition update on, vanilla keeps subtracting from the calorie, carbohydrate, lipid and protein stores on its own clock and rewrites the weight flags every tick. The mod then misreads that drain, and the two models fight over weight.

The mod never changes the option itself. When it finds the option on at boot, it prints a warning line at every log level, and its self-report reads `nutritionOn=true`.

## Sandbox options

Every option sits on the sandbox page `Nutrition Revamp` under the prefix `NR`.

| option | default | what it does |
|---|---|---|
| `NR.Mode` | 1 (Managed) | Managed: vanilla's hunger, thirst and fatigue rates are set to zero at server start, and the mod writes those stats once a game minute from its own model. Overlay: vanilla's rates and stats stand; the mod tracks nutrients and writes only its effects. Read once at server start; a change needs a restart. |
| `NR.LogLevel` | 2 (Normal) | How much the mod prints to the server console: 1 Quiet (the self-report and warnings only), 2 Normal, 3 Verbose. |
| `NR.LegacyMirror` | true | On: every minute the server writes the vanilla calorie, protein, carbohydrate and lipid stores from the mod's trailing 24 hours, so vanilla code and other mods that read those stores keep working. Off: the mod leaves those stores alone. |
| `NR.OnsetSpeed` | 1.0 (0.5 to 30) | Multiplies how fast the slow deficiencies develop and recover (the nutrients that take more than 90 days to reach a clinical deficiency). 1.0 is real time. Vitamin C, the other fast vitamins, water, caffeine, alcohol, glycogen and sleep are never scaled. |
| `NR.DeficienciesCanKill` | true | On: the most severe states drain health until treated: starvation with the fat reserves gone, long clinical scurvy, beriberi or pellagra, severe dehydration or low blood sodium, and an iron overdose. Off: they never drain health. |
| `NR.ExcessEffectsOn` | true | On: an intake above a nutrient's upper limit raises that nutrient's excess level (the magnesium, niacin, folate and vitamin E limits apply to supplemental or added forms, so food never reaches them). Off: every excess level reads zero; intake is still tracked. |
| `NR.BalanceBonus` | true | On: while every tracked nutrient is replete, endurance regeneration during sleep and fatigue recovery run 5 percent faster. A game choice. |
| `NR.Severity` | 1.0 (0 to 3) | Scales every penalty a deficiency or an excess brings. 0 removes them all except the health drains, which `NR.DeficienciesCanKill` controls. Short Sighted needs 1.0 or more. |
| `NR.VisibilityMode` | 2 (Bands) | How much each player's interface shows: 1 Symptoms, 2 Bands, 3 Numbers. A character with the Nutritionist trait sees Numbers whatever the option. |
| `NR.RecordKeepDays` | 30 (0 to 3650) | A player's nutrition record is dropped after this many real days without the player online; a returning player then starts a fresh record from the character as it stands (see the lost-record limitation under Body, energy and exercise). 0 keeps every record. Counted in real time, because game days pass at each server's own speed. Time the server is down counts too. |

The server re-reads the options every in-game minute, so a change made while the server runs takes effect without a restart, except `NR.Mode`, which is read at start.

## Managed and Overlay

**Managed** (the default). At server start the mod saves vanilla's hunger, thirst and fatigue rise rates and sets them to zero. Once a game minute it writes hunger, thirst and fatigue from its own model.
- The mode is read at start; a change needs a restart.
- With the rates at zero, a stopped writer stops hunger rather than falling back to vanilla.
- Other mods that read vanilla's hunger, thirst or fatigue rates read zero. A mod that needs the saved values can call `NutritionRevamp.vanillaRate(key)`.
- A rate tweak from another mod has no effect, because the mod's model sets those stats. A mod that sets the rates again after the mod's start handler brings vanilla's drift back between the minute writes, and the next write takes it back.

**Overlay.** Vanilla's rates and its hunger, thirst and fatigue stand. The mod still tracks nutrients, the body and the stomach, and writes its effects: mood and sickness floors, panic, body temperature and intoxication. Drinking that the game does on its own (auto-drink) is not captured in Overlay.

The self-report says which mode is running and whether the rates were zeroed.

## Where the records live

Each player's record is kept in files under the server's cache directory, in the folder `Lua/NutritionRevamp/<server name>/`.
- Each player has a pair of slot files, written in turn, so a crash during a write leaves the other file whole. An index pair holds each player's last-seen time.
- A player's slot is written at most once a real minute, and soon after an eat, a drink or a respawn. A clean stop loses at most the last real minute of digestion.
- After a hard kill the world goes back to its last save, while the record files keep their latest state.
- A player unseen for `NR.RecordKeepDays` real days loses the record. Lua cannot delete a file, so a pruned player's two files are emptied, not deleted.
- The folder is named after the server, so a world wiped under the same server name finds the old files, and every returning player's record carries over, the respawn count included. For a fresh start, delete the folder by hand.

## What players see

- **The panel.** The `;` key opens a movable, collapsible panel; players can rebind the key on the mod's options page. The rows depend on `NR.VisibilityMode`:
  - **Symptoms:** six words for energy, hydration, deficiency, excess, stimulant and sleep.
  - **Bands:** also the weight band, the weight, a **Body fat** word (Very lean, Lean, Healthy, High or Very high, with cut points by sex; a shown word holds until the fat share leaves its band by half a percentage point), the energy state, hydration, and a grade for each tracked nutrient (Replete, Marginal, Depleted or Clinical).
  - **Numbers:** also fat and lean mass, each nutrient's store and excess level, caffeine in the body, blood alcohol and sleep debt.
- **The character tab.** A Nutrition tab in the character info window shows the same rows.
- **The food tooltip.** A band below each food's tooltip says where its values come from. At Bands it lists the four macros and the nutrients the item is rich or low in; at Numbers it lists every nutrient. The band shows the values of a whole item. A player can turn the band off on the options page.
- **The moodles.** Seven moodles: Energy (Peckish to Starving), Hydration (Slightly dry to Severely dehydrated), Deficiency (Marginal to Clinical), Excess (Elevated to Excessive), Stimulant (Alert to Overdosed), Sleep (Short on sleep to Collapsing) and Overfull (Pleasantly overfull to Painfully stuffed). With MoodleFramework they are drawn through it; without it, in the mod's own icon column. A player can turn them off on the options page. Vanilla's own hunger and thirst moodles still show.

## What the mod models

- **Nutrients beyond the macros.** Thirteen vitamins and choline, seven minerals, fibre, essential fatty acids, sodium, potassium, caffeine and alcohol. Most have a store that fills from food and empties at its own rate, a daily requirement, and steps of deficiency and excess.
- **Foods.** 522 vanilla foods have their calories, carbohydrates, proteins and lipids re-based on published food-composition data, and each carries a nutrient table. A food the table does not map, such as another mod's food, gets values estimated from its food type and energy. A food mod can declare its own nutrients through the documented `NR_Nutrients` item key. Dishes and crafted food are counted from their ingredients. Drinks count by their fluid. Water drunk straight from the world counts as water.
- **Eating.** Every eat and drink through the game's own actions is captured on the server. Food passes through a stomach that empties over time before it is absorbed, and some nutrients absorb better or worse with others in the meal.
- **Hunger.** Hunger comes from physiology, not from vanilla's per-food hunger values:
  - how full the stomach is, with protein filling more and drinks filling less;
  - a pool of recently eaten energy, which fades within a few hours;
  - the deficit drive: the last 24 hours' energy balance and the body's fat reserves;
  - the time of day, recent hard exercise (which briefly blunts hunger), sleep debt and nicotine withdrawal.

  Past about 730 g in the stomach the Overfull moodle rises in four steps to 1100 g. It warns and never blocks an eat. In Managed mode hunger is held below vanilla's top level, so it never kills.
- **Thirst.** A body water pool with sodium and potassium. Water is lost through basic turnover and sweat, and sweat grows with work and heat. Salt changes how much water the body holds. Thirst follows the water the body lacks, and water still in the stomach already eases it. In Managed mode thirst is held below vanilla's top level.
- **Monotony.** Eating the same food day after day lowers mood, up to the first level of Unhappy and Bored; a staple such as bread, rice or pasta counts a quarter as much. It fades over the days after the diet varies.
- **The body.** A body of fat mass and lean mass, split from the starting weight by sex. Resting and activity expenditure, eating and training move both. The total is written into vanilla's weight, which sets the vanilla weight band traits (Emaciated to Obese).
- **Exercise and energy use.** Energy use follows the game's own activity level. A Fitness exercise is billed at the energy cost of its type: squats 3.0 MET, push-ups and sit-ups 3.8, burpees 7.5, and the curls and the dumbbell press 3.5. Hard exercise leaves a short after-burn. Muscle glycogen falls with hard work and a low-carbohydrate diet, and blood glucose falls with exhausting work or alcohol on an empty stomach.
- **Strength and training.** Strength experience is never touched. The shown Strength level is held under a ceiling set by lean mass, training and the recent energy deficit. Strength held for two weeks leaves a memory that keeps much of it through a long lay-off. Exercise reps, melee hits, tree chopping, climbing and carrying heavy loads count as resistance training, and time at a raised activity level counts as aerobic training. Carry capacity moves with dehydration, long hours awake, caffeine and body fat.
- **Deficiency and excess.** Each deficiency and excess brings effects of its own: fatigue, mood, sickness, slower healing, heavier bleeding, faster wound infection, colds, body temperature, bruising, and Short Sighted at a clinical vitamin A deficiency. A long, well-stocked vitamin A and zinc intake grants Night Vision. The most severe states drain health (see `NR.DeficienciesCanKill`).
- **Caffeine, alcohol and sleep debt.** Caffeine is absorbed and cleared over hours, builds tolerance and brings withdrawal. Alcohol raises blood alcohol and drives the game's intoxication, with a hangover after. Sleep debt builds from short nights and raises hunger.

## Known limitations

The mod's own code lists these. Some are game choices, some are walls the game puts in a mod's way.

**Hunger and the stomach**
- Displayed hunger never reaches 0 after a meal.
- Fibre sates only through its mass. Sugar, starch and other carbohydrates sate alike per calorie; protein sates more and fat a little less, by a fitted weighting.
- Alcohol's calories sate like any other energy. Sugary drinks, ketosis, aerated foods and eating speed have no special effect on hunger.
- The exercise part of an energy deficit reaches hunger only over weeks, so a regular exerciser who eats to balance reads lower hunger for weeks.
- Heavy work the model does not class as vigorous raises hunger more than heavy labour does in studies.
- A resting fast's hunger drive levels off after about a day and a half; it climbs further only as fat is burned.
- Heat does not lower appetite (cold reaches hunger through the extra energy it costs), and an injury costs no extra energy.
- Short sleep raises hunger by a capped factor. The rise steps in once a day, when the mod's 24-hour sleep tally closes, not on waking, so a short night that crosses that close raises hunger in two steps a day apart. After a short night, nights of exactly the needed length repay nothing, so the rise holds until a longer night.
- Right at the end of hard exercise, hunger reads lower than studies show.
- On a generous diet, hunger dips less after meals than in the overfeeding study the model was checked against.
- Every Fitness set counts as hard resistance work for the brief hunger dip, whatever the exercise.
- Nicotine withdrawal's rise in hunger rests on one small trial and fades over 26 weeks. A smoker who keeps smoking sees the rise between smokes. A character first seen already in withdrawal shows none until the next smoke.
- A new character, or one who just respawned, reads as if they had eaten evenly the day before. They reach the first energy moodle after several hours without food.
- An eat in a new record's very first minute does not count toward the meal pool.
- An eat another mod makes without the game's eat action counts a minute late and as calories and macros only. A drink another mod makes outside the game's drink actions is not seen.
- When the mod first sees a character, it reads the character's current low hunger as a meal already eaten, up to a cap; a hunger above what the stomach's fullness allows drops to that level at once.
- The game itself still refuses to start an eat at the top level of its own fullness moodle.

**Thirst and fluids**
- Water from food breakdown and from breathing is not counted. Caffeine causes no extra water loss in a regular drinker.
- At high, sustained salt intakes the body is modelled as holding more water than it does. A salt shortfall shrinks body water only so far before thirst lets the water be drunk back.
- Sweat gets less salty only with a sodium shortfall, not with heat alone.
- Water still in the stomach eases thirst for as long as it stays there.
- A drink from a world water source counts at most the amount the drink action planned, and always counts as plain water, even from a tainted source. While the drink runs, the source can lose a little more than was counted.
- An automatic drink is counted a minute late, and a sip in the same minute as another eat or drink is caught one minute later still. Right after a respawn, one minute's automatic drinking can count toward the old character.
- A dose of caffeine or alcohol split across many sips can read a lower level than the same dose in one go.
- Caffeine and alcohol absorb as fast with a meal as on an empty stomach.
- Two meals in the stomach at once act as one meal for how nutrients help or hinder each other's absorption. Fat-soluble vitamins absorb better with fat still in the stomach, so the help eases as the meal empties.
- A new record's first minute drops what was absorbed in it.

**Body, energy and exercise**
- The game does not tell the server when a player runs or sprints, so a runner is billed as a walker.
- Activity reaches the model with a short lag, fixed in real seconds, so its length in game time depends on the day length. Only a Fitness exercise is billed from its first minute. The server cannot see which timed action is running, so timed actions are billed at their activity level.
- A minute in which the game clock cannot be read is skipped. Carried weight is read as kilograms.
- Chopping is billed as rope climbing (8.0 MET), and a short climb can be missed.
- A Fitness set the client abandons without stopping it is billed until the client disconnects; the game's server keeps the set running too.
- A modded exercise, a set started before a reconnect or a server start, or a set on a game build with no Fitness action, is billed at the flat Fitness rate (6.0 MET). Such a set's training is classed from the Strength experience it gives.
- After a standing player stops an activity, the first minutes may be billed as idle, and an eat or a sip can bill one idle minute.
- The after-burn follows the Fitness set only, at a fixed share and pace.
- An exhausted, idle character burns energy as if lightly active.
- Time offline is not simulated: a long absence counts as at most an hour of the model, and no clock the mod keeps runs while the player is away, so no sleep debt builds, a repeated food does not fade and no day counts toward quitting nicotine; a jump of several days closes the missed days with no protein counted.
- When a character's saved record is lost (pruned after the server's keep period, a damaged save file, or a save file that stays unreadable), the mod starts a new record from the character as it stands, so changes the mod made earlier stay: a Strength level it lowered becomes the new starting level, the carry capacity it last set becomes the new base, and a Night Vision or Short Sighted trait it added is never taken away.
- The model's day closes at 07:00 game time, and the daily figures count from that close. The day's energy figure leaves out the exercise of the minute before the close, and a close that skipped days reads only the new day's training.
- Aerobic training counts minutes in two intensity bands, not total energy.
- Alcohol's effect on recovery resets at the day close, not over a rolling 24 hours.
- A rep is counted from the Strength experience the game grants; a character at the Strength experience cap has reps counted from Fitness experience instead.
- Loss of strength from disuse needs a broken or splinted leg.
- Strength is clamped to the game's levels 0 to 10. A rise is at most one level per six game hours; a fall follows an experience loss at once and a falling ceiling by one level per game hour.
- With BeyondTen loaded, its mastery levels above 10 are outside the model, and a level-10 perk holding at least the level-9 experience reads 10.
- The weight direction thresholds are a game choice.

**Deficiency, excess and effects**
- Vitamin D has no sunlight term, so every character trends toward the level their diet holds; its effects ship turned off.
- Omega-3 drives no mood effect. Liver glycogen is not modelled. Potassium does not count toward refeeding risk.
- Movement speed and aiming effects are computed but not applied, because the game resets them.
- Toxicity shows as food sickness, never as poison. The magnesium, niacin, folate and vitamin E upper limits apply to supplemental or added forms only, so food is never tested against them; the food data does not separate the folic acid and niacin added to enriched foods from what they contain naturally, so an enriched staple is exempt too.
- In Managed mode, hunger and thirst never reach the top-level Hungry and Thirsty moodles.
- A trait the mod gives or takes reaches the player at once, but other players see the change only after a reconnect.
- The body-temperature effects are not calibrated against the body's own regulation, and at rest a small cooling effect does not act.
- A Night Vision or Short Sighted trait the character already had is never removed.
- Whether the healing effects reach healing while awake is not yet measured, and a wound's last fraction heals at the normal rate. The regeneration settings are not saved with the character; the mod sets them again each time.
- The protein grade reads unknown for the first seven days. Protein needs read a neutral figure before the first day closes.
- The refeeding sickness holds for the whole day of the event.
- Endurance stays vanilla's while awake. Asleep, the mod's recovery factor applies one minute late.
- The sleep-onset delay is the game's. A wake of under 10 game minutes during the night counts as sleep.
- The sleep model needs `SleepAllowed` and `SleepNeeded` both on, and reads them once at start.
- The cold-catching effect is not yet measured.
- A dead character's record stops until the respawn.
- Several model steps read the previous minute's values, so some effects act a minute late, and a number that goes bad in one step is repaired at the next minute.

**Intake and food values**
- A food outside the table gets estimated values. A crafted item made by a recipe with several outputs, or at a furnace or drying rack, takes its own type's values instead of its ingredients'. An ingredient used in part counts whole.
- A drink-like food (thirst but no hunger value) that was split or partly eaten can count a little off.
- Monotony counts each food by its full type, so a cooked dish is one type whatever went into it, and one food sold under two types counts as two. A small snack counts only a small part of a meal; drinks count no monotony. As monotony fades it lowers mood by the same amount, even if something else raised it meanwhile. Vanilla wipes boredom while a character panics, so monotony's boredom is wiped then too.
- The caffeine and alcohol of a drink taken in the minute before a server stop are lost (the day's totals keep them).
- Another mod that replaces the game's eat or drink action without calling the original stops the mod seeing those eats.
- Calories another mod adds straight to the calorie store are counted as eaten food, as calories and macros only, with no nutrients; a very small rise is ignored, and a fall is never counted. A write by another mod inside an eat counts as part of that eat. With vanilla Nutrition on, a missed intake smaller than vanilla's drain is lost.
- The food tooltip shows a whole item's values; for a dish or a crafted item it does not show the ingredients the eat will count.

**The interface and sync**
- Updates reach the player's panel and moodles with the next game minute, at most once a minute of real time.
- The energy moodle holds a reached level until the energy state falls a little below its bound. The hold starts afresh when the player is first seen after a join or a server start, and a panel opened between updates can show the last update's level beside the current state.
- A player's request for fresh values is answered at most once every five seconds.

**Managed mode**
- The mode is read once at server start.
- With the rates at zero, a stopped writer stops hunger, thirst and fatigue rather than falling back to vanilla.
- Other mods reading vanilla's hunger, thirst or fatigue rates read zero.
- Hunger, thirst and fatigue are written once a game minute: an eat or a drink shows at once, and the next write sets the model's value.
- Panic is written once a game minute, and vanilla lowers it a little between writes. Body temperature is written once a game minute.
- Asleep, fatigue saw-tooths by one minute of vanilla's recovery.
- Another mod that sets vanilla's rates after the mod's start brings back vanilla's drift between the minute writes.

## The self-report

At boot the server console prints one line, and each client console prints one when the player joins:

```
[NutritionRevamp] NutritionRevamp v1.0.0 build 42.21 side=server mode=managed itemPass=true legacyMirror=on frameworks=n/a rates=zeroed limitations=13 nutritionOn=false log=2
[NutritionRevamp] NutritionRevamp v1.0.0 build 42.21 side=client mode=managed itemPass=true frameworks=MoodleFramework log=2
```

- `itemPass` is `true` when the mod's food values are loaded (it reads one food, the acorn, and compares its calories with the mod's value), `false` when the vanilla value or another mod's value won, and `unread` when the read could not be made.
- `legacyMirror` is the `NR.LegacyMirror` option. `frameworks` names MoodleFramework on a client that has it, else `none`; the server prints `n/a` because the framework is client-side.
- `mode` is `managed` or `overlay`, and `rates` is `zeroed` when Managed mode set vanilla's rates to zero, else `vanilla`.
- `limitations` counts the stat writer's own limitation list: 13 in 1.0.0. A different number means a different build of the mod.
- `nutritionOn=true` means the vanilla Nutrition option is on (see above).

When you report a bug that involves food, eating, weight or stats, paste both lines with the mod list: the server's from the server console log, and the client's from the player's `console.txt`. A large nutrition mod is the usual first suspect for an unrelated food bug, and the two lines settle most of those at once.

## When the mod does not load

The mod declares `versionMin=42.21` and no maximum. On a game build older than 42.21 the game treats the mod as absent: the log prints the same not-found line it prints for a mod folder that is not there, or for a missing dependency. When the mod does not load, read its `mod.info` and compare `versionMin` with the game build rather than trusting the log line. On a later build the `42.21/` directory stays in use until a release ships a newer one.

## Updates and the join checksum

The game hashes every script and Lua file the mod ships and compares them when a client joins; a client whose copy of any one file differs from the server's — even by one character inside a comment — is disconnected before it reaches the game (its log names the file: `checksum-File doesn't match the one on the server`). Only line endings are ignored. So any update that changes a script file or a `.lua` file is a server event: stop the server, update the mod on the server, start it, then let clients update. A client still holding the old release is refused at the join until it updates; it does not join with the difference.

Every code release of this mod changes a Lua file, so every release is a server event. Each release's notes say so.

Never give a player a checksum-bypass role to get them in: the bypass skips the check but leaves the difference, and that player then plays on food values and Lua code the server does not hold.

## When another mod raises an error

A release client was tested with one mod that raises an error in an event handler, and the reading was one shape: the raising handler stops, and the handlers around it and the client go on. A client run with `-debug` stops in the Lua debugger instead, so a player on a release client does not see that stop.

## Compatibility

The neighbour table, with what the mod does about each mod and the evidence behind it, is `COMPATIBILITY.md`. Nutrition Makes Sense cannot run beside this mod: when both are loaded, the server log prints a warning at boot.
