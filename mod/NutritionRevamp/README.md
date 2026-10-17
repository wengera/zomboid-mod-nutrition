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
| `NR.ExcessEffectsOn` | true | On: an intake above a nutrient's upper limit raises that nutrient's excess level (the magnesium, niacin, folate and vitamin E limits apply to supplemental or added forms, so food never reaches them). Off: every excess level reads zero; intake is still tracked. |
| `NR.BalanceBonus` | true | On: while every tracked nutrient is replete, the regeneration coefficient runs 5 percent higher (a game choice with no live reading). |
| `NR.Severity` | 1.0 (0 to 3) | Scales every penalty a deficiency or an excess brings. 0 removes them all except the health drains, which no option turns off. Short Sighted needs 1.0 or more. |
| `NR.VisibilityMode` | 2 (Bands) | How much each player's interface shows: 1 Symptoms, 2 Bands, 3 Numbers. A character with the Nutritionist trait sees Numbers whatever the option. |
| `NR.RecordKeepDays` | 30 (0 to 3650) | A player's nutrition record is dropped after this many real days without the player online; a returning player then starts a fresh record from the character as it stands (see the lost-record limitation under Body, energy and exercise). 0 keeps every record. Counted in real time, because game days pass at each server's own speed. Time the server is down counts too. |
| `NR.SexSpecific` | false | Off, every character uses the male values wherever the mod indexes by sex (requirements, body-fat bands, the thin-trait edges, the starting fat, alcohol, iron, calcium); on, a female character uses the female values. |
| `NR.StimulantRealism` | 1 (Game) | The strength of coffee and alcohol. 1 Game: a cup eases fatigue about twice as much as vanilla's, four beers drunk within an hour peak at about vanilla's first Drunk level, and the effect builds and fades over hours, and the hangover is mild and short. 2 Realistic: the pharmacological strengths (a cup about six times vanilla's fatigue relief, about half again the intoxication, a hangover twice as long and twice as heavy). Absorption, clearance, caffeine tolerance and withdrawal, and when the hangover starts are the same in both. |

The server re-reads the options every in-game minute, so a change made while the server runs takes effect without a restart, except `NR.Mode`, which is read at start.

### Strength options

Every Strength option is read through one clamp: a number outside its range takes the nearest bound, except the two whole-day options, which read their default.

| option | default (range) | what it does |
|---|---|---|
| `NR.StrengthTimeScale` | 1.0 (0.25 to 30) | The biology clock: 1.0 is one biological day per game day. It multiplies the daily growth, detraining, regain and peak-memory rates and shortens the grace days by the same factor; weekly sets still count over 7 game days. |
| `NR.StrengthXPPerSet` | 360 (50 to 2000) | How much vanilla Strength experience counts as one hard set (360 is one push-up set to exhaustion, measured). |
| `NR.StrengthIncidentalWeight` | 0.35 (0 to 1) | The weight on Strength XP earned outside a Fitness exercise (carrying, chopping, combat), relative to the same XP from training. |
| `NR.StrengthCapLevel` | 16.5 (12 to 20) | The untrained natural muscle cap, in bio levels (one bio level is 0.5 kg/m2 of lean mass; level 5 is the untrained average). Caps above about 17.7 are held at the natural muscle limit. |
| `NR.StrengthTraitShare` | 0.5 (0 to 1) | The share of a muscle trait's starting lean-mass difference that moves the set point and the cap, as a fraction. |
| `NR.StrengthYearsToLevel10` | 4 (1 to 10) | How many years of perfect training at a biology clock of 1.0 take the untrained average character to Strength 10, in years. |
| `NR.StrengthNeuralMax` | 1.1 (1.0 to 1.15) | The most that trained neural drive multiplies strength, as a factor (1.0 is none). |
| `NR.StrengthNeuralRiseWeeks` | 3 (1 to 8) | The time constant of the neural factor's rise under training, in weeks. |
| `NR.StrengthNeuralDecayWeeks` | 12 (4 to 26) | The time constant of the neural factor's decay once training has lapsed past its grace days, in weeks. |
| `NR.StrengthNeuralGraceDays` | 21 (0 to 60) | How many days below the maintenance dose pass before the neural factor starts to decay, in days. |
| `NR.StrengthNeuralSaturationSets` | 5 (1 to 12) | The weekly hard sets at which the neural factor rises at its full rate, in sets a week. |
| `NR.StrengthRate` | 1.0 (0.25 to 4) | A multiplier on the fitted muscle growth rate: 2 builds twice as fast, 0.5 half as fast. |
| `NR.StrengthThreshold` | 0.5 (0.25 to 1.0) | The weekly hard sets a novice needs before muscle grows, in sets a week; the threshold rises with training status. A combination that makes the threshold exceed the set cap falls back to the defaults at load. |
| `NR.StrengthThresholdRise` | 3 (0 to 4) | How steeply the growth threshold rises with training status, as an exponent (0 is flat). A combination that makes the threshold exceed the set cap falls back to the defaults at load. |
| `NR.StrengthTrainedSetCap` | 12 (8 to 30) | The most weekly hard sets that count toward growth in a body at its cap, in sets a week. A combination that makes the threshold exceed the set cap falls back to the defaults at load. |
| `NR.StrengthProteinFull` | 1.6 (1.0 to 3.0) | The protein intake at which growth is not held back by protein, in grams per kilogram a day; the lower protein steps scale with it. |
| `NR.StrengthDeficitZero` | -650 (-2000 to -200) | The daily energy deficit at which a novice's muscle growth stops, in kcal a day (negative). |
| `NR.StrengthDeficitZeroStatusDrop` | 0.5 (0 to 0.9) | How far that deficit limit shrinks toward zero for a body at its cap, as a fraction of the limit. |
| `NR.StrengthNoviceDeficitDepth` | 6 (0 to 10) | How much further a high-protein novice can grow into a deficit, as a multiple of the deficit limit. |
| `NR.StrengthBalanceGate` | 1.0 (0.5 to 1.0) | The share of full growth available at energy balance for a novice, as a fraction (1.0 is all). |
| `NR.StrengthBalanceGateStatusDrop` | 0.5 (0 to 0.7) | How far that share drops for a body at its cap, as a fraction of the share. |
| `NR.StrengthSurplusFull` | 0.1 (0.02 to 0.30) | The energy surplus at which growth is not held back by energy, as a fraction of daily energy expenditure. |
| `NR.StrengthSurplusFullStatusDrop` | 0.5 (0 to 0.9) | How far that surplus requirement shrinks for a body at its cap, as a fraction of the surplus. |
| `NR.StrengthTrainedNeedsSurplus` | 0 (0 to 1) | How strongly a body at its cap needs an energy surplus to grow: the option scales the growth available at energy balance by (1 − value × status), so at 1 a body at its cap grows nothing at balance. As a fraction. |
| `NR.LeanLossTrainingProtect` | 0.35 (0 to 0.9) | The share of a deficit's lean-mass loss that training prevents, as a fraction. |
| `NR.LeanLossProteinProtect` | 0.6 (0 to 0.9) | The share of a deficit's lean-mass loss that enough protein prevents, as a fraction. |
| `NR.LeanLossProtectFloor` | 0.1 (0 to 0.5) | The share of a deficit's lean-mass loss that no protection prevents, as a fraction of the loss. |
| `NR.LeanLossProteinFull` | 1.6 (1.2 to 3.0) | The protein intake at which the protein protection of lean mass in a deficit is complete, in grams per kilogram a day. |
| `NR.StrengthMaintainShare` | 0.333 (0.1 to 1.0) | The share of the growth threshold (for muscle) and of the neural saturation sets (for the neural factor) that holds strength without growth; weeks below it count toward detraining. As a fraction. |
| `NR.StrengthGraceDays` | 14 (0 to 60) | How many days of missed training pass before muscle begins to detrain, in days. |
| `NR.StrengthDetrainHalfLifeWeeks` | 6 (2 to 26) | The half-life of muscle lost to detraining once the grace days have passed, in weeks. |
| `NR.StrengthDetrainStatusSlowing` | 2 (0 to 4) | How much a trained body's detraining slows with status, as a multiplier on the half-life per unit of status (0 is none). |
| `NR.StrengthRegainHalfLifeWeeks` | 6 (1 to 26) | The half-life of regaining muscle lost below its held peak, in weeks. |
| `NR.StrengthPeakHalfLifeYears` | 2 (0.25 to 20) | The half-life of the body's memory of its peak muscle, in years. |

## Managed and Overlay

**Managed** (the default). At server start the mod saves vanilla's hunger, thirst and fatigue rise rates and sets them to zero. Once a game minute it writes hunger, thirst and fatigue from its own model.
- The mode is read at start; a change needs a restart.
- With the rates at zero, a stopped writer stops hunger rather than falling back to vanilla.
- Other mods that read vanilla's hunger, thirst or fatigue rates read zero. A mod that needs the saved values can call `NutritionRevamp.vanillaRate(key)`.
- A rate tweak from another mod has no effect, because the mod's model sets those stats. A mod that sets the rates again after the mod's start handler brings vanilla's drift back between the minute writes, and the next write takes it back.

**Overlay.** Vanilla's rates and its hunger, thirst and fatigue stand. The mod still tracks nutrients, the body and the stomach, and writes its effects: mood and sickness floors, panic, body temperature and intoxication. Drinking that the game does on its own (auto-drink) is not captured in Overlay.
- Starving and dying of thirst are vanilla's in Overlay: vanilla's own level-4 hunger and thirst health drains, and their deaths, run as in the base game. The mod's starvation and dehydration drains do not run there. Its scurvy, beriberi, pellagra, sodium and iron drains still do.
- A new character still eats the fresh start's plate in Overlay. Its calories, nutrients and stomach weight count, though vanilla's hunger is left as the game set it.

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
  - **Symptoms:** four words for deficiency, excess, stimulant and sleep, and a line for each health-draining state (Weakened by starvation, Suffering from dehydration, Scurvy, Beriberi, Pellagra, Dangerously low sodium or Iron poisoning).
  - **Bands:** also the body-fat band (Emaciated, Gaunt, Overly lean, Normal, Overfat or Obese), the weight, a **Body fat** word (Very lean, Lean, Healthy, High or Very high, with cut points by sex; a shown word holds until the fat share leaves its band by half a percentage point), a **Weight trend** word (Losing, Steady or Gaining: the last seven days' change in body mass, steady within 0.02 kg a day, the same threshold as vanilla's weight arrows on the character screen), the **Strength** level to one decimal (the body's true level; the Strength perk follows it with a quarter-level hold, see Strength), the dehydration in per cent of body mass once it passes 1 %, and a grade for each tracked nutrient (Replete, Marginal, Depleted or Clinical).
  - **Numbers:** also fat and lean mass, each nutrient's store and excess level, caffeine in the body, blood alcohol and sleep debt.
- **The character tab.** A Nutrition tab in the character info window shows the same rows.
- **The food tooltip.** A band below each food's tooltip first says about how long a whole one fills you and its kcal, in place of vanilla's hunger line: the hours a whole item eaten alone, when Peckish, keeps the Peckish moodle off for an average body, to the nearest half hour (for a whole item, even when part of it is eaten, and not capped by the Overfull refusal). A dish made from a recipe keeps vanilla's hunger line. The band then says where its values come from. At Bands it lists the four macros and the nutrients the item is rich or low in; at Numbers it lists every nutrient. The band shows the values of a whole item. A player can turn the band off on the options page.
- **The moodles.** Five moodles: Deficiency (Marginal to Clinical; it reads only the nutrients whose shortage has an effect, while the panel grades every nutrient), Excess (Elevated to Excessive), Stimulant (Alert to Overdosed), Sleep (Short on sleep to Collapsing) and Overfull (Pleasantly overfull to Painfully stuffed). With MoodleFramework they are drawn through it; without it, in the mod's own icon column. A player can turn them off on the options page, or hide only the first level of Stimulant, Sleep and Excess. Hunger and thirst show through vanilla's own moodles.

## What the mod models

- **Nutrients beyond the macros.** Thirteen vitamins and choline, seven minerals, fibre, essential fatty acids, sodium, potassium, caffeine and alcohol. Most have a store that fills from food and empties at its own rate, a daily requirement, and steps of deficiency and excess.
- **Foods.** 522 vanilla foods have their calories, carbohydrates, proteins and lipids re-based on published food-composition data, and each carries a nutrient table. A food the table does not map, such as another mod's food, gets values estimated from its food type and energy. A food mod can declare its own nutrients through the documented `NR_Nutrients` item key. Dishes and crafted food are counted from their ingredients. Drinks count by their fluid. Water drunk straight from the world counts as water.
- **Eating.** Every eat and drink through the game's own actions is captured on the server. Food passes through a stomach that empties over time before it is absorbed, and some nutrients absorb better or worse with others in the meal.
- **Hunger.** Hunger comes from physiology, not from vanilla's per-food hunger values:
  - how full the stomach is, with protein filling more and drinks filling less;
  - a pool of recently eaten energy, which fades within a few hours;
  - the deficit drive: the last 24 hours' energy balance and how much fat the body has lost from its own reference (nothing until a tenth of it is lost, the full drive at seven tenths);
  - the time of day, recent hard exercise (which briefly blunts hunger), sleep debt and nicotine withdrawal.

  Past about 730 g in the stomach the Overfull moodle rises in four steps to 1100 g. At its third step the body slows, as under a heavy load; at the fourth the character feels queasy and cannot start eating, or drinking anything with food value, until the stomach empties (water stays allowed). A satisfying meal shows vanilla's Well Fed for about half an hour, with a gentle heal. Peckish and Hungry come back on vanilla's rhythm through the day. In Managed mode hunger stays below vanilla's top level until the body truly starts to starve: about thirty hours after the stomach last held food, Starving shows (near vanilla's own time), and health drains to a floor (see Deficiency and excess). Eating 600 kcal or less over the last three to four days keeps it Starving between meals. Only a real meal or snack, about 200 kcal or more at once, ends it; nibbling a floret an hour does not. A new character starts from a fresh plate of food, so its first hunger reads like vanilla's spawn.
- **Thirst.** A body water pool with sodium and potassium. Water is lost through basic turnover and sweat, and sweat grows with work and heat. Salt changes how much water the body holds. Basic turnover is about 2 litres a day, more for a bigger body; High Thirst raises it by half and Low Thirst halves it. Thirst follows the water the body lacks, and water still in the stomach already eases it. In Managed mode Parched shows at a 4 % body-water deficit, about 32 hours without water at rest, where the dehydration drain begins.
- **Monotony.** Eating the same food day after day lowers mood, up to the first level of Unhappy and Bored; a staple such as bread, rice or pasta counts a quarter as much. It fades over the days after the diet varies.
- **The body.** A body of fat mass, lean mass and a small labile lean (water and glycogen that an overfed day stores and a deficit spends first), set at character creation (see Character creation). Resting and activity expenditure, eating and training move it; the lean and labile masses move once a game day. The total is written into vanilla's weight. The weight band traits follow body fat, not weight: Overly Lean, Gaunt and Emaciated below 12, 8 and 5 % body fat (20, 16 and 13 % for a woman under `NR.SexSpecific`); Overfat and Obese from about 26 and 34 % body fat, the fat cuts scaled by the body's lean, so a muscular body holds more fat before they apply. Each is shown under the mod's name, moves only a little past its edge, and is checked once a game day.
- **Character creation.** The creation screen offers Weak, Feeble, Stout and Strong at their vanilla costs, and Overfat, Obese, Overly Lean and Gaunt (vanilla's Overweight, Obese, Underweight and Very Underweight), which give 6, 10, 6 and 10 points; Emaciated is reached only in play. A muscle trait keeps its vanilla start level but for Weak, which vanilla starts at 0 and the mod at 1 (Weak 1, Feeble 3, none 5, Stout 7, Strong 9), built from lean mass and an innate strength the trait sets; half the start's lean difference from the average is permanent, so an idle Strong character settles in the Stout band. A profession's Strength boost raises the start like a small trait (a Farmer with no muscle trait starts at 6). A fat trait starts with more fat on the same lean; a thin trait starts with less fat (10 and 6.5 % body fat) and underfed: hungry, with a partly slowed metabolism, until the fat is regained. Weight Gain and Weight Loss change no starting body. The server checks the point total and the exclusions again and strips an illegal trait, the costliest first, logging it.
- **Exercise and energy use.** Energy use follows the game's own activity level. A Fitness exercise is billed at the energy cost of its type: squats 3.0 MET, push-ups and sit-ups 3.8, burpees 7.5, and the curls and the dumbbell press 3.5. Hard exercise leaves a short after-burn. Muscle glycogen falls with hard work and a low-carbohydrate diet, and blood glucose falls with exhausting work or alcohol on an empty stomach.
- **Strength.** The Strength level reads the body: its lean mass, a trained neural factor (up to 10 % more strength, built over weeks of training and lost over months without) and an innate strength the muscle trait sets at creation. Strength experience never moves the level; it is the training signal. The week's Strength experience counts as hard sets, one per `NR.StrengthXPPerSet`, and experience earned outside a Fitness exercise (carrying, chopping, combat) counts at `NR.StrengthIncidentalWeight`. Lean mass grows only when training, protein and enough energy act together (growth stops at a deficit of about 650 kcal a day for a novice, less for a trained body), ever more slowly toward a natural cap that no character passes, and a trained body needs more weekly sets to keep growing. Without training, muscle detrains after two weeks toward the body's set point; lost muscle comes back fast toward a remembered peak that fades over years; starvation takes lean mass whatever the training. The level is written once a game day: it rises at each whole level and falls only once the body is a quarter level below it. At the defaults, an untrained character on perfect training (20 hard sets a week, 2 g of protein per kg a day and a 10 % energy surplus) reaches Strength 10 in four years (`NR.StrengthYearsToLevel10`). With BeyondTen loaded, the mod writes BeyondTen's Strength mastery above 10; without it the perk shows 10. Carry capacity follows vanilla's factor for the Strength band and moves with dehydration, long hours awake, caffeine and body fat. Time at a raised activity level counts as aerobic training.
- **Deficiency and excess.** Each deficiency and excess brings effects of its own: fatigue, mood, sickness, slower healing, heavier bleeding, faster wound infection, colds, body temperature, bruising, and Short Sighted at a clinical vitamin A deficiency. A long, well-stocked vitamin A and zinc intake grants Night Vision. The most severe states (starvation, dehydration, clinical scurvy, beriberi or pellagra, very low blood sodium and an iron overdose) drain health to a floor that deepens until the state is treated or reaches its real death point; no option turns the drains off.
- **Caffeine, alcohol and sleep debt.** Caffeine is absorbed and cleared over hours, builds tolerance and brings withdrawal. Alcohol raises blood alcohol and drives the game's intoxication, with a hangover after. How strong each is follows `NR.StimulantRealism`. Sleep debt builds from short nights and raises hunger.

## Known limitations

The mod's own code lists these. Some are game choices, some are walls the game puts in a mod's way.

**Hunger and the stomach**
- The model's hunger never reaches 0 after a meal; the displayed hunger, written through a curve fitted to vanilla's rhythm, reads about 0 after a satisfying one. A hunger level steps down only once hunger is a little under its threshold.
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
- A new character, or one who just respawned, reads as if they had eaten evenly the day before. They reach vanilla's Peckish moodle after several hours without food.
- An eat in a new record's very first minute does not count toward the meal pool.
- An eat another mod makes without the game's eat action counts a minute late and as calories and macros only. A drink another mod makes outside the game's drink actions is not seen.
- When the mod first sees a character whose hunger is lower than its stomach alone can show, the character eats a fresh plate of ordinary foods first (at most a 667 kcal plate), counted like any meal, so its first hunger reads back the game's own; this also happens in Overlay. A hunger above what the stomach's fullness allows drops to that level at once.
- A diet of tiny snacks begun while fed, such as a broccoli floret an hour with no fast first, stays out of the starvation state: it is over the 600 kcal the fallback allows and never long enough unfed. Only the slow starvation at a BMI under 13 catches it. Once the state is open, such snacks no longer end it.
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
- A modded exercise, a set started before a reconnect or a server start, or a set on a game build with no Fitness action, is billed at the flat Fitness rate (6.0 MET). Its Strength experience counts as incidental training (`NR.StrengthIncidentalWeight`), not as a Fitness set.
- After a standing player stops an activity, the first minutes may be billed as idle, and an eat or a sip can bill one idle minute.
- The after-burn follows the Fitness set only, at a fixed share and pace.
- An exhausted, idle character burns energy as if lightly active.
- Time offline is not simulated: a long absence counts as at most an hour of the model, and no clock the mod keeps runs while the player is away, so no sleep debt builds, a repeated food does not fade and no day counts toward quitting nicotine; the model's day calendar stops while the player is away, so a return closes no missed day: the body, its training and its Strength stand as they were left.
- When a character's saved record is lost (pruned after the server's keep period, a damaged save file, or a save file that stays unreadable), the mod starts a new record from the character as it stands, so changes the mod made earlier stay: the muscle trait is read back from the Strength level net of the profession's and the other traits' boosts, so a level that training or the mod moved reads as another trait (a Stout Farmer detrained from 8 to 6 starts again with no muscle trait), and a Night Vision or Short Sighted trait it added is never taken away.
- The model's day closes at 07:00 game time, and the daily figures count from that close. The day's energy figure leaves out the exercise of the minute before the close.
- Aerobic training counts minutes in two intensity bands, not total energy.
- Alcohol's effect on recovery resets at the day close, not over a rolling 24 hours.
- Strength experience the game grants while a character sleeps, or while its Strength experience sits at the level-10 total, trains nothing. A grant made without the game's multipliers (the admin `/addxp` without `-true`) is divided by the sandbox multiplier anyway, and a grant that ends a skill book's range counts at the book's factor.
- The fast muscle loss of immobilisation needs a broken or splinted leg; otherwise missed training detrains muscle at the normal pace.
- The Strength perk shows levels 0 to 10. A level is written once a game day, and at once when an admin or a grant moves the perk. It rises at each whole level and falls only a quarter level below the level shown, so the perk can read up to a quarter level above the body; the panel shows the body's true level. A level due while the character sleeps waits until it wakes.
- With BeyondTen loaded, its mastery levels above 10 follow the body's level at each write, without the quarter-level hold.
- A thin start stays hungry until its fat is back at the no-trait share: the body never sets that reference lower.
- The weight direction thresholds are a game choice.

**Deficiency, excess and effects**
- Vitamin D has no sunlight term, so every character trends toward the level their diet holds; its effects ship turned off.
- Omega-3 drives no mood effect. Liver glycogen is not modelled. Potassium does not count toward refeeding risk.
- Movement speed and aiming effects are computed but not applied, because the game resets them.
- Toxicity shows as food sickness, never as poison. The magnesium, niacin, folate and vitamin E upper limits apply to supplemental or added forms only, so food is never tested against them; the food data does not separate the folic acid and niacin added to enriched foods from what they contain naturally, so an enriched staple is exempt too.
- In Managed mode, the top-level Starving and Parched moodles show only while the starvation or dehydration state is active. While either shows, the game's own starvation and thirst health loss is off for that player. The mod puts back the other health losses that share that setting (sickness, bleeding, heavy load and weight under 35 kg) once a minute, at vanilla's rates on average. The heavy-load loss is its average, never below 75 health, not the game's one-in-ten roll each moment.
- While a health drain runs, vanilla's regeneration and its food heal are held off, so health rests at the floor. Wounds still mend toward the floor at vanilla's pace.
- The mod writes vanilla's food timer every minute for Well Fed and the Overfull refusal, so another mod that reads or writes that timer sees the mod's value and loses its own write at the next minute. A drink with no food value, and an eat another mod starts on the server, are not refused.
- Starvation's effect phases (weakness, then cold and slower healing, then infection and mood) count unfed hours on their own clock. The refeeding risk and the protein-energy grade count whole days of little food, the clinical criterion, so the two can disagree by up to a day at a fast's start. A new character's first, partial day never counts as a day without food.
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
- The food tooltip shows a whole item's values; for a dish or a crafted item it does not show the ingredients the eat will count. Its fill hours are for the whole item eaten alone, even when the Overfull refusal would stop the eat partway (a whole watermelon, a block of butter), and even when part of it is gone.
- Whether the tooltip's hiding of vanilla's hunger line, and the band below the box, show on screen is not yet measured: the test harness cannot hover.

**The interface and sync**
- Updates reach the player's panel and moodles with the next game minute, at most once a minute of real time.
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
